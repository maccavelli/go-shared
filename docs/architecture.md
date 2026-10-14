# Architecture

How this repository is put together, as it is now. This file carries no
history and no rationale — when you want to know *why* something is this
way, the decision records under [decisions/](decisions/) hold the argument,
and [README.md](README.md) points at the ones people ask for most.

## What it is

go-shared holds the scripts and tools that the owner's Go repositories share: repository-level
checks and helpers that more than one repository runs, so a fix lands once. A consuming repository
runs a tool from a sibling checkout of this repository, and adopts it in its own records.

## Tree

```text
README.md                 repository entry; links here
AGENTS.md                 agent instructions
LICENSE                   Apache License 2.0
.markdownlint-cli2.jsonc  fleet Markdown style
.gitattributes            LF on every platform
scripts/check_records.py  record numbering and link check
scripts/check_libs.py     library-compatibility check, run against a consuming repository
docs/
  README.md               ToC and the "I want to…" matrix
  architecture.md         this file
  decisions/              MADR/PLAN pairs
  reports/                numbered observations (not created yet)
  guides/                 unnumbered how-to documents (not created yet)
```

## Tools

### `scripts/check_libs.py`

Checks a Go repository against the latest semver tag of each library its `check_libs.json` names.
From the consuming repository's root:

```bash
python3 ../go-shared/scripts/check_libs.py --repo .
```

It clones the consumer's committed `HEAD` into a scratch directory, then for each library runs
`go get` and `go mod tidy`, `go build`, `go vet` for linux, darwin and windows, `go test` on the
configured packages, apidiff from the pinned version, govulncheck, and the library's GitHub
security advisories. It needs the network. `--self-test` runs offline. Exit 0 is all checks
passing, 1 is a failing check, and 2 is a usage or config error. Why it is built this way:
[0002-MADR-shared-library-compatibility-check.md](decisions/0002-MADR-shared-library-compatibility-check.md).

## What is not here

- No `Makefile`; the gates run as plain commands, listed in `AGENTS.md`.
- No CI workflow.
- No Go module: nothing here is imported at build time.
