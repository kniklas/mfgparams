# Implementation Plan: Process Namespaces and Installation Extras

**Branch**: `014-process-namespaces-extras` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-process-namespaces-extras/spec.md`

## Summary

Reorganise the calculation modules from operation-first (`mfgparams.operations.<operation>`) to
process-first (`mfgparams.processes.machining.<operation>`), move the interactive console into
`mfgparams.console`, and declare `[console]`/`[all]` installation extras so a default install
carries only what the calculations need.

The work is almost entirely a **mechanical move**: no formula, input, output, or reference-data
value changes (FR-003), and the top-level public surface is unchanged (FR-005), so the existing
contract and integration suites are the primary correctness evidence — they must pass with only
import-path edits.

Four things are genuinely new and carry the design risk:

1. An automated guard that the core never imports the console (FR-008), with a deliberate,
   narrowly-scoped exemption for `mfgparams/__main__.py`.
2. A friendly missing-dependency path for the console entry point (FR-011), which must be built
   against a dependency set that is currently empty.
3. Packaging metadata for the relocated bundled data, verified against a **built** artifact
   rather than a source checkout (FR-015).
4. A static check that the old layout cannot be reintroduced (FR-017).

## Technical Context

**Language/Version**: Python 3.9–3.12 (floor 3.9, `requires-python = ">=3.9"`)

**Primary Dependencies**: `tomli` (3.9/3.10 only) for core. No new runtime dependency is added by
this feature; the `console` extra is declared empty (spec Assumptions).

**Storage**: Bundled TOML reference data shipped as package data; user-supplied TOML config files.

**Testing**: pytest + pytest-cov; tox across py39–py312; `-m packaging` env for wheel-contents
assertions

**Target Platform**: OS-independent; library plus interactive console

**Project Type**: Single project, `src/` layout, library + CLI

**Performance Goals**: Unchanged. Principle V's legacy-hardware budgets are enforced by
`tests/performance/` and must not regress. Making the console import lazy should *reduce* core
import cost; no budget is expected to move.

**Constraints**: No behaviour change of any kind (FR-003, FR-012); coverage stays ≥90%; every
Principle IX gate must pass; no release cut by this feature (FR-018).

**Scale/Scope**: ~31 source modules and ~65 test modules move or have imports rewritten; 3 bundled
data directories relocate (`mfgparams/data/`, holding `materials.toml`, stays at the package root);
2 Sphinx pages need path updates and the README gains install and structure content.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Verdict |
|---|---|---|
| I. Code Quality | Pure relocation; no function gains responsibility. Ruff/black/mypy configs need path updates only. | PASS |
| II. Testing | No new calculation logic, so existing tests are the regression evidence. Four genuinely new behaviours (FR-008, FR-011, FR-015, FR-017) each get their own test. Coverage threshold unchanged. | PASS |
| III. Calculation Robustness | FR-003 forbids any numeric change; contract tests move unedited apart from import lines. Reference data moves byte-identical. | PASS |
| IV. Packaging & Versioning | `src/` layout and single-source dynamic version retained. Extras are the standard mechanism. FR-018 defers the version bump to the last slice of #63. | PASS (see Complexity Tracking) |
| V. Resource-Constrained Compatibility | No runtime change. Lazy console import can only reduce core import cost; performance budgets re-run unchanged. | PASS |
| VI. Extensibility by Design | This feature *is* Principle VI applied to the process layer: a future process attaches beside `machining` without editing it (FR-006). | PASS |
| VII. Documentation & Publishing | Sphinx pages reference the old paths and must be updated (FR-016); docs build is a CI gate already. | PASS |
| VIII. Internationalization | Catalogs stay in core this slice. FR-011 introduces one new user-facing string, which must be catalogued, not inlined — with a forward-compatibility trap documented in research.md #4. | PASS (with constraint) |
| IX. Automated Gates | No gate is added, removed, or reconfigured. `ci-ok`'s composition is untouched. | PASS |
| X. Licensing & Author Rights | Unaffected. | PASS |
| XI. Multi-Agent Consistency | No agent-integration file changes. **Corrected during implementation**: this originally read "no skill or agent-integration file changes", which under-scoped FR-017 — that requirement reaches every tracked file, and two files under `.github/skills/` still described the operation-first layout. `/speckit-converge` found them; T045-T047 fixed them and widened the guard that missed them. Skill *documentation* corrections are direct edits, not generated-artifact syncs, so Principle XI's no-hand-syncing rule is untouched. | PASS (see T045-T047) |
| XII. Long-Lived Feature Branches | Not triggered: this slice is independently releasable and targets `main` as a single PR, per the agreed decomposition on issue #63. | N/A |

**Post-Phase 1 re-check**: PASS. The Phase 1 design introduces no new module with mixed
responsibility, no new dependency, and no new gate. The one constraint carried forward is
Principle VIII's, recorded as research.md #4 and encoded in
[contracts/console-entry-contract.md](./contracts/console-entry-contract.md).

## Project Structure

### Documentation (this feature)

```text
specs/014-process-namespaces-extras/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── package-layout-contract.md
│   ├── installation-extras-contract.md
│   └── console-entry-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/mfgparams/
├── __init__.py                     # public surface — unchanged names (FR-005)
├── __main__.py                     # `python -m mfgparams` shim; lazy console import (FR-012)
├── config.py, models.py, registry.py, registry_config.py,
├── units.py, validation.py, logging_setup.py
├── i18n.py                         # stays in core this slice (slice 015 relocates)
├── locales/
│   └── en.py
├── data/
│   └── materials.toml
├── console/                        # was cli.py (FR-007)
│   ├── __init__.py
│   ├── __main__.py                 # console script target
│   └── cli.py
└── processes/                      # was operations/ (FR-001)
    ├── __init__.py
    └── machining/
        ├── __init__.py
        ├── drilling/
        │   ├── __init__.py, formulas.py, tools.py
        │   └── data/
        └── milling/                # sub-operation level retained (FR-002)
            ├── __init__.py, _shared.py, _calculate.py, _tool_registry.py
            ├── end_milling/
            │   ├── __init__.py, formulas.py, tools.py
            │   └── data/
            └── face_milling/
                ├── __init__.py, formulas.py, tools.py
                └── data/

tests/
├── contract/                       # import-path edits only
├── integration/                    # import-path edits only
├── performance/
├── scripts/
├── static/
│   ├── test_no_old_layout.py       # NEW (FR-017)
│   └── test_core_does_not_import_console.py   # NEW (FR-008)
└── unit/
    ├── shared/
    └── processes/machining/        # mirrors src (FR-014)
        ├── drilling/
        └── milling/{end_milling,face_milling}/
```

**Structure Decision**: Single project, `src/` layout, retained unchanged. Two sibling top-level
sub-packages under `mfgparams`: `processes/` (calculation domain, grouped process → operation →
sub-operation per the resolved clarifications) and `console/` (presentation). Cross-cutting modules
(`models`, `units`, `validation`, `registry`, `config`, `i18n`) stay at the package root, since
Principle VI requires them to be shared across processes rather than duplicated per process.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Additional Constraints require every merge to `main` to publish a release to PyPI; this feature merges to `main` without doing so (FR-018) | The publish workflow does not exist yet (issue #40), so the repository is *already* non-compliant with this clause; this feature does not introduce the deviation. Publishing each slice of issue #63 separately would burn a major version per slice for a package with no users. | Cutting a release per slice was rejected: nothing is published yet (verified 2026-08-30), so there is no consumer for whom the intermediate versions have value, and FR-004's no-alias rule means each slice would be an independently breaking release. One 2.0.0 after the last slice is both simpler and more honest. |
| `mfgparams/__main__.py` is core code that references the console, against FR-008's blanket wording | `python -m mfgparams` requires a `__main__.py` at the package root; there is no other location the interpreter will accept. | Moving it into `console/` was rejected: it would silently drop `python -m mfgparams`, breaking FR-012. The exemption is instead narrowed to one named file whose import must be *lazy* (inside the function body), so importing `mfgparams` still never pulls the console — enforced by test, see research.md #1. |
