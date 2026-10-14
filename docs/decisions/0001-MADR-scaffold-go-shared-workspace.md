---
status: accepted
date: 2026-10-13
decision-makers: Project Owner
consulted: none
informed: maintainers of magic-cli-remote and gobble-cli
---

# Create `go-shared` and scaffold it to the fleet workspace standard

## Context and Problem Statement

The owner's Go repositories each carry their own copy of the scripts and tools they share. The
first case is the library-compatibility check: `gobble-cli` has `scripts/check_libs.py`, and
`magic-cli-remote` needs the same check
(`magic-cli-remote` `docs/decisions/0186-MADR-integrate-current-library-releases-and-prepare-gobble.md`,
D7). On 2026-10-13 the owner decided that the check lives in a new shared repository instead of a
second copy (0186, owner answer Q6):

> create a new repo for shared scripts and tools named go-shared and scaffold it as per the
> workspace-scaffolding skill, put the script in the scripts dir as per the scaffolding rules. then
> create it on my github and stage it so i can push it

This record decides how the repository is created and scaffolded. The script itself is
[0002-MADR-shared-library-compatibility-check.md](0002-MADR-shared-library-compatibility-check.md),
because the workspace standard keeps source out of the scaffold's commit.

Facts, read on 2026-10-13:

* No `go-shared` repository exists, locally or on GitHub. The owner's related repositories are
  all public: `magic-cli-remote`, `gobble-cli`, `acp-go-sdk2`, `go-selfupdate-lib`,
  `go-llmprovider-sdk` and `mcplib`.
* The global hooks path is the owner's global hooks directory, so commits use
  `git commit --no-edit`, and the hook writes the message.
* The other Go repositories sit side by side under one parent directory. `go-shared` joins them
  there, so a consumer can find it at `../go-shared`.

## Decision Drivers

* The repository follows the workspace standard from its first commit: records before mutation,
  the five harness pointers, and the docs gates.
* The scaffold commit carries no source. The bootstrap exception covers records, `AGENTS.md` and
  the pointers only.
* The owner commits and pushes. The agent stages, and creates the empty GitHub repository the owner
  asked for.
* Shared tooling has one home, so a fix lands once.

## Considered Options

* **A. A new repository, scaffolded to the workspace standard, with the script in its own later
  change** (chosen).
* **B. A bare repository holding only the script.**
* **C. Ship shared scripts inside the `workspace-scaffolding` skill's templates.**

## Decision Outcome

Chosen option: "**A. A new repository, scaffolded to the workspace standard, with the script in
its own later change**", because it is what the owner asked for, and it gives the shared tools the
same gates as every repository that runs them. B leaves a repository whose changes no record
governs. C puts product tooling into a host-level skill, which the skill's own boundary rules out:
it does not own product tooling.

### The decisions

* **D1 — Location and name.** The repository is `go-shared`, beside the other Go repositories, with
  default branch `main`. On GitHub it is `maccavelli/go-shared`, **public** like its consumers. The
  owner confirms visibility when approving this record.
* **D2 — The workspace file set, unmodified except for the named deltas.**
  * **Copied byte for byte from the skill's templates, and checked with `cmp`:**
    * the five harness pointers (Claude, Grok, OpenCode, Codex, Kilo);
    * `.claude/.gitignore` and `.kilo/.gitignore`;
    * `opencode.json`;
    * `.markdownlint-cli2.jsonc`;
    * `scripts/check_records.py`;
    * `.gitattributes`, whose template carries no provenance comment to change.
  * **Named deltas:**
    * `.gitignore`: written from the skill's fragment, since none exists;
    * `AGENTS.md`: the three slots below;
    * `docs/README.md` and `docs/architecture.md`: from the templates, describing this
      repository;
    * a short root `README.md` that links to `docs/README.md`.
  * **No `Makefile` in the scaffold.** The owner has not asked for one, and none exists. The gates
    run as plain commands.
* **D3 — The `AGENTS.md` slots.**
  * **Scope:** "go-shared holds scripts and tools shared across the owner's Go repositories, so a
    check or helper that several repositories run has one home. Each tool is decided by a record
    here, and each consuming repository decides in its own records to use it.
    `docs/architecture.md` lists what exists today."
  * **Dependencies:** the template's default. No dependency is added without a record that names
    it.
  * **Pre-add:** the template's default. Run `python3 scripts/check_records.py --check-all` and
    `npx --yes markdownlint-cli2@0.23.2` before every commit, and a failing file is not committed.
    0002 adds the script's self-test.
* **D4 — The GitHub repository is created empty.** `gh repo create maccavelli/go-shared` runs with
  no README, licence or `.gitignore`, so the first push is the owner's commit. `origin` is added
  locally. The agent does not commit or push.
* **D5 — No licence file in the scaffold.** The workspace file set has none. A licence for a public
  repository is an owner decision, taken by a later record (see "More Information").

### Consequences

* Good, because shared tooling gets one home with the same record and lint gates as its consumers.
* Good, because the scaffold commit is records and workspace files only, so the bootstrap exception
  holds.
* Neutral, because the repository is created empty on GitHub and stays so until the owner pushes.
* Bad, because a public repository without a licence is "all rights reserved" by default until the
  owner adds one.

### Confirmation

* `cmp` reports every byte-copied file identical to its template.
* `python3 scripts/check_records.py --check-all` and `npx --yes markdownlint-cli2@0.23.2` exit 0.
  Each is first shown failing on a planted input in a scratch copy, never in the tree: a broken
  link, an MD004 list, and a 224-character paragraph in `README.md` and in `AGENTS.md`.
* `git ls-files --eol` reports `attr/text=auto eol=lf` for every staged text file.
* An identifier scan of the added files finds no account name, host name or real-machine path.
* `gh repo view maccavelli/go-shared` shows the empty public repository, and `git remote -v` names
  it as `origin`.

## Pros and Cons of the Options

### A. A new repository, scaffolded to the workspace standard

* Good, because it matches the owner's instruction exactly.
* Good, because every later tool arrives under a record.
* Bad, because one more repository has to be kept in step with the workspace templates.

### B. A bare repository holding only the script

* Good, because it is smaller.
* Bad, because nothing gates its changes, and its consumers' records would point at an unrecorded
  tool.

### C. Shared scripts inside the `workspace-scaffolding` skill

* Good, because every scaffolded repository already receives the skill's files.
* Bad, because the skill owns the workspace, not product tooling, and lives outside any repository.

## More Information

### Questions for the owner

* **Visibility:** public (proposed, like every consumer) or private.
* **Licence:** none for now (proposed), or name one for a later record.

### Amendment — 2026-10-13: the owner's answers

The owner answered on 2026-10-13, and approved the PLAN ("proceed with 0001"). This record is
accepted with these changes. Where they contradict a decision above, this amendment governs.

* **Visibility is public.** D1 stands.
* **The licence is Apache-2.0, in the scaffold.** This replaces D5.
  * `LICENSE` holds the Apache License 2.0 text, as GitHub's licence API serves it
    (`gh api licenses/apache-2.0`).
  * It joins the scaffold's file set. It is neither source, test, CI nor product config, so the
    bootstrap exception still holds.
  * The "Bad" consequence about a public repository without a licence is withdrawn.
* **The scope paragraph** was left to the agent: "make something relevant up". D3's wording
  stands, extended so the paragraph names what kind of tool belongs here and what does not.

### Related records

* [0001-PLAN-scaffold-go-shared-workspace.md](0001-PLAN-scaffold-go-shared-workspace.md): this
  record's plan.
* [0002-MADR-shared-library-compatibility-check.md](0002-MADR-shared-library-compatibility-check.md):
  the first tool.
* `magic-cli-remote` `docs/decisions/0186-MADR-integrate-current-library-releases-and-prepare-gobble.md`
  (D7, owner answer Q6) and `gobble-cli`
  `docs/decisions/0019-MADR-sibling-libraries-current-pins-and-integration.md` (D14), cited by
  repository because a relative link cannot reach another repository.
