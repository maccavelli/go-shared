---
status: complete
date: 2026-10-13
associated-madr: "0002-MADR-shared-library-compatibility-check.md"
---

# Implement the shared library-compatibility check

Associated MADR: [0002-MADR-shared-library-compatibility-check.md](0002-MADR-shared-library-compatibility-check.md)

**Not approved for execution.** P1 starts on the owner's "proceed" or "do 0002 P1", and only after
the owner has committed the 0001 scaffold, so the scaffold commit carries no source.

## Goal

`scripts/check_libs.py` runs the MADR's checks against any Go repository that supplies
`check_libs.json`, and its self-test is this repository's pre-add gate for it.

## Scope

P1 may create or change only:

* `scripts/check_libs.py` (new);
* `AGENTS.md`'s pre-add section, to add `python3 scripts/check_libs.py --self-test`;
* `docs/architecture.md`, to list the tool;
* `docs/README.md`, to update the 0002 rows' status;
* this PLAN, for its execution record.

Nothing is written to any consuming repository.

## Implementation Steps

### P1 — Write, prove and stage the script

1. Start from `gobble-cli` `scripts/check_libs.py` at `007b63f`. Name the source in the docstring.
2. Replace the gobble-specific parts (MADR D2–D5):
   * `LIBRARIES` becomes a reader for `check_libs.json`, or `--config`;
   * `REPO` becomes `--repo`, defaulting to the current directory;
   * the toolchain comes from the consumer's `go.mod`;
   * apidiff and govulncheck run through `go tool` when declared, and `go run <path>@<pin>`
     otherwise.
3. Pin govulncheck to the newest `golang.org/x/vuln` tag that `go list -m -versions
   golang.org/x/vuln` reports, and record it in this PLAN's execution record. Pin apidiff to the
   MADR's pseudo-version.
4. Extend `--self-test` (MADR D8). Add the config reader's cases: valid, missing file, malformed
   JSON, and an entry without `module`. Add the toolchain reader's cases: a `toolchain` line, a `go`
   line only, and neither.
5. Update `AGENTS.md`'s pre-add list and `docs/architecture.md`.
6. Run the verification, then `git add` the P1 files. Do not commit.

## Verification

Exit status recorded before reading output:

```bash
python3 scripts/check_libs.py --self-test        # expect 0
python3 scripts/check_records.py --check-all
npx --yes markdownlint-cli2@0.23.2
```

* **Fail first.** On a scratch copy, break one parser so it returns a wrong answer. `--self-test`
  must exit 1 and name the case.
* **Usage errors.** With no config, the script exits 2 and names the missing file.
* **A real run.** Run against `gobble-cli` with a scratch `check_libs.json` passed by `--config`,
  listing its three libraries and the packages gobble's own script uses. Then:
  * its verdicts are compared with gobble's own `make check-libs` run the same day;
  * `git -C <gobble-cli> status --porcelain` is identical before and after.
  * This uses the network and no provider quota.
* **A second consumer.** Run against `magic-cli-remote` with a scratch config. Its
  `acp-go-sdk2` build failures are expected, and recorded as the check working (that repository's
  0186 MADR measured them). Its tree is unchanged.
* **Identifiers.** A scan of the added files finds no account name, host name or real-machine path.

## Rollout and Rollback

* Before the owner commits: unstage and delete the script.
* After a push, a fix is a new commit under an amendment.
* Consumers adopt the script under their own records, so removing it here breaks only a consumer's
  optional `make check-libs`.

## Execution record

### P1, 2026-10-13

Approved by the owner: "proceed with 0001, scaffold, then proceed to 0002 P1".

**Done.**

* `scripts/check_libs.py` was written from `gobble-cli`'s at `007b63f`, and its docstring names the
  source.
* The gobble-specific parts were replaced as MADR D2–D5 say:
  * the libraries come from `check_libs.json`, or `--config`;
  * the repository comes from `--repo`;
  * `GOTOOLCHAIN` comes from the consumer's `go.mod`;
  * apidiff and govulncheck run as `go tool` when the consumer declares them, and pinned otherwise.
* **Pins:** govulncheck `v1.9.0`, the newest that `go list -m -versions golang.org/x/vuln`
  reported. apidiff at `golang.org/x/exp` `v0.0.0-20260908205506-85c1c2202aba`.
* The self-test grew from 9 cases to 22: config, toolchain, tool-directive and govulncheck-routing
  cases.
* `AGENTS.md`'s pre-add list, `docs/architecture.md` and `docs/README.md` were updated.

**Deviations.**

* **2026-10-13, step 6: not staged.**
  * The scaffold is staged and not yet committed. The owner's organization does not allow the agent
    to commit on `main`, so the owner commits it.
  * Staging P1's files now would put source into the scaffold's commit, which the bootstrap
    exception forbids.
  * So every P1 change stays in the working tree only. The owner commits the staged scaffold first
    (`git commit --no-edit`), then stages P1, which is `git add -A` once the scaffold is committed.
  * The index still holds the scaffold's copies of `AGENTS.md`, `docs/README.md`,
    `docs/architecture.md` and the 0002 records. Their working-tree versions carry P1's changes.
* **2026-10-13, verification: the `magic-cli-remote` run.** The plan expected `acp-go-sdk2` build
  failures. Instead, that repository requires neither library yet, so both report `required: FAIL`,
  as designed. The MADR's amendment records why.
* **2026-10-13, implementation: the pin is read from `HEAD`.** The first draft read the pinned
  version from the consumer's working tree, while the check clones `HEAD`. It now reads `go.mod`
  from `HEAD` (`git show HEAD:go.mod`), as the MADR's amendment states.

**Verification,** each exit status recorded before reading its output:

```text
python3 scripts/check_libs.py --self-test        exit=0   22 of 22 ok
python3 scripts/check_records.py --check-all     exit=0
markdownlint-cli2 (repository config)            exit=0   5 files, 0 issues
```

Fail first, on scratch copies of the script. Each broken parser makes `--self-test` exit 1 and name
its case:

| Plant | Failing case |
| :--- | :--- |
| toolchain default `.0` removed | "a two-part go line is its .0 release" |
| incompatible-line marker changed | "an incompatible line fails" |
| config module check disabled | "an entry without module is refused" |
| tool block reader disabled | "tool directives are read" |

Real runs (network, no provider quota):

* **No config:** exit 2, `…/check_libs.json: not found; the repository must supply check_libs.json`.
* **`gobble-cli` with a scratch config** (its three libraries and its script's packages): exit 0.
  * Every check is ok for `acp-go-sdk2 v0.17.1`, `go-llmprovider-sdk v1.12.0` and
    `go-selfupdate-lib v1.15.2`: get and tidy, version, modules, build, vet on three systems, test,
    govulncheck and advisories.
  * Each was already pinned at its latest tag, so apidiff had nothing to compare.
  * gobble's `git status --porcelain` was identical before and after.
  * gobble's own `make check-libs` was not run for comparison. Its records pin all three at these
    tags, which agrees.
* **apidiff and govulncheck at their pins,** through a harness calling the script's functions
  with a consumer that declares no tools:
  * `go install` built apidiff at the pin;
  * `go-selfupdate-lib` `v1.14.0`→`v1.15.2` was ok;
  * the reverse, `v1.15.2`→`v1.14.0`, failed with 2 incompatible changes
    (`taskscheduler.ErrTaskDisabled: removed` first). That is the negative control;
  * `govulncheck@v1.9.0` on a clone of `go-selfupdate-lib` reported "No vulnerabilities found."
* **`magic-cli-remote` with a scratch config:** exit 1. Both libraries reported `required: FAIL`
  (see the deviation), and its tree was unchanged.
* **Identifiers.** A scan of the working tree's 23 files found no account name, hostname, home path
  or e-mail domain. A planted identifier was found.
