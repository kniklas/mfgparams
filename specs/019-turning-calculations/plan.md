# Implementation Plan: Turning Calculations Module

**Branch**: `019-turning-calculations` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/019-turning-calculations/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Add a new `turning` machining process as a sibling to the existing `drilling` and `milling`
processes: a single-subtype process package under
`src/mfgparams/processes/machining/turning/` that calculates spindle speed, feed rate,
machining time, cutting force, and power for straight (outside-diameter) lathe turning,
across the same three calculation modes (standard, fixed-RPM, power-constrained) already
implemented for drilling and milling. Reuses the existing `WorkpieceMaterial` registry,
the bundled-`tools.toml` configurable-tool pattern, the shared `CalculationResult`/`ErrorInfo`
result types, the message-catalog i18n mechanism, and unit conversion layer without
modifying any of them structurally; extends `MachiningOperation` and the console dispatch
with one new `TURNING` member, mirroring exactly how drilling and milling are wired in today.

## Technical Context

**Language/Version**: Python (>=3.9, per `pyproject.toml` `requires-python` and the
tox multi-version matrix from `specs/013-tox-multi-python-testing/`)

**Primary Dependencies**: None new. Reuses `mfgparams.registry` (materials),
`mfgparams.config` (external bounds override), `mfgparams.i18n` (message catalog),
`mfgparams.units`, `mfgparams.models`, `mfgparams.validation`, and the console's
`prompt-toolkit`-based TUI (`mfgparams.console.tui`) already used by drilling/milling.

**Storage**: N/A (in-memory calculation; bundled `tools.toml` per operation, same as
drilling/milling; optional external configuration file for validation-bound overrides,
same mechanism as the existing processes).

**Testing**: `pytest`, following this repo's existing three-tier layout
(`tests/unit/`, `tests/contract/`, `tests/integration/`) and the drilling/milling test
naming conventions (e.g. `test_library_api_turning*.py`, `test_validation_turning.py`).

**Target Platform**: Cross-platform CLI/TUI (Linux/macOS/Windows), including
resource-constrained legacy hardware per Constitution Principle V — identical target to
the existing drilling/milling processes; this feature does not change that target.

**Project Type**: Single Python package (library + console front-end), `src/` layout —
matches the existing project structure exactly; no new project/subsystem is introduced.

**Performance Goals**: Each turning calculation completes in well under the
Principle V target of 0.5-1.0s on the legacy/low-power hardware profile — it is closed-form
arithmetic (no iteration beyond the existing power-constrained solve already used by
drilling/milling), so no new performance risk is introduced.

**Constraints**: Must run within the existing ~64-128 MB RAM / single-threaded-CPU
envelope (Constitution Principle V); no new runtime dependency may be introduced that
would put this at risk. No new dependency is planned.

**Scale/Scope**: One new process package (`turning`), one new bundled tool config
(`turning/data/tools.toml`), one new `MachiningOperation` enum member, one new console
menu entry, and the corresponding test suites — comparable in size to the original
`001-metal-drilling-calc` + `002-constrained-calculation-modes` features combined (this
feature intentionally ships turning with all three calculation modes from the start,
rather than splitting standard-mode and calculation-modes into separate features the way
drilling originally did).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Code Quality)**: Turning's `formulas.py`/`tools.py`/`__init__.py` will
  follow the exact single-responsibility split already used by `drilling/` (formulas vs.
  tool registry vs. orchestration); no god-functions. PASS.
- **Principle II (Testing Standards)**: New unit/contract/integration tests will be added
  for every new calculation function and mode, including nominal/boundary/zero/negative
  cases and reference-value checks, per SC-002. PASS (planned, not yet written — Phase 2
  `/speckit-tasks` will enumerate test tasks before implementation tasks).
- **Principle III (Calculation Robustness & Accuracy)**: Formulas will cite their
  published source (e.g. Sandvik Coromant / Machinery's Handbook turning formulas) in code
  comments, exactly as `drilling/formulas.py` does; floating-point comparisons in tests use
  `math.isclose`; all inputs validated before use (FR-010, FR-011, FR-013). PASS.
- **Principle IV (Python Packaging & Versioning)**: No packaging changes; turning ships as
  part of the existing `mfgparams` package/version. This is a MINOR (additive, non-breaking)
  change to the public API surface. PASS.
- **Principle V (Resource-Constrained Compatibility)**: No new dependency; closed-form
  arithmetic identical in cost profile to drilling/milling. PASS.
- **Principle VI (Extensibility by Design)**: This is the principle turning was explicitly
  named under ("The module's architecture MUST anticipate growth beyond drilling into
  other metal machining operations (e.g., turning, milling...)"). Turning will be added as
  its own `mfgparams.processes.machining.turning` package implementing the same
  `calculate()`-style interface, without modifying `drilling/` or `milling/`. PASS.
- **Principle VII (Documentation & Publishing)**: New Sphinx doc pages
  (`docs/source/turning.rst`, `docs/source/turning-api.rst`) will be added mirroring
  `milling.rst`/`milling-api.rst`; existing coverage/build-status badges are unaffected
  mechanically. PASS (tracked as a task, not yet written).
- **Principle VIII (Internationalization)**: All new user-facing strings (turning menu
  label, prompts, errors) go into the existing message-catalog mechanism with English
  entries only for this feature, exactly as FR-015 and the Assumptions section state. PASS.
- **Principle IX (Automated Quality/Complexity/Security Gates)**: No change to CI gate
  configuration; new code is subject to the same existing complexity/lint/type/security
  gates automatically since it lives under `src/`. PASS.
- **Principle X (Licensing & Author Rights)**: No change. N/A.
- **Principle XI (Multi-Agent Coding-Tool Consistency)**: No skill files
  (`.github/skills/**`) are touched by this feature. N/A.
- **Principle XII (Long-Lived Feature Branches for Multi-PR Work)**: **Superseded by
  actual delivery** (updated post-implementation, per a Copilot review finding on PR #100:
  this section originally planned a two-PR split — a spec-only PR followed by a separate
  implementation PR, mirroring the `018-tui-splitpane-redesign` precedent — but that plan
  was reconsidered mid-flow once the spec PR turned out to still be open/unmerged when
  implementation started; see PR #100's own description). The feature was in fact
  delivered as a **single** pull request (`#100`) on the `019-turning-calculations` branch,
  containing the complete spec, plan, tasks, and a complete, working implementation
  together. A single complete PR trivially does not merge a "partially-built slice" of code
  to `main`, so the long-lived-integration-branch/dual-ruleset machinery this principle
  requires for a genuine multi-PR split was never triggered and remains inapplicable.
  PASS.

## Project Structure

### Documentation (this feature)

```text
specs/019-turning-calculations/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── library-api-turning.md
│   └── cli-repl-turning.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

Single project, `src/` layout (existing structure — no new option introduced):

```text
src/mfgparams/
├── models.py                          # + TURNING member on MachiningOperation (no new class)
├── console/
│   └── tui/
│       └── machining_menu.py          # + turning menu entry, dispatching like drilling/milling
├── processes/
│   └── machining/
│       ├── drilling/                  # existing, unchanged — closest structural analog
│       └── turning/                   # NEW — single-subtype process, mirrors drilling/
│           ├── __init__.py            # calculate() orchestration (validation, mode dispatch)
│           ├── formulas.py            # spindle speed / feed / time / cutting force / power
│           ├── tools.py               # TurningTool dataclass + get_tool()
│           └── data/
│               └── tools.toml         # bundled HSS/Cobalt/Carbide reference factors
docs/source/
├── turning.rst                        # NEW — end-user docs, mirrors milling.rst
└── turning-api.rst                    # NEW — API reference, mirrors milling-api.rst

tests/
├── unit/
│   └── test_validation_turning.py     # NEW
├── contract/
│   ├── test_library_api_turning.py                    # NEW
│   ├── test_library_api_turning_fixed_rpm.py          # NEW
│   ├── test_library_api_turning_fixed_rpm_errors.py   # NEW
│   ├── test_library_api_turning_power_constrained.py  # NEW
│   └── test_library_api_turning_power_constrained_errors.py  # NEW
└── integration/
    ├── test_tui_turning.py            # NEW
    └── test_turning_fixed_rpm_feasibility.py  # NEW
```

**Structure Decision**: Reuses the existing single-package `src/` layout unmodified.
Turning is added as a new sibling package
`src/mfgparams/processes/machining/turning/`, structurally identical to
`src/mfgparams/processes/machining/drilling/` (a single-subtype process — no
intermediate sub-operation grouping the way `milling/` has for
`end_milling`/`face_milling`, per the spec's Assumptions section). No existing file
in `drilling/` or `milling/` is modified; the only edits to already-existing files
are additive (a new `MachiningOperation` member in `models.py`, a new dispatch branch
in `console/tui/machining_menu.py`, and a new top-level re-export in
`mfgparams/__init__.py`), consistent with Constitution Principle VI.

## Post-Design Constitution Re-check

Re-evaluated after Phase 1 (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`):
no new violation surfaced. The one design change Phase 0 research forced — adding
`depth_of_cut` as a required input and `cutting_force` as a new optional
`CalculationResult` field — is itself an application of Principle III (validated,
physically meaningful inputs) and Principle VI (extend the shared result type rather than
special-case it), not a deviation from either. All PASS verdicts from the pre-design
Constitution Check above stand unchanged.

## Complexity Tracking

*No entries — the Constitution Check above found no violations requiring justification.*
