#!/usr/bin/env python3
"""Scan one repository's tracked files for real user-home paths and print file, line, category.

Housed here by docs/decisions/0003-MADR-house-disclosure-check.md and
docs/decisions/0003-PLAN-house-disclosure-check.md. Derived from
prepare-commit-msg's scripts/check_disclosure.py at commit
72b37c384d122911e69b331ea816a4a32053301d, the copy that repository's
docs/decisions/0022-MADR-align-docs-ci-and-disclosure-gates.md defines:
PREFIXES, the placeholder rules, the markup stripping, the angle-bracket
window, the NUL skip, the unreadable-file result and the summary that names
counts only are that file's code unchanged. Two changes serve a shared
location (0003-MADR D2 and D5): the scan root is the --repo directory the
caller passes instead of this file's location, and a git failure is caught
and returns 2 where the source let it raise.

A finding is a user-home path written in the real layout with a concrete
(non-placeholder) account segment:

* macOS:    /Users/<name>
* Linux:    /home/<name>
* Windows:  \\Users\\<name> (covers C:\\Users\\<name>), and C:/Users/<name>;
  Windows forms are matched case-insensitively

A placeholder account segment is accepted, so convention lines pass:

* an environment substitution, such as $HOME, ${HOME}, %USERPROFILE%,
  $env:USERPROFILE
* a ~ segment

An angle-bracket token never decides here: a line carrying a full <…> token
demonstrates redaction in its own text and is accepted as a whole, and so is
the flagged line when the token sits on the line beside it too, since a
wrapped literal splits a demonstration across lines. A real home path
within a line of a <…> token passes it. Markup reaching into the segment
from either side is ignored first, and markup without an account in it is
accepted as no path occurrence.

One line is printed per file and line, `<path>:<line>: <category>`, then a
summary that names no content. A file with a NUL byte is read as binary and
skipped. A tracked file that cannot be read is a tool error, never a silent
skip. An account segment stops at the first separator or whitespace, since
a real one never spans either on its own.

The tree that is scanned is --repo, resolved and required to be a
directory; the tracked-file list comes from git ls-files run there. The
default --repo is the current directory, so a consumer runs it from its own
root as `python3 ../go-shared/scripts/check_disclosure.py --repo .` (D3).

--self-test ports the assertions of prepare-commit-msg's
scripts/test_check_disclosure.py at the same commit to the functions of
this file. It writes nothing outside a scratch directory, scans no
repository and needs no git; it prints one line per case.

Usage:
  check_disclosure.py [--repo DIR]
  check_disclosure.py --self-test

Exit status: 0 no finding, 1 a finding, 2 a tool error (an unreadable
tracked file, a --repo that is not a directory, or a git failure), either
kind of problem dominating.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# (prefix bytes, matched case-insensitively?, category); the first prefix
# that yields a finding on a line wins.
PREFIXES = (
    (b"/Users/", False, "macOS home path"),
    (b"/home/", False, "Linux home path"),
    (b"\\users\\", True, "Windows home path"),
    (b"c:/users/", True, "Windows home path"),
)

SEPARATORS = (b"/", b"\\", b" ", b"\t")

# Markdown and prose markup that reaches into a segment from either side.
LEADING_MARKUP = b"([{`'\""
TRAILING_MARKUP = b")]}`'\".,;:!?"


def stripped_segment(segment: bytes) -> bytes:
    """One segment without markup reaching in from either side."""
    while segment[:1] in (b"(", b"[", b"{", b"`", b"'", b'"'):
        segment = segment[1:]
    while segment[-1:] in (b")", b"]", b"}", b"`", b"'", b'"',
                           b",", b".", b";", b":", b"!", b"?"):
        segment = segment[:-1]
    return segment


def is_placeholder(segment: bytes) -> bool:
    """Whether one home-path account segment is a documented placeholder.

    An angle-bracket token never reaches here on a live line: a line
    carrying a full <…> token is a redaction demonstration, accepted
    wholesale before this function decides. Markup without an account
    inside it is not a path occurrence, and is accepted too.
    """
    segment = stripped_segment(segment)
    if not segment or segment == b"~":
        return True
    if segment.startswith(b"$"):
        return True
    if segment.startswith(b"%") and segment.endswith(b"%"):
        return True
    return False


def segment_end(hay: bytes, start: int) -> int:
    """Where the account segment after a prefix stops in one line."""
    end = len(hay)
    for sep in SEPARATORS:
        stop = hay.find(sep, start)
        if stop != -1:
            end = min(end, stop)
    return end


def line_category(line: bytes) -> str | None:
    """The finding category for one line's own bytes, or None."""
    low = line.lower()
    for prefix, insensitive, name in PREFIXES:
        hay = low if insensitive else line
        at = hay.find(prefix)
        while at != -1:
            start = at + len(prefix)
            segment = line[start:segment_end(hay, start)]
            if segment and not is_placeholder(segment):
                return name
            at = hay.find(prefix, at + 1)
    return None


def scan_bytes(data: bytes) -> list[tuple[int, str]]:
    """One (line number, category) pair per affected line of one file."""
    lines = data.splitlines()
    raw = [(line_no, category) for line_no, line in enumerate(lines, 1)
           if (category := line_category(line)) is not None]

    def demonstrates_redaction(line_no: int) -> bool:
        for other in (line_no - 1, line_no, line_no + 1):
            if 1 <= other <= len(lines) and b"<" in lines[other - 1] \
                    and b">" in lines[other - 1]:
                return True
        return False

    return [(line_no, category) for line_no, category in raw
            if not demonstrates_redaction(line_no)]


def tracked_files(repo: Path) -> list[str]:
    """Every path git lists in the repository the caller passed."""
    head = subprocess.run(["git", "ls-files", "-z"], cwd=repo,
                          stdout=subprocess.PIPE, check=True).stdout
    return [os.fsdecode(name) for name in head.split(b"\x00") if name]


def scan_files(paths: list[str] | None = None,
               base: Path = Path(".")) -> tuple[list[str], int, int]:
    """Finding lines, files scanned, and files that could not be read.

    Each path is read under `base`. One line per affected file and line, in
    the form `<path>:<line>: <category>`, never any line content; a file
    that cannot be read yields one line naming nothing but the path, under
    the category `unreadable`.
    """
    names = tracked_files(base) if paths is None else paths
    findings: list[str] = []
    unreadable = 0
    scanned = 0
    for name in names:
        path = Path(base, name)
        try:
            data = path.read_bytes()
        except OSError:
            unreadable += 1
            findings.append(f"{name}: unreadable input (category: unreadable)")
            continue
        scanned += 1
        if b"\x00" in data:
            continue
        seen: set[tuple[int, str]] = set()
        for line_no, category in scan_bytes(data):
            if (line_no, category) not in seen:
                seen.add((line_no, category))
                findings.append(f"{name}:{line_no}: {category}")
    return findings, scanned, unreadable


_ACCOUNT = b"jo"
_PEER = b"pia"
_PLANTED = b"carol"

_INPUT_MACOS = PREFIXES[0][0] + _ACCOUNT + b"/x\n"
_INPUT_LINUX = b"at " + PREFIXES[1][0] + _ACCOUNT + b"/x here\n"
_INPUT_WINDOWS = b"file=C:" + PREFIXES[2][0] + _ACCOUNT + b"\\x.json\n"
_INPUT_WINDOWS_SHARE = b"see \\\\SERVER" + PREFIXES[2][0] + _ACCOUNT + b" too\n"
_INPUT_WINDOWS_FORWARD = PREFIXES[3][0] + _ACCOUNT + b"/AppData\n"
_INPUT_WINDOWS_UPPER = b"and C:" + PREFIXES[2][0].upper() + _ACCOUNT.upper() + b" here\n"

_PLACEHOLDER_INPUTS = (
    PREFIXES[1][0] + b"<user>/notes.md\n",
    PREFIXES[0][0] + b"<user>/Library/Lists\n",
    b"file=C:" + PREFIXES[2][0] + b"<user>\\AppData\n",
    PREFIXES[1][0] + b"~\n",
    PREFIXES[1][0] + b"$HOME/x\n",
    PREFIXES[0][0] + b"${HOME}/y\n",
    b"file=C:" + PREFIXES[2][0] + b"%USERPROFILE%\\cfg\n",
    PREFIXES[1][0] + b"$env:USERPROFILE/z\n",
)

_CONVENTIONS = (b"%USERPROFILE%\\hooks\n"
                b"%LOCALAPPDATA%\\Programs\n"
                b"~/.config/tool/config.json\n"
                b"$HOME/bin\n"
                b"placeholder " + PREFIXES[1][0] + b"<user>/ shapes\n"
                b"\n"
                b"all clean\n")

_LONE_PATTERN_WORDS = b"layouts " + PREFIXES[0][0] + b" and " + PREFIXES[1][0] + b" below\n"
_PROSE_REACH = b"reach " + PREFIXES[0][0] + _ACCOUNT + b" when needed\n"
_LINE_NUMBER_INPUT = (b"clean\n\n" + PREFIXES[3][0] + _ACCOUNT + b"/app\n"
                      + PREFIXES[0][0] + _ACCOUNT + b" and " + PREFIXES[0][0] + _PEER
                      + b"\n")
_BINARY_INPUT = b"\x00" + PREFIXES[0][0] + _ACCOUNT + b"/x\n"

_DEMONSTRATION_SAME_LINE = PREFIXES[1][0] + rb"[^/\s]+" + b'", "' + PREFIXES[1][0] \
    + b"<user>\"\n"
_DEMONSTRATION_KEYED_LINE = (b"file=C:" + PREFIXES[2][0] + _ACCOUNT + b"\\cfg, per"
                             b" the C:" + PREFIXES[2][0] + b"<user> rule\n")
_DEMONSTRATION_EVIDENCE = b"'" + PREFIXES[0][0] + _ACCOUNT + b"/x' != '" \
    + PREFIXES[0][0] + b"<user>/x'\n"
_DEMONSTRATION_ADJACENT = (b'    r"C:' + PREFIXES[2][0] + _PLANTED
                           + b"\\\\AppData /c/Users/" + _PLANTED
                           + b"/go\", ids),\n"
                           b'    r"C:' + PREFIXES[2][0] + b"<user>\\\\AppData"
                           b" /c/Users/<user>/go\")\n")
_BOUNDARY_TEXT = (b"seen: <user> form\n"
                  b"no path on this line\n"
                  + PREFIXES[0][0] + _ACCOUNT + b"/x\n"
                  + b"nothing else\n"
                  + b"again <user>\n")

_SECRET_DIR = b"secret-dir"
_SECRET_INPUT = b"file=C:" + PREFIXES[2][0] + _ACCOUNT + b"\\" + _SECRET_DIR + b"\\name\n"


def scan_files_two_files() -> bool:
    with tempfile.TemporaryDirectory() as name:
        Path(name, "a.md").write_bytes(b"clean\n" + _INPUT_MACOS)
        Path(name, "b.md").write_bytes(PREFIXES[1][0] + _PEER + b"/y\n")
        findings, scanned, unreadable = scan_files(["a.md", "b.md"], Path(name))
    return (findings == ["a.md:2: macOS home path",
                         "b.md:1: Linux home path"]
            and (scanned, unreadable) == (2, 0))


def unreadable_input_is_a_tool_error() -> bool:
    with tempfile.TemporaryDirectory() as name:
        path = Path(name, "locked.md")
        path.write_bytes(PREFIXES[1][0] + _ACCOUNT + b"/x\n")
        path.chmod(0o000)
        try:
            findings, _, unreadable = scan_files(["locked.md"], Path(name))
        finally:
            path.chmod(0o644)
    return (unreadable == 1
            and findings == ["locked.md: unreadable input (category: unreadable)"])


def binary_content_is_skipped() -> bool:
    with tempfile.TemporaryDirectory() as name:
        Path(name, "blob.bin").write_bytes(_BINARY_INPUT)
        findings, scanned, unreadable = scan_files(["blob.bin"], Path(name))
    return (findings, scanned, unreadable) == ([], 1, 0)


def rendered_finding_carries_no_content() -> bool:
    finds = scan_bytes(_SECRET_INPUT)
    rendered = "".join(f"{no}:{category}" for no, category in finds)
    return (finds == [(1, "Windows home path")]
            and _SECRET_DIR.decode() not in rendered
            and _ACCOUNT.decode() not in rendered)


SELF_TEST_CASES = (
    ("a real macOS, Linux and Windows path is found, in both Windows forms "
     "and either case",
     scan_bytes(_INPUT_MACOS) == [(1, "macOS home path")]
     and scan_bytes(_INPUT_LINUX) == [(1, "Linux home path")]
     and scan_bytes(_INPUT_WINDOWS) == [(1, "Windows home path")]
     and scan_bytes(_INPUT_WINDOWS_SHARE) == [(1, "Windows home path")]
     and scan_bytes(_INPUT_WINDOWS_FORWARD) == [(1, "Windows home path")]
     and scan_bytes(_INPUT_WINDOWS_UPPER) == [(1, "Windows home path")]),
    ("placeholder segments pass, tilde, $ and % included",
     all(scan_bytes(line) == [] for line in _PLACEHOLDER_INPUTS)),
    ("the convention block of placeholder lines passes",
     scan_bytes(_CONVENTIONS) == []),
    ("a prefix with no account passes; prose reaches in and stops at "
     "whitespace",
     scan_bytes(_LONE_PATTERN_WORDS) == []
     and scan_bytes(_PROSE_REACH) == [(1, "macOS home path")]
     and scan_bytes(PREFIXES[0][0] + b"/x " + PREFIXES[1][0] + b"  \n") == []),
    ("a line with a full angle-bracket token passes, and the adjacent line "
     "does too",
     scan_bytes(_DEMONSTRATION_SAME_LINE) == []
     and scan_bytes(_DEMONSTRATION_KEYED_LINE) == []
     and scan_bytes(_DEMONSTRATION_EVIDENCE) == []
     and scan_bytes(_DEMONSTRATION_ADJACENT) == []),
    ("the line two away from a token still reports",
     scan_bytes(_BOUNDARY_TEXT) == [(3, "macOS home path")]),
    ("one finding per line, with the source line number",
     scan_bytes(_LINE_NUMBER_INPUT) == [(3, "Windows home path"),
                                        (4, "macOS home path")]),
    ("a NUL byte does not stop the byte scan (scan_files owns the skip)",
     scan_bytes(_BINARY_INPUT) != []),
    ("scan_files reports file, line and category for two files",
     scan_files_two_files()),
    ("an unreadable file is a tool-error finding naming no content",
     unreadable_input_is_a_tool_error()),
    ("a NUL file is scanned and contributes no finding",
     binary_content_is_skipped()),
    ("a rendered finding carries no account and no source-line text",
     rendered_finding_carries_no_content()),
)


def self_test() -> int:
    """The rules of this file on composed inputs, offline; every case must
    give its expected answer. Every payload composes its account segment
    and every path prefix from this module's own prefix table at module
    level, so the source carries no full home-path shape and stays
    scan-clean."""
    for name, ok in SELF_TEST_CASES:
        print(f"self-test {name}: {'ok' if ok else 'FAIL'}")
    return 0 if all(ok for _, ok in SELF_TEST_CASES) else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Check a repository's tracked text for real user-home paths.")
    ap.add_argument("--repo", default=".", help="the repository to scan; default the current directory")
    ap.add_argument("--self-test", action="store_true", help="run the offline self-test and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"check-disclosure: --repo is not a directory: {repo}", file=sys.stderr)
        return 2
    try:
        findings, scanned, unreadable = scan_files(tracked_files(repo), repo)
    except (OSError, subprocess.CalledProcessError) as err:
        print(f"check-disclosure: git ls-files failed: {err}", file=sys.stderr)
        return 2
    for line in findings:
        print(line)
    print(f"disclosure: {scanned} files scanned, {len(findings)} finding(s), "
          f"{unreadable} unreadable")
    if unreadable:
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
