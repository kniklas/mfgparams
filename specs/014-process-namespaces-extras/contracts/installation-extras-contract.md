# Contract: Installation Extras

**Feature**: [../spec.md](../spec.md) | **Requirements**: FR-009, FR-010, FR-013, FR-015, FR-018

## Declared extras

| Command | Installs | Guarantee |
|---|---|---|
| `pip install mfgparams` | Core runtime only (`tomli` on Python < 3.11) | Full calculation API; zero console-only dependencies (FR-009, FR-013) |
| `pip install mfgparams[console]` | Core + console dependencies | Interactive console starts and behaves identically to before this feature (FR-010) |
| `pip install mfgparams[all]` | Every runtime extra the project ships | Superset of all of the above (FR-010) |

`test` and `dev` are pre-existing development extras and are outside this contract; `all` covers
*runtime* extras only, and MUST NOT pull development tooling into a user install.

`all` is expressed as a **self-referential extra** (`all = ["mfgparams[console]"]`) so that it
cannot drift out of step with the extras it aggregates. pip resolves that form only from **21.2**
onward. The project already instructs users to upgrade pip before installing, because Python 3.9
ships a pip predating PEP 660 editable installs (README, *Install (development)*) - so no new
instruction is needed there, but that step is now load-bearing for a second, independent reason
and MUST NOT be dropped as obsolete when the 3.9 floor eventually rises. The reason it is stated
in the user-facing *Install* section as well: that section is where a non-developer meets
`mfgparams[all]`, and the development note is below it, past the point of failure. (Cited by
section rather than by line: this contract outlived its own line reference once already.)

**The `console` extra is empty on delivery.** The console currently needs nothing beyond the
standard library. It is declared anyway: adding an extra later is a packaging change users must
react to, whereas populating a declared one is invisible to them.

## What an extra does and does not gate

An extra gates **dependencies only**. Every module — `mfgparams.console` included — ships in the
single distribution regardless of which extras were requested.

This has one consequence that governs the whole design, and getting it wrong produces a guard that
can never fire: **module importability is not evidence that an extra was installed.** Any check of
the form "can I import `mfgparams.console`?" answers "yes, always" and is therefore worthless. The
FR-011 guard MUST key on importing the console's **dependencies**. See
[console-entry-contract.md](./console-entry-contract.md).

## Bundled data (FR-015)

The built distribution MUST contain:

```
mfgparams/data/materials.toml
mfgparams/processes/machining/drilling/data/tools.toml
mfgparams/processes/machining/milling/end_milling/data/tools.toml
mfgparams/processes/machining/milling/face_milling/data/tools.toml
```

and MUST contain no `.toml` under any `mfgparams/operations/` path. Both directions are asserted
against a **built artifact**, not a source checkout — a source-tree check passes even when packaging
metadata is wrong, which is the failure this assertion exists to catch. These assertions carry the
`packaging` marker and run in CI's `build` job and `tox -e packaging`.

## Release handling (FR-018)

This feature publishes nothing and bumps no version. Changes accumulate under `## [Unreleased]` in
`CHANGELOG.md`, to be released as a single major version once the last slice of issue #63 lands and
before issue #40 publishes. The clean break of FR-004 is only defensible while nothing is published.
