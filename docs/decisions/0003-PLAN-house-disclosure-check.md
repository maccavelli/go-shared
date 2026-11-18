---
status: complete
date: 2026-11-17
associated-madr: "0003-MADR-house-disclosure-check.md"
---

# Implement the shared home-path disclosure check

Associated MADR: [0003-MADR-house-disclosure-check.md](0003-MADR-house-disclosure-check.md)

The owner accepted the MADR and approved this plan on 2026-11-17. P1 is the execution record below.

## Goal

`scripts/check_disclosure.py` scans the repository named by `--repo` for a real user-home path, using the rules in the associated MADR, and `--self-test` covers those rules offline.

## Scope

P1 may create or change only:

* `scripts/check_disclosure.py` (new);
* `AGENTS.md`, one sentence beside the `check_libs.py` pre-add line, requiring `python3 scripts/check_disclosure.py --self-test` before a commit that touches this script;
* `docs/architecture.md`, a Tools subsection for the script, written only once the file exists;
* `docs/README.md` and `README.md`, status text for this pair once the decision is accepted;
* this PLAN, for its execution record.

Nothing is written to a consuming repository. `mcp-server-duckduckgo` adopts the script in its own 0008 plan. `scripts/verify-scripts.sh` is not added. No Makefile and no workflow are added.

## Implementation Steps

### P1 — Write the script and prove `--self-test`

1. Start from `prepare-commit-msg` `scripts/check_disclosure.py` at `72b37c384d122911e69b331ea816a4a32053301d`. Name that source and `0022-MADR-align-docs-ci-and-disclosure-gates.md` in the docstring.
2. Replace the scan root (MADR D2). Delete the assignment that sets the repository from `Path(__file__).resolve().parent.parent`. Add `--repo`, default `.`. Resolve it, require a directory, and run `git ls-files -z` with that directory as the working directory. Pass that directory as the base `scan_files` already accepts. A missing directory and a `git` failure print to stderr and return 2 (MADR D5).
3. Add `--self-test`. When it is set, run the cases below and return. Do not call `git`. Port the assertions from `prepare-commit-msg` `scripts/test_check_disclosure.py` at the same commit, retargeted at the functions in this file:
   * a real path in each of `macOS home path`, `Linux home path`, and `Windows home path`, including the backslash form, the forward-slash form, and the upper-case Windows form;
   * placeholder segments pass, including `~`, a `$` segment, and a `%…%` segment;
   * a line with a full angle-bracket token passes, and so does the adjacent line;
   * the line two away from that token still reports;
   * one finding per line, with the source line number;
   * `scan_files` reports `<path>:<line>: <category>` for two files;
   * an unreadable file increments the unreadable count and returns a finding whose category is `unreadable`;
   * a NUL file is scanned and adds no finding;
   * the rendered finding text does not contain the account segment or the rest of the source line.
4. `--self-test` returns 0 when every case passes and 1 when any case fails. Follow the shape of `self_test` in `scripts/check_libs.py`: print one line per case, and do not discover a second test file.
5. Keep `PREFIXES`, the placeholder function, the angle-bracket window, the NUL skip, and the summary line that names counts only. The summary stays free of line content.
6. On a scratch copy of the script, outside this tree, break one case so a known real path is treated as clean. `--self-test` on that copy must exit 1 and name the case. Restore nothing in this tree from that copy. Record the failure text in the execution record.
7. Run `python3 scripts/check_disclosure.py --self-test` here. It exits 0.
8. Run `python3 scripts/check_disclosure.py --repo .` here. It exits 0. Then run it with `--repo` pointed at a missing path. It exits 2 and names the path.
9. Update `docs/architecture.md` so the Tools section describes the script, the `--repo .` invocation from a sibling checkout, the exit codes, and a link to the MADR. The description matches the file that was just written.
10. Add the `AGENTS.md` pre-add sentence from Scope.
11. Run `python3 scripts/check_records.py --check-all` and `npx --yes markdownlint-cli2@0.23.2`. Both exit 0. Search the changed files for a home directory, an account name, and a machine path. A hit is a stop. Describe the search in the execution record.

The implementing commit's hash is whatever `git rev-parse HEAD` prints after the owner commits. This plan does not reserve a hash. A consumer that pins a workflow `ref` reads that commit after it exists.

## Verification

* `python3 scripts/check_disclosure.py --self-test` exits 0, and the planted broken copy exited 1 before that.
* `python3 scripts/check_disclosure.py --repo .` exits 0 and prints a summary whose finding count is 0.
* `python3 scripts/check_disclosure.py --repo` of a missing directory exits 2.
* A search of `scripts/check_disclosure.py` finds no assignment of the scan root from `__file__`.
* `docs/architecture.md` names `scripts/check_disclosure.py` and `--repo`.
* `python3 scripts/check_records.py --check-all` and `npx --yes markdownlint-cli2@0.23.2` exit 0.

## Rollout and Rollback

Rollout is the commit the owner makes with `git commit --no-edit`. Do not push unless the owner asks in that turn. Consumers pick up the script when their own records say so.

Rollback, before any consumer pins the commit: delete `scripts/check_disclosure.py`, restore `AGENTS.md` and `docs/architecture.md`, and return this pair's status text. After a consumer has pinned the commit, rollback is a new commit plus that consumer's own plan. Do not rewrite history.

## Execution record

P1 ran on 2026-11-17. An earlier draft of this sentence named 2026-11-18. The session date is 2026-11-17. The owner approved the plan on this date, after the script was already in the working tree.

* `scripts/check_disclosure.py` was written per D1–D5, derived from
  `prepare-commit-msg` `scripts/check_disclosure.py` at commit
  `72b37c384d122911e69b331ea816a4a32053301d` (its
  `docs/decisions/0022-MADR-align-docs-ci-and-disclosure-gates.md`), cited in the
  docstring. No file outside the Scope list changed; `docs/README.md` and `README.md`
  gain no status text yet, because the decision is not accepted.
* Step 6, the planted break: on a scratch copy of the script outside this tree,
  `is_placeholder` was patched to accept one planted account segment, so a known real
  path was treated as clean. `--self-test` on that copy exited 1 and named its cases;
  the first line of that output:
  `self-test a real macOS, Linux and Windows path is found, in both Windows forms and either case: FAIL`.
  The tree was untouched by the experiment, and nothing was restored from the copy.
* Steps 7–8: `python3 scripts/check_disclosure.py --self-test` here exited 0, all
  twelve cases `ok`; `python3 scripts/check_disclosure.py --repo .` here exited 0
  (`disclosure: 21 files scanned, 0 finding(s), 0 unreadable`); `--repo` pointed at a
  missing path exited 2 and named the resolved path.
* Step 9–10: `docs/architecture.md` gained the tree line and the Tools subsection,
  and `AGENTS.md` gained the pre-add sentence from Scope.
* Step 11: `python3 scripts/check_records.py --check-all` and
  `npx --yes markdownlint-cli2@0.23.2` were run after this record was written; both
  exited 0. The changed files (`scripts/check_disclosure.py`, `docs/architecture.md`,
  `AGENTS.md`, this PLAN) were searched for a home directory in the macOS, Linux and
  Windows forms with a concrete account segment, for the local account name, and for
  the machine's host name: no hit of any kind, so no stop.

### Acceptance 2026-11-17

The owner accepted the MADR and approved this plan on this date. The MADR frontmatter is `accepted`. This plan's frontmatter is `complete`. `docs/README.md` lists those two statuses. The root `README.md` already links this MADR from its "I want to…" table and has no status column, matching the 0002 row.

Re-ran on this date, from this repository: `python3 scripts/check_disclosure.py --self-test` exited 0, twelve cases `ok`. `python3 scripts/check_disclosure.py --repo .` exited 0 and printed `disclosure: 21 files scanned, 0 finding(s), 0 unreadable`. A missing `--repo` exited 2 and printed `check-disclosure: --repo is not a directory:` plus the resolved path. A search of `scripts/check_disclosure.py` finds no `Path(__file__)` assignment. `python3 scripts/check_records.py --check-all` exited 0. `npx --yes markdownlint-cli2@0.23.2` exited 0, 5 files, 0 issues. The changed files were searched for `/Users/`, `/home/`, a Windows users prefix, the local account name, and the machine's host name. The only hits are the script's prefix constants, its `<name>` and `<user>` examples, the synthetic self-test segments, and the placeholder in `AGENTS.md`. The local account name and the host name had no hit.

Rollout is still the owner's `git commit --no-edit` of the Scope paths. This plan does not stage the pre-existing 0001 and 0002 plan edits, and it does not push. The implementing commit's hash is whatever `git rev-parse HEAD` prints after that commit. This file does not reserve a hash.
