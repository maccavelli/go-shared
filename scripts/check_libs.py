#!/usr/bin/env python3
"""Check a Go repository against the latest tags of the libraries it names.

docs/decisions/0002-MADR-shared-library-compatibility-check.md. Derived from
gobble-cli's scripts/check_libs.py at 007b63f (its 0019-MADR D14), with the
gobble-specific parts replaced: the libraries come from the consumer's
check_libs.json, the toolchain from the consumer's go.mod, and apidiff and
govulncheck run at pinned versions unless the consumer declares them as tools.

For each library named in check_libs.json, take the latest semver tag (never a
branch), and on a scratch clone of the consumer's committed HEAD, outside its
working tree:

  1. go get the tag and go mod tidy, failing if tidy settles on another
     version or moves any other module;
  2. go build, go vet for linux, darwin and windows, and go test the
     configured packages;
  3. apidiff from the pinned version, failing on an incompatible change of a
     v1 module (a module below v1 is reported, not failed); apidiff's exit
     status is not its verdict, so its text is read; a library pinned at the
     tag has nothing to compare;
  4. govulncheck, and the library's GitHub security advisories, which
     govulncheck does not see.

check_libs.json, at the consumer's root:

  {"libraries": [
    {"module": "github.com/<owner>/<repo>", "packages": ["./pkg/..."]}
  ]}

It needs the network, so it is never part of an offline gate. It reads,
prints and sends no credential: every command runs without the variables
whose names look like one.

Usage:
  check_libs.py [--repo DIR] [--config FILE] [--lib MODULE] [--tag vX.Y.Z]
                [--from vX.Y.Z] [--keep]
  check_libs.py --self-test

Exit status is 1 when any check fails, and 2 on a usage or config error.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

GOOSES = ("linux", "darwin", "windows")
SEMVER = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
SECRET = re.compile(r"KEY|TOKEN|SECRET|PASSWORD", re.IGNORECASE)
REQUIRE = re.compile(r"^\s*([^\s()]+)\s+(v[^\s]+)")
CONFIG_NAME = "check_libs.json"

# Tool pins (0002-MADR D5). golang.org/x/exp publishes no tags, so apidiff is
# pinned to a pseudo-version; it is the one gobble-cli's go.mod selects.
APIDIFF = "golang.org/x/exp/cmd/apidiff"
APIDIFF_VERSION = "v0.0.0-20260908205506-85c1c2202aba"
GOVULNCHECK = "golang.org/x/vuln/cmd/govulncheck"
GOVULNCHECK_VERSION = "v1.9.0"


class ConfigError(Exception):
    """A missing or malformed check_libs.json."""


@dataclass(frozen=True)
class Library:
    module: str
    packages: tuple[str, ...]

    @property
    def owner_repo(self) -> tuple[str, str]:
        parts = self.module.split("/")
        return parts[1], parts[2]

    @property
    def url(self) -> str:
        owner, repo = self.owner_repo
        return f"https://github.com/{owner}/{repo}"

    @property
    def name(self) -> str:
        return self.owner_repo[1]


@dataclass
class Consumer:
    root: Path
    toolchain: str | None
    tools: frozenset[str]


@dataclass
class Report:
    lib: str
    failures: list[str] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        line = f"{self.lib} {name}: {'ok' if ok else 'FAIL'}{' ' + detail if detail else ''}"
        print(line, flush=True)
        if not ok:
            self.failures.append(line)
        return ok

    def note(self, name: str, detail: str) -> None:
        print(f"{self.lib} {name}: {detail}", flush=True)


def read_config(text: str, source: str) -> list[Library]:
    """The libraries a check_libs.json names. Raises ConfigError naming source."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise ConfigError(f"{source}: not valid JSON: {err}") from err
    entries = data.get("libraries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f'{source}: needs a non-empty "libraries" list')
    libs: list[Library] = []
    for i, entry in enumerate(entries):
        module = entry.get("module") if isinstance(entry, dict) else None
        packages = entry.get("packages") if isinstance(entry, dict) else None
        if not isinstance(module, str) or not re.fullmatch(r"github\.com/[\w.-]+/[\w.-]+", module):
            raise ConfigError(f'{source}: libraries[{i}] needs "module" as github.com/<owner>/<repo>')
        if not isinstance(packages, list) or not packages or not all(isinstance(p, str) and p for p in packages):
            raise ConfigError(f'{source}: libraries[{i}] needs a non-empty "packages" list of strings')
        libs.append(Library(module, tuple(packages)))
    return libs


def load_config(path: Path) -> list[Library]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise ConfigError(f"{path}: not found; the repository must supply {CONFIG_NAME}") from err
    return read_config(text, str(path))


def toolchain_of(gomod: str) -> str | None:
    """The GOTOOLCHAIN a go.mod asks for: its toolchain line, else its go line."""
    toolchain = re.search(r"^toolchain\s+(go\S+)\s*$", gomod, re.M)
    if toolchain:
        return toolchain[1]
    go = re.search(r"^go\s+(\d+\.\d+)(\.\d+)?\s*$", gomod, re.M)
    if go:
        return f"go{go[1]}{go[2] or '.0'}"
    return None


def tools_of(gomod: str) -> frozenset[str]:
    """The tool paths a go.mod declares, in tool lines or a tool block."""
    found: set[str] = set()
    block = False
    for raw in gomod.splitlines():
        line = raw.split("//")[0].strip()
        if line.startswith("tool ("):
            block = True
            continue
        if block and line == ")":
            block = False
            continue
        if block and line:
            found.add(line)
        elif line.startswith("tool "):
            found.add(line.removeprefix("tool ").strip())
    return frozenset(found)


def version_key(v: str) -> tuple[int, int, int]:
    m = SEMVER.match(v if v.startswith("v") else "v" + v)
    if not m:
        raise ValueError(f"not a semver version: {v}")
    return int(m[1]), int(m[2]), int(m[3])


def clean_env(consumer: Consumer | None, **extra: str) -> dict[str, str]:
    """The environment without credential-shaped variables, with extra set."""
    env = {k: v for k, v in os.environ.items() if not SECRET.search(k)}
    env["CGO_ENABLED"] = "0"
    if consumer and consumer.toolchain:
        env["GOTOOLCHAIN"] = consumer.toolchain
    env.update(extra)
    return env


def run(args: list[str], cwd: Path, log: Path, consumer: Consumer | None, timeout: int = 1800, **env: str) -> int:
    """Run args in cwd, write their whole output to log, return the exit status."""
    with log.open("wb") as out:
        out.write(f"$ {' '.join(args)}\n".encode())
        out.flush()
        return subprocess.run(args, cwd=cwd, env=clean_env(consumer, **env), stdout=out, stderr=subprocess.STDOUT,
                              timeout=timeout).returncode


def latest_tag(lib: Library) -> str:
    out = subprocess.run(["git", "ls-remote", "--tags", lib.url], capture_output=True, text=True, timeout=120,
                         env=clean_env(None), check=True).stdout
    tags = {line.split("refs/tags/")[1].removesuffix("^{}") for line in out.splitlines() if "refs/tags/" in line}
    semver = sorted((t for t in tags if SEMVER.match(t)), key=version_key)
    if not semver:
        raise RuntimeError(f"{lib.module} has no semver tag")
    return semver[-1]


def requirements(gomod: str) -> dict[str, str]:
    """Every required module of a go.mod's text, by path."""
    out: dict[str, str] = {}
    block = False
    for raw in gomod.splitlines():
        line = raw.split("//")[0].strip()
        if line.startswith("require ("):
            block = True
            continue
        if block and line == ")":
            block = False
            continue
        if block or line.startswith("require "):
            m = REQUIRE.match(line.removeprefix("require "))
            if m:
                out[m[1]] = m[2]
    return out


def moved_modules(before: str, after: str, module: str) -> list[str]:
    """The modules other than module that a go.mod change adds, removes or moves."""
    a, b = requirements(before), requirements(after)
    return sorted(p for p in a.keys() | b.keys() if p != module and a.get(p) != b.get(p))


def incompatible(apidiff_text: str) -> list[str]:
    """apidiff's incompatible changes: the hyphen lines before "Compatible changes:"."""
    head = apidiff_text.split("Compatible changes:")[0]
    return [line.strip() for line in head.splitlines() if line.strip().startswith("- ")]


def covers(range_text: str, version: str) -> bool:
    """Whether a GitHub advisory's vulnerable_version_range covers version."""
    v = version_key(version)
    for part in range_text.split(","):
        m = re.fullmatch(r"\s*(<=|>=|<|>|=)?\s*v?(\d+\.\d+\.\d+)\s*", part)
        if not m:
            raise ValueError(f"unreadable version range: {range_text}")
        op, bound = m[1] or "=", version_key(m[2])
        if not {"=": v == bound, "<": v < bound, "<=": v <= bound, ">": v > bound, ">=": v >= bound}[op]:
            return False
    return True


def advisories(lib: Library) -> list[dict]:
    owner, repo = lib.owner_repo
    req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}/security-advisories",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "go-shared-check-libs"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - a fixed https URL
        return json.load(resp)


def apidiff_binary(consumer: Consumer, work: Path, logs: Path) -> Path:
    """apidiff, from the consumer's tool directive when it has one, else at the pinned version."""
    binary = work / ("apidiff.exe" if os.name == "nt" else "apidiff")
    if binary.exists():
        return binary
    if APIDIFF in consumer.tools:
        run(["go", "build", "-o", str(binary), APIDIFF], consumer.root, logs / "apidiff-build.log", consumer)
    else:
        run(["go", "install", f"{APIDIFF}@{APIDIFF_VERSION}"], work, logs / "apidiff-build.log", consumer,
            GOBIN=str(work))
    if not binary.exists():
        raise RuntimeError(f"apidiff could not be built; see {logs / 'apidiff-build.log'}")
    return binary


def govulncheck_args(consumer: Consumer) -> list[str]:
    if GOVULNCHECK in consumer.tools:
        return ["go", "tool", "govulncheck", "./..."]
    return ["go", "run", f"{GOVULNCHECK}@{GOVULNCHECK_VERSION}", "./..."]


def export_api(apidiff: Path, lib: Library, version: str, work: Path, logs: Path, consumer: Consumer) -> Path:
    """apidiff's export of the library at version, from a scratch module requiring it."""
    mod = work / f"api-{lib.name}-{version}"
    mod.mkdir()
    log = logs / f"{lib.name}-api-{version}.log"
    run(["go", "mod", "init", "scratch/checklibs"], mod, log, consumer)
    run(["go", "get", f"{lib.module}@{version}"], mod, logs / f"{lib.name}-api-get-{version}.log", consumer,
        GOFLAGS="-mod=mod")
    out = work / f"{lib.name}-{version}.exp"
    if run([str(apidiff), "-m", "-w", str(out), lib.module], mod, log, consumer, GOFLAGS="-mod=mod") != 0 \
            or not out.exists():
        raise RuntimeError(f"apidiff could not export {lib.module}@{version}; see {log}")
    return out


def check_api(report: Report, lib: Library, base: str, tag: str, work: Path, logs: Path, consumer: Consumer) -> None:
    """apidiff from base to tag. A library pinned at the tag has nothing to
    compare, and exporting one version twice would collide (gobble-cli's
    0019-PLAN P5 deviation 15)."""
    if base == tag:
        report.note("api", f"pinned at {tag}; nothing to compare")
        return
    try:
        apidiff = apidiff_binary(consumer, work, logs)
        old = export_api(apidiff, lib, base, work, logs, consumer)
        new = export_api(apidiff, lib, tag, work, logs, consumer)
        diff_log = logs / f"{lib.name}-apidiff.log"
        run([str(apidiff), "-m", str(old), str(new)], work, diff_log, consumer)
        breaks = incompatible(diff_log.read_text(encoding="utf-8", errors="replace"))
        if version_key(tag)[0] == 0:
            report.note("api", f"{len(breaks)} incompatible changes {base}->{tag}, reported only below v1; see {diff_log}")
        else:
            report.check("api", not breaks, f"{len(breaks)} incompatible: {breaks[0]}" if breaks else "")
    except RuntimeError as err:
        report.check("api", False, str(err))


def module_version(lib: Library, root: Path) -> str | None:
    """The library's version as the go.mod in root's tree requires it, or None when it is not required."""
    gomod = (root / "go.mod").read_text(encoding="utf-8")
    return requirements(gomod).get(lib.module)


def committed_gomod(root: Path) -> str:
    """The consumer's go.mod at HEAD: what the scratch clone checks (0002-MADR amendment)."""
    proc = subprocess.run(["git", "-C", str(root), "show", "HEAD:go.mod"], capture_output=True, text=True,
                          timeout=60, env=clean_env(None), check=False)
    if proc.returncode != 0:
        raise FileNotFoundError(proc.stderr.strip())
    return proc.stdout


def check_library(lib: Library, tag: str, base: str, work: Path, consumer: Consumer) -> Report:
    report = Report(lib.name)
    logs = work / "logs"
    logs.mkdir(exist_ok=True)
    clone = work / f"clone-{lib.name}"
    report.note("versions", f"pinned {base}, checking {tag}")
    if run(["git", "clone", "--quiet", str(consumer.root), str(clone)], work, logs / f"{lib.name}-clone.log",
           consumer) != 0:
        report.check("clone", False)
        return report
    before = (clone / "go.mod").read_text(encoding="utf-8")
    ok = run(["go", "get", f"{lib.module}@{tag}"], clone, logs / f"{lib.name}-get.log", consumer) == 0
    ok = ok and run(["go", "mod", "tidy"], clone, logs / f"{lib.name}-tidy.log", consumer) == 0
    if not report.check("get and tidy", ok, "" if ok else f"see {logs}"):
        return report
    # tidy resolves a package the consumer imports from the newest version
    # that has it, so a tag lacking one ends up as another version; every check
    # after this would then test that version (gobble-cli's 0019-PLAN P1
    # deviation 1).
    got = module_version(lib, clone)
    if not report.check("version", got == tag,
                        "" if got == tag else f"tidy moved it to {got}: {tag} lacks a package the repository imports"):
        return report
    moved = moved_modules(before, (clone / "go.mod").read_text(encoding="utf-8"), lib.module)
    report.check("modules", not moved, "new or changed module: " + ", ".join(moved) if moved else "")
    report.check("build", run(["go", "build", "./..."], clone, logs / f"{lib.name}-build.log", consumer) == 0)
    for goos in GOOSES:
        report.check(f"vet {goos}", run(["go", "vet", "./..."], clone, logs / f"{lib.name}-vet-{goos}.log", consumer,
                                         GOOS=goos) == 0)
    test_log = logs / f"{lib.name}-test.log"
    tested = run(["go", "test", "-count=1", *lib.packages], clone, test_log, consumer) == 0
    report.check("test", tested, "" if tested else f"see {test_log}")
    check_api(report, lib, base, tag, work, logs, consumer)
    report.check("govulncheck", run(govulncheck_args(consumer), clone, logs / f"{lib.name}-vuln.log", consumer) == 0)
    try:
        hits = [f"advisory {a.get('ghsa_id')} covers {tag}" for a in advisories(lib)
                if a.get("state", "published") == "published"
                for v in a.get("vulnerabilities") or [] if v.get("vulnerable_version_range")
                and covers(v["vulnerable_version_range"], tag)]
        report.check("advisories", not hits, "; ".join(hits))
    except (OSError, ValueError) as err:
        report.check("advisories", False, f"could not read: {err}")
    return report


def remove_tree(path: Path) -> bool:
    """Remove path, clearing the read-only bit git sets on its objects on
    Windows; report whether it is gone."""
    def writable_and_retry(func, target, _exc):  # noqa: ANN001 - shutil's onexc signature
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onexc=writable_and_retry)
    return not path.exists()


SELF_TEST_LIB = Library("github.com/example/lib", ("./...",))


def pinned_at_tag_not_compared() -> bool:
    """check_api with the base the tag exports nothing: its work and log
    directories do not exist, so any export or build would fail the case."""
    report = Report("self-test")
    missing = Path(tempfile.gettempdir()) / "go-shared-check-libs-self-test-missing"
    consumer = Consumer(missing, None, frozenset())
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            check_api(report, SELF_TEST_LIB, "v1.0.0", "v1.0.0", missing, missing / "logs", consumer)
    except Exception:  # noqa: BLE001 - any failure of the call fails the case
        return False
    return not report.failures and "nothing to compare" in out.getvalue() and not missing.exists()


def raises_config_error(text: str) -> bool:
    try:
        read_config(text, "fixture")
    except ConfigError:
        return True
    return False


def missing_config_refused() -> bool:
    missing = Path(tempfile.gettempdir()) / "go-shared-check-libs-no-such-dir" / CONFIG_NAME
    try:
        load_config(missing)
    except ConfigError as err:
        return CONFIG_NAME in str(err)
    return False


def self_test() -> int:
    """The parsers on fixed inputs, and the API step for a library pinned at
    the tag; each case must give its expected answer."""
    mod_a = "module m\n\nrequire (\n\tgithub.com/maccavelli/acp-go-sdk2 v0.14.0\n\tgolang.org/x/sys v0.48.0 // indirect\n)\n"
    mod_b = mod_a.replace("v0.14.0", "v0.17.0")
    mod_c = mod_b.replace("golang.org/x/sys v0.48.0 // indirect\n", "golang.org/x/sys v0.48.0 // indirect\n\texample.com/x v1.0.0\n")
    diff_bad = "Incompatible changes:\n- Foo: removed\n\nCompatible changes:\n- Bar: added\n"
    diff_ok = "Compatible changes:\n- Bar: added\n"
    good_config = '{"libraries": [{"module": "github.com/maccavelli/acp-go-sdk2", "packages": ["./acp/..."]}]}'
    tool_mod = "module m\n\ngo 1.27.2\n\ntool (\n\tgolang.org/x/exp/cmd/apidiff\n\tgolang.org/x/vuln/cmd/govulncheck\n)\n"
    cases = [
        ("an incompatible line fails", incompatible(diff_bad) == ["- Foo: removed"]),
        ("no incompatible line passes", incompatible(diff_ok) == []),
        ("only the library moving passes", moved_modules(mod_a, mod_b, "github.com/maccavelli/acp-go-sdk2") == []),
        ("adding example.com/x fails", moved_modules(mod_a, mod_c, "github.com/maccavelli/acp-go-sdk2") == ["example.com/x"]),
        ("= 0.15.0 covers v0.15.0", covers("= 0.15.0", "v0.15.0")),
        ("= 0.15.0 does not cover v0.16.0", not covers("= 0.15.0", "v0.16.0")),
        ("< 1.2.0, >= 1.0.0 covers v1.1.0", covers("< 1.2.0, >= 1.0.0", "v1.1.0")),
        ("< 1.2.0, >= 1.0.0 does not cover v1.2.0", not covers("< 1.2.0, >= 1.0.0", "v1.2.0")),
        ("a library pinned at the tag is not compared", pinned_at_tag_not_compared()),
        ("a valid config reads one library",
         read_config(good_config, "fixture") == [Library("github.com/maccavelli/acp-go-sdk2", ("./acp/...",))]),
        ("a missing config is refused, naming the file", missing_config_refused()),
        ("malformed JSON is refused", raises_config_error('{"libraries": [')),
        ("an entry without module is refused", raises_config_error('{"libraries": [{"packages": ["./..."]}]}')),
        ("an empty library list is refused", raises_config_error('{"libraries": []}')),
        ("a toolchain line wins", toolchain_of("module m\n\ngo 1.27.1\n\ntoolchain go1.27.2\n") == "go1.27.2"),
        ("a go line alone is used", toolchain_of("module m\n\ngo 1.27.2\n") == "go1.27.2"),
        ("a two-part go line is its .0 release", toolchain_of("module m\n\ngo 1.27\n") == "go1.27.0"),
        ("no go line leaves the toolchain alone", toolchain_of("module m\n") is None),
        ("tool directives are read", tools_of(tool_mod) == frozenset({APIDIFF, GOVULNCHECK})),
        ("no tool directive reads none", tools_of(mod_a) == frozenset()),
        ("a declared govulncheck runs as go tool",
         govulncheck_args(Consumer(Path("."), None, frozenset({GOVULNCHECK})))[:3] == ["go", "tool", "govulncheck"]),
        ("an undeclared govulncheck runs pinned",
         govulncheck_args(Consumer(Path("."), None, frozenset()))[2] == f"{GOVULNCHECK}@{GOVULNCHECK_VERSION}"),
    ]
    for name, ok in cases:
        print(f"self-test {name}: {'ok' if ok else 'FAIL'}")
    return 0 if all(ok for _, ok in cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Check a Go repository against the latest tags of its libraries.")
    ap.add_argument("--repo", default=".", help="the consuming repository's root; default the current directory")
    ap.add_argument("--config", help=f"the library list; default <repo>/{CONFIG_NAME}")
    ap.add_argument("--lib", help="one library's module path; default every configured library")
    ap.add_argument("--tag", help="the version to check; default the latest semver tag")
    ap.add_argument("--from", dest="base", help="the version to diff from; default the pinned one")
    ap.add_argument("--keep", action="store_true", help="keep the scratch directory")
    ap.add_argument("--self-test", action="store_true", help="run the offline self-test and exit")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    root = Path(args.repo).resolve()
    try:
        libs = load_config(Path(args.config).resolve() if args.config else root / CONFIG_NAME)
        gomod = committed_gomod(root)
    except ConfigError as err:
        print(f"check_libs: {err}", file=sys.stderr)
        return 2
    except FileNotFoundError as err:
        print(f"check_libs: {root}: no go.mod at HEAD ({err}); --repo must be a git repository whose root "
              "is a Go module", file=sys.stderr)
        return 2
    if args.lib and args.lib not in {lib.module for lib in libs}:
        print(f"check_libs: --lib {args.lib} is not in the configured libraries", file=sys.stderr)
        return 2
    consumer = Consumer(root, toolchain_of(gomod), tools_of(gomod))
    work = Path(tempfile.mkdtemp(prefix="go-shared-check-libs-"))
    print(f"repository: {root.name}; toolchain: {consumer.toolchain or 'the local go'}; logs: {work / 'logs'}",
          flush=True)
    failures: list[str] = []
    for lib in libs:
        if args.lib and lib.module != args.lib:
            continue
        base = args.base or requirements(gomod).get(lib.module)
        if base is None:
            report = Report(lib.name)
            report.check("required", False, f"{root.name}'s go.mod does not require {lib.module}; nothing to check")
            failures += report.failures
            continue
        report = check_library(lib, args.tag or latest_tag(lib), base, work, consumer)
        failures += report.failures
    kept = args.keep or bool(failures)
    if not kept and not remove_tree(work):
        print(f"could not remove {work}")
        kept = True
    print(f"{len(failures)} failing checks; " + (f"scratch kept at {work}" if kept else "scratch removed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
