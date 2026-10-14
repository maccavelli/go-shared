# Documentation

This tree holds three kinds of document:

- reports that measured something;
- the decisions behind the work;
- guides you follow to do a thing.

- **[architecture.md](architecture.md)** — how the pieces fit together, as they are now.
- **guides/** — task-shaped walkthroughs. None exists yet; the first real guide creates this directory.
- **[decisions/](decisions/)** — numbered MADR/PLAN pairs.
- **reports/** — what was observed, deciding nothing. None exists yet; the first report creates this directory.

## Records

| Number | Kind | Record | Status |
| :--- | :--- | :--- | :--- |
| 0001 | MADR | [Create `go-shared` and scaffold it to the fleet workspace standard](decisions/0001-MADR-scaffold-go-shared-workspace.md) | accepted |
| 0001 | PLAN | [Implement creating `go-shared` and scaffolding it to the fleet workspace standard](decisions/0001-PLAN-scaffold-go-shared-workspace.md) | complete |
| 0002 | MADR | [Ship one library-compatibility check, `scripts/check_libs.py`, that any Go repository runs against its own libraries](decisions/0002-MADR-shared-library-compatibility-check.md) | accepted |
| 0002 | PLAN | [Implement the shared library-compatibility check](decisions/0002-PLAN-shared-library-compatibility-check.md) | complete |

## I want to…

| I want to… | Start here |
| :--- | :--- |
| understand how this fits together | [architecture.md](architecture.md) |
| know the rules agents follow in this repository | [AGENTS.md](../AGENTS.md) |
| know why the repository has the files and gates it has | [0001-MADR-scaffold-go-shared-workspace.md](decisions/0001-MADR-scaffold-go-shared-workspace.md) |
| check my repository against the latest library tags | [0002-MADR-shared-library-compatibility-check.md](decisions/0002-MADR-shared-library-compatibility-check.md) |
