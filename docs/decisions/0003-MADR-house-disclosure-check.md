---
status: accepted
date: 2026-11-17
decision-makers: Project Owner
consulted: "prepare-commit-msg scripts/check_disclosure.py and scripts/test_check_disclosure.py at 72b37c384d122911e69b331ea816a4a32053301d, tree 2715f2d05c56c04d1dd915253e4444e97f9341f6; go-llmprovider-sdk scripts/check_disclosure.py at b407f02da53bedd23393977312a5c12c7dabe4a2; go-tui-lib scripts/check_disclosure.py at dfce61ea7e017bb9f708b811bf93dcc327b389ba; go-selfupdate-lib Makefile disclosure-check at peeled v1.26.3 1dffdc9dee24a7534513dc51c9039408be37c09b; go-shared scripts/check_libs.py at d62e2a2. All read 2026-11-17."
informed: maintainers of repositories that run a home-path disclosure check
---

# House the home-path disclosure check in go-shared

## Context and Problem Statement

Several of the owner's Go repositories scan tracked text for a real user-home path. Each repository currently carries its own copy of that scan, and the copies have already drifted. A fix in one tree does not land in the others. [0001-MADR-scaffold-go-shared-workspace.md](0001-MADR-scaffold-go-shared-workspace.md) created this repository so a shared check lives once and a consumer runs it from a sibling checkout. [0002-MADR-shared-library-compatibility-check.md](0002-MADR-shared-library-compatibility-check.md) is the first tool built that way: `scripts/check_libs.py`, `--repo` defaulting to the current directory, and an offline `--self-test`.

The disclosure scan is the same kind of tool. `prepare-commit-msg` is the copy to derive from. Its `scripts/check_disclosure.py` (191 lines) and `scripts/test_check_disclosure.py` (183 lines) arrived in commit `72b37c384d122911e69b331ea816a4a32053301d`. The record that defines them is `prepare-commit-msg` `docs/decisions/0022-MADR-align-docs-ci-and-disclosure-gates.md`. On 2026-11-17 that repository's HEAD was `2715f2d05c56c04d1dd915253e4444e97f9341f6`, and `git log -1` of those two files was still `72b37c3`.

What that script does, read at that commit:

* `REPO = Path(__file__).resolve().parent.parent`. `tracked_files` runs `git ls-files -z` with that directory as the working directory. `main` scans that repository and no other.
* A finding is one of three categories, from the `PREFIXES` constant: `macOS home path`, `Linux home path`, `Windows home path`. The two Windows prefixes match case-insensitively. The first prefix that yields a finding on a line wins.
* A placeholder account segment passes: empty, `~`, a segment that starts with `$`, and a segment that starts and ends with `%`. A line that contains a full angle-bracket token, and the line on either side of it, passes as a whole.
* One line is printed per file and line, `<path>:<line>: <category>`, then a summary that names no line content. A file with a NUL byte is counted as scanned and skipped. A tracked file that cannot be read is one finding of category `unreadable`.
* Exit 0 is no finding. Exit 1 is a finding. Exit 2 is an unreadable file. A `git` failure is an uncaught `CalledProcessError`, because `tracked_files` uses `check=True`.

`cmp` of that file against the other two copies exited 1 both times. `go-llmprovider-sdk` `scripts/check_disclosure.py` at `b407f02da53bedd23393977312a5c12c7dabe4a2` is 84 lines and sets `ROOT` from `Path(__file__).resolve().parent.parent`. `go-tui-lib` `scripts/check_disclosure.py` at `dfce61ea7e017bb9f708b811bf93dcc327b389ba` is 126 lines and documents `--root`. Those shorter copies are not the source.

`go-selfupdate-lib` at peeled `v1.26.3` has no `scripts/check_disclosure.py`. Its Makefile `disclosure-check` target runs `./scripts/check-docs.sh --ids --ids-optional` over `git ls-files -z`. That is a different program.

`prepare-commit-msg`'s `make verify` is a Makefile aggregate, not a portable script. At HEAD `2715f2d` the recipe is `verify: tools mod-check fmt-check lint vet test coverage vuln workflow-lint tools-test build-all`. `make disclosure-check` is a separate target and runs `scripts/check_disclosure.py`. `scripts/verify-scripts.sh` is 27 lines: it syntax-checks `scripts/` and `tools/*.py`, runs actionlint on `.github/workflows/*.yml`, and runs `scripts/check_ci_filters.py`. A consumer's `verify` target names that consumer's own tools. It is not something this repository can ship as one file.

Moving the disclosure script unchanged would scan the wrong tree. `parent.parent` of a file in this repository is this repository. The consumer's files would never be read. `check_libs.py` already solved that for its own check: `--repo` defaults to `.`, and `--self-test` runs offline.

A scratch git repository, created outside either tree on 2026-11-17, had one markdown file of its own and a nested git directory containing another markdown file. `git ls-files -z --cached --others --exclude-standard -- '*.md'` listed only the outer file. `git status` listed the nested directory as untracked. This repository's disclosure scan uses `git ls-files -z` of the `--repo` the caller passes, so a second checkout is scanned only when it is that `--repo`.

## Decision Drivers

* **One implementation.** A fix to the home-path rules lands once. Every consumer runs the same file.
* **The consumer chooses the tree.** The script scans the repository it is pointed at. Living in this repository must not make it scan this repository.
* **Keep the rules `prepare-commit-msg` already proved.** The prefixes, the placeholder rules, the angle-bracket window, the NUL skip, the unreadable-file result, and the output that contains no line content stay. The unittest at `72b37c3` is the list of cases.
* **Standard-library Python 3 only.** The same bar as `check_libs.py`. No package install.
* **A consumer's `make verify` stays in the consumer.** Coverage thresholds, vuln scanners, actionlint, and release builds differ per repository. This repository has no Makefile and no CI workflow.

## Considered Options

* **A. House one script here, derived from `prepare-commit-msg`, with `--repo` and `--self-test`.** Consumers run it from a sibling checkout. A consumer Makefile may wrap it. The wrapper is that consumer's decision.
* **B. Copy `prepare-commit-msg`'s script into each consumer.**
* **C. Treat `go-selfupdate-lib`'s `check-docs.sh --ids` as the shared disclosure check.**
* **D. Also house `verify-scripts.sh` and the `prepare-commit-msg` `verify` recipe as shared programs.**

## Decision Outcome

Chosen option: "A. House one script here, derived from `prepare-commit-msg`, with `--repo` and `--self-test`.", because the scan is one program with one set of rules, and the repository boundary is the same `--repo` flag `check_libs.py` already uses. B is the drift this repository exists to stop. C is a different checker. D packages a consumer's tool list as if it were portable.

### The decisions

* **D1 — `scripts/check_disclosure.py`, standard-library Python 3 only.** It is derived from `prepare-commit-msg` `scripts/check_disclosure.py` at `72b37c384d122911e69b331ea816a4a32053301d`. The docstring names that source and that repository's `0022-MADR-align-docs-ci-and-disclosure-gates.md`. The script holds no hostname, account name, or machine path.
* **D2 — `--repo` is the tree that is scanned.** It defaults to the current directory, the same default as `check_libs.py`. Tracked files come from `git ls-files -z` run in that directory. The scan root is that directory. `Path(__file__).resolve().parent.parent` is not the scan root.
* **D3 — How a consumer runs it.** From the consumer's root: `python3 ../go-shared/scripts/check_disclosure.py --repo .`. A consumer may wrap that in `make disclosure-check` with `GO_SHARED ?= ../go-shared`. The wrapper, and any `make verify` that calls it, belong to the consumer's own record. This repository does not grow a Makefile for that wrapper.
* **D4 — `--self-test` is offline.** It ports the cases in `scripts/test_check_disclosure.py` at the same commit: real paths in each category, placeholder segments, the angle-bracket window including the adjacent line, the line one past that window, one finding per line, `scan_files` per file, an unreadable file, a NUL skip, and a rendered finding that contains no source text. Exit 0 is every case passing. Exit 1 is any case failing. `--self-test` does not scan a repository and does not need `git`.
* **D5 — Results.** Exit 0 is no finding. Exit 1 is one or more findings. Exit 2 is a tool error: an unreadable tracked file, a `--repo` that is not a directory, or a `git` failure. A tool error is printed to stderr and is not a traceback. The source script already returns 2 for an unreadable file and lets a `git` failure raise; catching that failure is the change that makes exit 2 match the docstring. A NUL file is scanned and contributes no finding. Output stays `<path>:<line>: <category>` plus the summary line that names counts only.
* **D6 — `verify` is not this script.** `scripts/verify-scripts.sh` is not copied. actionlint, `check_ci_filters.py`, coverage, and govulncheck are not added here. A consumer that wants `make verify` writes that target in its own Makefile and decides which of its existing targets belong in the list.
* **D7 — CI checkouts are the consumer's record.** A GitHub-hosted runner has no sibling checkout. The consumer's workflow checks out this public repository at a commit, with `persist-credentials: false`, into a path outside the consumer tree, and passes that path as `--repo`'s neighbor through `GO_SHARED`. The pin is the commit that contains this script. This repository still has no workflow of its own.

### Confirmation

Compliance is the completion criteria of [0003-PLAN-house-disclosure-check.md](0003-PLAN-house-disclosure-check.md). The script is absent until that plan is executed. `docs/architecture.md` describes the tools that exist today, so it gains this script in that same implementation and not before.

Accepted 2026-11-17. That plan has written `scripts/check_disclosure.py`, and the sentence above is the state before it ran.

## Consequences

* Good, because a rule change is one edit in `scripts/check_disclosure.py`, and every consumer that points at a sibling checkout runs it.
* Good, because `--repo .` scans the consumer. A checkout of this repository beside the consumer is a tool directory, and `git ls-files` of the consumer does not list it.
* Good, because `--self-test` needs no network and no consumer tree, which is the gate this repository can run on the script itself.
* Neutral, because each consumer still writes its own `make disclosure-check` and its own `make verify`. Those lines are short. The rules they invoke are not copied.
* Neutral, because the shorter copies in `go-llmprovider-sdk` and `go-tui-lib` stay until those repositories adopt this script in their own records. This decision does not edit them.
* Bad, because a consumer workflow has to pin a commit of this repository. Until the implementing commit exists, that pin has no hash to write down.
* Bad, because `parent.parent` in the source file is wrong for a shared location. An unmodified copy would report a clean consumer while scanning this tree.

## Pros and Cons of the Options

### A. House one script here, derived from `prepare-commit-msg`, with `--repo` and `--self-test`

* Good, because the 191-line script and its 183-line unittest are the longest copy and the one `0022-MADR` defines.
* Good, because `--repo` and `--self-test` are the interface `check_libs.py` already documents for a sibling checkout.
* Neutral, because the consumer still names `GO_SHARED` and still chooses what `make verify` depends on.
* Bad, because the first consumer cannot pin a workflow `ref` until this plan's implementing commit exists.

### B. Copy `prepare-commit-msg`'s script into each consumer

* Good, because each repository would then run without a second checkout.
* Bad, because the three copies that exist today already differ, at 191, 126, and 84 lines, so the next copy would drift the same way.
* Bad, because [0001-MADR-scaffold-go-shared-workspace.md](0001-MADR-scaffold-go-shared-workspace.md) exists so that a fix lands once.

### C. Treat `go-selfupdate-lib`'s `check-docs.sh --ids` as the shared disclosure check

* Good, because that target already runs in the library's own Makefile.
* Bad, because it is `check-docs.sh`, and the library tree has no `scripts/check_disclosure.py`. The categories, the angle-bracket window, and the unittest at `72b37c3` belong to the Python script.
* Bad, because taking it would replace a defined check with a different one.

### D. Also house `verify-scripts.sh` and the `prepare-commit-msg` `verify` recipe

* Good, because `prepare-commit-msg` runs that recipe as its quality gate.
* Bad, because the recipe names `tools`, coverage, govulncheck, `workflow-lint`, `tools-test`, and `build-all`. Those targets are that repository's. `verify-scripts.sh` requires `tools/*.py`, actionlint, and `check_ci_filters.py`.
* Bad, because this repository has no Makefile and no `.github` workflow. Adding them to carry one consumer's tool list would invent a CI this record does not need.

## More Information

* Charter and the sibling-checkout rule: [0001-MADR-scaffold-go-shared-workspace.md](0001-MADR-scaffold-go-shared-workspace.md).
* The `--repo` / `--self-test` pattern this record repeats: [0002-MADR-shared-library-compatibility-check.md](0002-MADR-shared-library-compatibility-check.md).
* Source record, cited by repository and filename because a relative link cannot cross repositories: `prepare-commit-msg` `docs/decisions/0022-MADR-align-docs-ci-and-disclosure-gates.md` and `docs/decisions/0022-PLAN-align-docs-ci-and-disclosure-gates.md`, at commit `72b37c384d122911e69b331ea816a4a32053301d`.
* Implementation plan: [0003-PLAN-house-disclosure-check.md](0003-PLAN-house-disclosure-check.md).
* The first consumer is `mcp-server-duckduckgo` `docs/decisions/0008-MADR-adopt-go-selfupdate-lib-v1.26.3.md`. That record decides that repository's `make verify` list. This record does not edit that repository.
