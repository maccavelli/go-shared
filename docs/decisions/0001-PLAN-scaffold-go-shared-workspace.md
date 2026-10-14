---
status: complete
date: 2026-10-13
associated-madr: "0001-MADR-scaffold-go-shared-workspace.md"
---

# Implement creating `go-shared` and scaffolding it to the fleet workspace standard

Associated MADR: [0001-MADR-scaffold-go-shared-workspace.md](0001-MADR-scaffold-go-shared-workspace.md)

~~**Not approved for execution.**~~ Approved by the owner on 2026-10-13 ("proceed with 0001,
scaffold, then proceed to 0002 P1").

## Goal

A local `go-shared` repository with the workspace file set staged, and an empty public
`maccavelli/go-shared` on GitHub as its `origin`. The owner commits and pushes.

## Scope

P1 may create only these files:

* `.gitattributes`, `.gitignore`;
* `.markdownlint-cli2.jsonc`, `opencode.json`;
* `.claude/.gitignore`, `.claude/rules/madr-and-plan-skill.md`;
* `.grok/rules/madr-plan-before-mutating-work.md`;
* `.opencode/rules.md`;
* `.codex/rules/madr-plan-before-mutating-work.md`;
* `.kilo/.gitignore`, `.kilo/agent/madr-and-plan-skill.md`;
* `scripts/check_records.py`;
* `AGENTS.md`, `README.md`, `docs/README.md`, `docs/architecture.md`;
* `LICENSE` (Apache-2.0; MADR amendment of 2026-10-13);
* the four existing records (0001 and 0002 pairs), unchanged except for this PLAN's execution
  record.

P2 changes only GitHub and the local `origin` remote. No source, test, CI or tool belongs to either
phase. `scripts/check_libs.py` is 0002's.

## Implementation Steps

### P1 — Scaffold the local repository and stage it

1. In the `go-shared` directory: `git init -b main`. Check that
   `git rev-parse --path-format=absolute --git-path hooks` resolves to the owner's global hooks
   directory, and stop if it does not.
2. Copy the byte-identical files from the `workspace-scaffolding` skill's `templates/` (MADR D2),
   then run `cmp` on each against its template.
3. Write `.gitignore` from the skill's `gitignore-fragment`.
4. Write `AGENTS.md` from the template with MADR D3's three slots, and check that no `{{` token
   remains.
5. Write `docs/README.md` from the template:
   * the record table lists 0001 and 0002, MADR and PLAN, each `proposed`;
   * the "I want to…" rows add "check my repository against the latest library tags", pointing at
     0002's MADR.
6. Write `docs/architecture.md` from the template:
   * "What it is": the scope paragraph;
   * "What is not here": no tool yet (0002 adds the first), no `Makefile`, no CI workflow, no
     licence.
7. Write a root `README.md`: one paragraph of scope, a link to `docs/README.md`, and the "I want
   to…" excerpt.
8. Run the gates (Verification), then stage every P1 file with `git add`. Do not commit.

### P2 — Create the empty GitHub repository

1. Run `gh repo create maccavelli/go-shared --public` (or `--private` if the owner chooses), with no
   README, licence or `.gitignore` option, so the remote stays empty.
2. Run `git remote add origin https://github.com/maccavelli/go-shared.git`.
3. Do not push. The owner runs `git commit --no-edit`, then pushes.

### After P2

0002's P1 stages `scripts/check_libs.py` only after the owner has committed this scaffold, so the
scaffold commit carries no source.

## Verification

Exit status recorded before reading output:

```bash
python3 scripts/check_records.py --next          # expect 0003
python3 scripts/check_records.py --check-all
npx --yes markdownlint-cli2@0.23.2
git ls-files --eol                               # every text file attr/text=auto eol=lf
```

* `cmp` reports each byte-copied file identical to its template.
* Plants, on a scratch copy of the staged tree, never in it. Each is seen failing:
  * `[x](missing.md)` in `README.md`, which must report a broken relative link;
  * a `* item` list in `README.md`, which must report MD004;
  * a 224-character paragraph in `README.md` and in `AGENTS.md`, which must report MD013;
  * the same paragraph in a `NNNN-MADR-*.md`, which must pass, because records are excluded from
    that rule.
* An identifier scan of the staged files, with the strings read from the environment, finds no
  account name, host name or real-machine path.
* After P2, `gh repo view maccavelli/go-shared --json visibility,isEmpty` shows the chosen
  visibility and an empty repository, and `git remote -v` shows `origin`.

## Rollout and Rollback

* Before the owner commits: unstage and delete the local directory. Nothing is published.
* After P2, `gh repo delete maccavelli/go-shared` removes the empty remote. That deletion is the
  owner's to approve.
* After the owner pushes, a correction is a new commit under an amended record.

## Execution record

### P1 and P2, 2026-10-13

Approved by the owner: "proceed with 0001, scaffold, then proceed to 0002 P1". The owner chose
public visibility and an Apache-2.0 licence, and left the scope paragraph to the agent (MADR
amendment of 2026-10-13).

**P1.**

* `git init -b main`. The hooks path resolves to the owner's global hooks directory.
* Eleven files were copied from the skill's templates, and `filecmp` (byte comparison) reports
  every one identical:
  * the five pointers;
  * `.claude/.gitignore` and `.kilo/.gitignore`;
  * `opencode.json` and `.markdownlint-cli2.jsonc`;
  * `scripts/check_records.py` and `.gitattributes`.
* `.gitignore` was written from the fragment. `AGENTS.md` was written with its three slots
  filled, and no `{{` token remains.
* `docs/README.md`, `docs/architecture.md`, `README.md` and `LICENSE` were written. `LICENSE`
  matches `gh api licenses/apache-2.0`'s body: 201 lines, ending "limitations under the License.".

**P2.**

* `gh repo create maccavelli/go-shared --public` created the remote, and
  `git remote add origin https://github.com/maccavelli/go-shared.git` added it.
* `gh repo view` reports `{"isEmpty":true,"visibility":"PUBLIC"}`.
* Nothing was pushed.

**Deviations.**

* **2026-10-13, P1 step 5: `docs/README.md` names `reports/` without a link.** The template links
  `reports/`, but that directory does not exist until the first report is written, so
  `check_records.py --check-all` failed: `broken relative link: docs/README.md:12: reports/`. The
  line now reads like the template's `guides/` line ("None exists yet; the first report creates this
  directory"). No other file changed. This is a template defect in the `workspace-scaffolding`
  skill, reported to the owner.
* **2026-10-13, P1 step 7: `LICENSE`'s trailing newline.** Written through `--jq`, it ended with
  one blank line more than the API body, and the extra newline was removed.

**Verification,** each exit status recorded before reading its output:

```text
python3 scripts/check_records.py --next        exit=0   0003
python3 scripts/check_records.py --check-all   exit=0   (exit=1 before the reports/ deviation)
markdownlint-cli2 (v0.23.2, repository config) exit=0   5 files, 0 issues
```

Plants, each on a scratch copy of the tree and removed afterwards:

| Plant | Result |
| :--- | :--- |
| `[x](missing.md)` in `README.md` | exit 1, "broken relative link", as expected |
| `* item` in `README.md` | exit 1, MD004, as expected |
| 224-character paragraph in `README.md` | exit 1, MD013, as expected |
| the same paragraph in `AGENTS.md` | exit 1, MD013, as expected (`AGENTS.md` is linted) |
| the same paragraph in a `NNNN-MADR-*.md` | exit 0, as expected (records are excluded) |

* **Identifier scan.** It scanned every file for the local account name, the hostname, the home
  directory path and the git e-mail domain, all read from the environment at run time. A planted
  identifier was found, and the tree had no hits.
* **Line endings.** After staging, `git ls-files --eol` reports `i/lf w/lf attr/text=auto eol=lf`
  for all 20 staged files.
* **`.kilo/.gitignore` is on disk, but not tracked.** Its template's line 7 is `.gitignore`, so the
  file ignores itself (`git check-ignore -v` names `.kilo/.gitignore:7`). This matches the fleet:
  `magic-cli-remote` tracks `.kilo/agent/` but not `.kilo/.gitignore`, and `gobble-cli` tracks
  nothing under `.kilo/`. It was not force-added.

Not done, deliberately: no commit and no push. The owner commits with `git commit --no-edit`, and
pushes.
