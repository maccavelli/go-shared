# AGENTS.md

Instructions for AI coding agents working in this repository. All agents read
this file. A repository-local `CLAUDE.md` / `.claude/rules/` / `.grok/rules/` /
`.opencode/rules.md` / `.codex/rules/` / `.kilo/agent/` wins only where it is
more specific than this file.

go-shared holds the scripts and tools that the owner's Go repositories share: repository-level
checks and helpers that more than one repository runs, kept here so a fix lands once. A
resident is run against a repository from a sibling checkout, such as the library-compatibility
check, and is written in standard-library Python or in Go. A tool only one repository needs stays
in that repository, and nothing here is a Go library imported at build time. Each tool is decided
by a record here, and each consuming repository adopts it in its own records. What exists today is
in [docs/architecture.md](docs/architecture.md); the records are indexed in
[docs/README.md](docs/README.md).

## Dependencies

No dependency may be added without a MADR in this repository that names it.
Lockfiles change in the same commit as the first import, and are cleaned in
the commit that removes the last. The first stack record owns the exact
commands.

## MADR and PLAN before mutating work

**Whenever the user asks for an MADR and a plan, load the
`madr-and-plan-writing` skill first** and follow it for authoring, naming and
review. This applies both to writing a fresh pair and to amending an existing
one.

The name is exact — it is the `name:` field of the skill. A mistyped call
returns `Unknown skill`, and an agent that proceeds without the skill writes
something shaped like a MADR while missing the required headings and the
directory rule below. Verify against the filesystem rather than memory:

```bash
ls -d ~/.claude/skills/*madr* ~/.grok/skills/*madr* ~/.codex/skills/*madr* ~/.agents/skills/*madr* 2>/dev/null
grep '^name:' ~/.claude/skills/*madr*/SKILL.md ~/.grok/skills/*madr*/SKILL.md ~/.codex/skills/*madr*/SKILL.md ~/.agents/skills/*madr*/SKILL.md 2>/dev/null
```

**Read-only investigation is allowed with no pair.** Reading, searching,
`git log` / `git show` / `git diff`, and existing tests or diagnostics that
do not write the tree do not need a MADR.

**Mutating work is not.** Before the first write, name the
`docs/decisions/NNNN-MADR-*` / `docs/decisions/NNNN-PLAN-*` pair being
executed, or stop and write one.

Mutating means: creating, editing, or deleting files; staging or committing
(except the bootstrap exception below); dependency or lockfile changes;
CI / config / hook changes; builds or installers that write the tree,
`$HOME`, or a live service; generating committed artifacts.

Order:

1. Investigate (read-only).
2. Write or amend the MADR (`status: proposed` unless the owner already
   decided). Present it. Do not implement.
3. Write or amend the PLAN. Present it.
4. Mutate **only after** the owner explicitly approves execution
   (`proceed`, `execute the plan`, `do phase N`). Stay inside that PLAN.
5. Anything discovered mid-execution that is out of scope waits: amend the
   pair, re-approve, then continue. Completing a phase is not permission to
   invent the next unwritten one.

Follow-up vs greenfield:

- **Same topic** (debug, leftover phase, bug found in that plan's live
  run): amend that number. Add a PLAN phase or an amendment in the MADR. Do
  not silently rewrite historical rationale.
- **Greenfield**: next unused `NNNN`, new MADR, new PLAN, same slug. No
  mutation until that PLAN is approved.

Bootstrap exception: authoring `docs/decisions/NNNN-MADR-*`,
`docs/decisions/NNNN-PLAN-*`, this file, and the per-agent pointers
(`.claude/rules/`, `.grok/rules/`, `.opencode/rules.md`, `.codex/rules/`,
`.kilo/agent/`) does not require a *prior* pair. Putting source, tests, CI,
or product config in that same commit is a violation.

`git push` and tags still need an explicit ask in the same turn.

When the user asks where a document belongs, load `documentation-writing`.

## Records

```text
docs/decisions/NNNN-MADR-short-slug.md
docs/decisions/NNNN-PLAN-short-slug.md
docs/reports/NNNN-REPORT-short-slug.md
docs/reports/NNNN-GATES-short-slug.md
```

- `NNNN` is a zero-padded 4-digit number, one sequence across
  `docs/decisions/` and `docs/reports/`. A MADR and its PLAN share the same
  number and the same slug.
- **Next number** comes from `python3 scripts/check_records.py --next`.
  Never reuse a number, never renumber an existing record, never leave a gap
  deliberately.
- `make check-records` validates naming, pairing, placement, and every
  relative link in the records and the unnumbered docs. If Make is absent,
  run `python3 scripts/check_records.py --check-all`.
- Cite records by full filename, never by number alone. Cite another
  repository's record by repository and filename; a relative link cannot reach
  it.
- `docs/README.md` indexes every record by hand. Update it in the same change.

## Pre-add checks

- Before staging, run the repository's pre-add command if one exists.
- Before every commit, run `make check-records` and `make markdownlint` when those targets exist; otherwise `python3 scripts/check_records.py --check-all` and `npx --yes markdownlint-cli2@0.23.2`.
- Before every commit that touches `scripts/check_libs.py`, run `python3 scripts/check_libs.py --self-test` (offline; 0002-MADR D8).
- A file that fails is not committed.

## Identifiers

Nothing committed carries a hostname, account name, org-internal path, or a
real-machine absolute path. Use placeholders (`<user>`, `/home/<user>/...`).

- When recording an identifier scan in a record or a commit, describe what was
  scanned for ("the local account name", "the hostname domain"); never quote
  it.
- Pushes to GitHub pass through a global pre-push disclosure guard. Before
  asking the owner to push, run the guard itself over the outgoing commits:

  ```bash
  echo "refs/heads/main $(git rev-parse HEAD) refs/heads/main $(git rev-parse origin/main)" |
    python3 ~/.global-git-hooks/github-disclosure.py pre-push origin "$(git remote get-url origin)"
  ```

- Never bypass it with `--no-verify`.

## Commits

`git commit --no-edit`. Never pass `-m` / `--message` / `-F`. The global
`prepare-commit-msg` hook writes the message from the staged diff.
