---
status: accepted
date: 2026-10-13
decision-makers: Project Owner
consulted: none
informed: maintainers of magic-cli-remote and gobble-cli
---

# Ship one library-compatibility check, `scripts/check_libs.py`, that any Go repository runs against its own libraries

## Context and Problem Statement

The owner's libraries (`acp-go-sdk2`, `go-selfupdate-lib`, `go-llmprovider-sdk`) tag several
times a day. A consuming repository needs to know, before it moves a pin, whether the newest tag
will hurt it:

* whether it builds;
* whether it changes the API;
* whether it moves another module;
* whether it carries a security advisory.

`gobble-cli` wrote that check as `scripts/check_libs.py` (its
`docs/decisions/0019-MADR-sibling-libraries-current-pins-and-integration.md`, D14).
`magic-cli-remote` needs the same check
(`docs/decisions/0186-MADR-integrate-current-library-releases-and-prepare-gobble.md`, D7). The owner
decided on 2026-10-13 that it lives here
([0001-MADR-scaffold-go-shared-workspace.md](0001-MADR-scaffold-go-shared-workspace.md)).

gobble's script, read at `gobble-cli` `007b63f`, is specific to gobble in four places:

* **Libraries.** Its three libraries, and the packages each is tested through, are a constant
  (`LIBRARIES`).
* **Toolchain.** The toolchain is fixed at `GOTOOLCHAIN=go1.27.2`.
* **Tools.** It runs `apidiff` by `go build golang.org/x/exp/cmd/apidiff`, and `govulncheck` by
  `go tool govulncheck`. Both depend on `tool` directives in gobble's own `go.mod`. A repository
  without those directives cannot run it, and `magic-cli-remote` has none.
* **Repository root.** It finds the repository as the script's own parent directory.

Everything else carries over unchanged:

* its checks;
* its rule that a tag is never a branch;
* its scratch clone outside the working tree;
* its removal of credential-shaped variables from every command's environment;
* its offline self-test.

## Decision Drivers

* **One implementation.** A fix to the check lands once, and every consumer gets it.
* **The consumer decides what is checked.** The library list and test packages belong to the
  repository that imports them.
* **Run on any consumer, without changing its `go.mod`** to add tool directives.
* **Never write the consumer's working tree,** and never read or send a credential.
* **Each verdict is real.** The checks that failed silently before stay closed:
  * apidiff's exit status is not its verdict, so its text is read;
  * `govulncheck` cannot see a GitHub-only advisory, so the advisories are read separately;
  * `go build` alone misses a test-only import, so `vet` and `test` run too.

## Considered Options

* **A. Generalize gobble's script: a per-consumer config file, the consumer's toolchain, and pinned
  tool versions run with `go run`** (chosen).
* **B. Copy gobble's script into each consumer, edited per repository.**
* **C. Rewrite the check as a Go program** in this repository.

## Decision Outcome

Chosen option: "**A. Generalize gobble's script**", because it keeps every check gobble's records
proved, while removing the four gobble-specific assumptions. B is what the owner rejected by
creating this repository. C would change working, tested code for no new capability, and would
need a Go module and its own release here.

### The decisions

* **D1 — `scripts/check_libs.py`, standard-library Python 3 only.** It is derived from
  `gobble-cli`'s `scripts/check_libs.py` at `007b63f`, which has the same owner. The script's
  docstring names that source.
* **D2 — The consumer supplies `check_libs.json` at its root.** The file holds one entry per
  library: its module path and the packages to test through it. For example:

  ```json
  {"libraries": [
    {"module": "github.com/maccavelli/acp-go-sdk2", "packages": ["./internal/provider/acpagent/..."]}
  ]}
  ```

  The repository URL comes from the module path. A missing or malformed file is a usage error, exit
  2, with a message naming the file.
* **D3 — How it is run.** From the consumer's root:
  `python3 ../go-shared/scripts/check_libs.py --repo .`. `--repo` defaults to the current
  directory.
  * A consumer may wrap this in `make check-libs`, with `GO_SHARED ?= ../go-shared`. That is the
    consumer's own record's choice.
  * A sibling checkout is chosen over downloading a pinned copy. The repositories already sit side
    by side, and the check needs the network either way. A download would need its own integrity
    pin.
  * `--config PATH` overrides the file location, so the check can be tried on a repository without
    writing to it.
* **D4 — The consumer's toolchain.** `GOTOOLCHAIN` is taken from the consumer's `go.mod`: its
  `toolchain` line, otherwise its `go` line. `CGO_ENABLED=0` stays, as in gobble.
* **D5 — Tools without `tool` directives.** apidiff and govulncheck run as the consumer's
  `go tool <name>` when its `go.mod` declares them. Otherwise they run with `go run <path>@<version>`,
  at versions pinned as constants in the script:
  * `golang.org/x/exp` has no tags, so apidiff is pinned to the pseudo-version gobble's `go.mod`
    selects (`v0.0.0-20260908205506-85c1c2202aba`);
  * govulncheck is pinned to the newest `golang.org/x/vuln` tag at implementation time. The PLAN
    records which tag that is.

  A tool's pin moves only by an amendment to this record.
* **D6 — The checks are gobble's D14, unchanged.** For each library:
  * latest semver tag, never a branch;
  * a scratch clone of the consumer outside its tree;
  * `go get` and `go mod tidy`, failing if tidy settles on another version or moves another module;
  * `go build ./...`, and `go vet ./...` for linux, darwin and windows;
  * `go test -count=1` over the configured packages;
  * apidiff from the pinned version to the tag. An incompatible change fails a v1 module, and is
    reported but not failed below v1;
  * govulncheck;
  * the library's published GitHub security advisories against the tag.

  Credential-shaped variables are removed from every command. Logs stay in a scratch directory,
  kept on failure. Exit status 1 when any check fails.
* **D7 — Not part of any offline gate.** It needs the network. A consumer runs it before moving a
  pin and on demand, never in `preflight` or pre-add.
* **D8 — The self-test stays, and grows.** `--self-test` runs gobble's parser cases, plus new cases
  for the config reader (D2) and the toolchain reader (D4). It is offline, and it is this
  repository's pre-add gate for the script, added to `AGENTS.md`'s pre-add list in the same
  change.
* **D9 — Adoption is each consumer's decision.**
  * `magic-cli-remote` adopts the check under its 0186 PLAN.
  * `gobble-cli` keeps its own copy until its own records move it here.
  * This repository never writes to a consumer.

### Consequences

* Good, because one script serves every repository, and its fixes land once.
* Good, because a consumer needs only a small config file. Its `go.mod` is untouched.
* Good, because every check gobble's records proved, and every negative control, carries over.
* Bad, because a consumer depends on a sibling checkout being present and current. A stale checkout
  runs an old check, and nothing pins which revision a consumer used.
* Bad, because `go run <tool>@<version>` downloads the tool on first use, and the apidiff pin is a
  pseudo-version, since `golang.org/x/exp` publishes no tags.
* Neutral, because gobble's copy and this one can drift until gobble adopts this one.

### Confirmation

* `python3 scripts/check_libs.py --self-test` exits 0. On a scratch copy with one parser broken, it
  exits 1.
* A run against `gobble-cli` with a scratch config passed by `--config` reproduces gobble's own
  verdicts for its three libraries. Nothing is written to `gobble-cli`.
* A run with no config exits 2, naming the missing file.
* `git status --porcelain` in the consumer is unchanged by any run.
* `python3 scripts/check_records.py --check-all` and markdownlint exit 0.

## Pros and Cons of the Options

### A. Generalize gobble's script

* Good, because the proved checks carry over, and the four gobble-specific assumptions go.
* Bad, because the consumer needs a sibling checkout.

### B. Copy into each consumer

* Good, because each repository is self-contained.
* Bad, because copies drift, and a fix must be made once per repository. The owner chose against
  it.

### C. A Go program

* Good, because it would be in the fleet's main language.
* Bad, because it rewrites working code, and adds a module and a release here for no new check.

## Amendment — 2026-10-13: found while implementing P1

Two behaviors this record did not state, recorded before P1 closes:

* **A library the consumer does not require is a failing `required` check.**
  * If the consumer's `go.mod` does not require a configured library, `go mod tidy` would drop the
    `go get` again, since nothing imports it. Any verdict after that would be about nothing.
  * So the script reports `required: FAIL … does not require <module>; nothing to check` for that
    library, and moves on.
  * The PLAN's expected "`acp-go-sdk2` build failures" for `magic-cli-remote` were wrong for this
    reason. That repository imports the Coder module today, not `acp-go-sdk2`.
* **The check runs on the consumer's committed `HEAD`.** As in gobble's script, the scratch copy
  is a `git clone` of the consumer, so uncommitted changes are not checked. The pinned version is
  read from that commit's `go.mod`.

## More Information

* [0002-PLAN-shared-library-compatibility-check.md](0002-PLAN-shared-library-compatibility-check.md):
  this record's plan.
* Source: `gobble-cli` `scripts/check_libs.py` and its
  `docs/decisions/0019-MADR-sibling-libraries-current-pins-and-integration.md` (F2, F12, D14).
  Repository names are given because a relative link cannot reach another repository.
