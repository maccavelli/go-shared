# go-shared

Scripts and tools that the owner's Go repositories share: repository-level checks and helpers that
more than one repository runs, kept in one place so a fix lands once. A consuming repository runs a
tool from a sibling checkout of this repository.

Documentation, decisions and the full index: [docs/README.md](docs/README.md).

## I want to…

| I want to… | Start here |
| :--- | :--- |
| understand how this fits together | [docs/architecture.md](docs/architecture.md) |
| know the rules agents follow in this repository | [AGENTS.md](AGENTS.md) |
| check my repository against the latest library tags | [0002-MADR-shared-library-compatibility-check.md](docs/decisions/0002-MADR-shared-library-compatibility-check.md) |

## Licence

Apache License 2.0. See [LICENSE](LICENSE).
