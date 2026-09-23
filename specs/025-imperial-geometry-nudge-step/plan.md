# Implementation Plan: Imperial Arrow-Key Nudge Step for Geometry Fields

**Branch**: `025-imperial-geometry-nudge-step` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/025-imperial-geometry-nudge-step/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Give nine existing geometry `NumberRow`s — milling's cutter diameter,
axial depth of cut, radial engagement, and length of cut
(`screens/milling.py`); drilling's drill diameter and hole depth
(`screens/drilling.py`); turning's workpiece diameter, depth of cut, and
length of cut (`screens/turning.py`) — a `step` of 0.1 in under IMPERIAL,
computed fresh at render time from `state.unit_system` exactly like
milling's `feed_per_tooth` (`024-feed-per-tooth-nudge-step`) and turning's
`target_feed_rate` (`020-turning-feed-per-rotation`) already do. METRIC
keeps each field's existing default step (`split_pane.NUDGE_STEP` = 1.0).
Unlike those two precedents, no shop-practice research is needed for the
imperial value: the feature request specifies 0.1 literally for all nine
fields, and the fields are already whole geometry dimensions (not a
per-tooth/per-rotation rate), so no metric→imperial conversion-fidelity
question arises either. Milling's `_number_row()` already accepts an
optional `step` (added by 024); drilling's and turning's do not yet — this
plan extends both, mirroring milling's shape, so their call sites can pass
`step=` the same way.

## Technical Context

**Language/Version**: Python (>=3.9, unchanged — no new version requirement).

**Primary Dependencies**: None new. Reuses `split_pane.NumberRow`'s
existing `step` field (`020-turning-feed-per-rotation`) and its
`Decimal`-safe `nudge_selected()` arithmetic (already exercised by 020 and
024 for sub-1.0 steps), the console's existing `prompt-toolkit`-based
split-pane TUI, and each screen's existing `_convert_on_unit_change()`.

**Storage**: N/A (stateless per-render UI constant, unchanged).

**Testing**: `pytest`, extending each screen's existing TUI integration
test suite (`tests/integration/test_tui_milling.py`,
`test_tui_drilling.py`, `test_tui_turning.py`) with nudge-step assertions
for the nine fields under both unit systems, mirroring the existing
`feed_per_tooth`/`target_feed_rate` step tests.

**Target Platform**: Cross-platform CLI/TUI (unchanged), including
resource-constrained legacy hardware per Constitution Principle V.

**Project Type**: Single Python package (library + console front-end),
`src/` layout — no new project/subsystem; touches three existing screen
modules.

**Performance Goals**: N/A — a constant-value change with no new
computation; negligible overhead, same as the 020/024 precedents.

**Constraints**: Same resource envelope as the rest of the console TUI
(Constitution Principle V); this is an interactive-TUI behavior change, so
Constitution Principle XIII (manual verification) applies — see
Constitution Check below.

**Scale/Scope**: Nine fields across three screens
(`screens/milling.py`, `screens/drilling.py`, `screens/turning.py`). No
new `FieldId`, `CalculationMode`, entity, or message-catalog key. Two of
the three screens' `_number_row()` helpers gain a `step` parameter
(drilling, turning); milling's already has one.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Code Quality)**: Each field's step is a `step=` keyword
  argument sourced from one shared `split_pane.geometry_nudge_step()`
  function (extracted during review after a local `/code-review` pass
  caught the same two-branch expression duplicated verbatim across all
  nine call sites — see research.md #2's correction and the contract
  delta), not a per-call-site literal. Drilling's and turning's
  `_number_row()` gain an optional `step` parameter, defaulted to
  `split_pane.NUDGE_STEP` so every other call site (available power,
  target RPM, number of teeth, etc.) is unaffected, matching how milling's
  024 change was scoped. PASS.
- **Principle II (Testing Standards)**: New unit/integration tests
  asserting each of the nine rows carries the correct `step` under both
  unit systems (mirroring `test_feed_rate_row_nudges_by_a_finer_step_*`/
  `test_feed_per_tooth_row_nudges_by_a_finer_step_*`), plus a test that an
  unrelated row (e.g. available power, number of teeth) keeps the default
  step — guarding FR-008's negative scope; ≥90% coverage maintained. PASS
  (planned — `/speckit-tasks` enumerates test tasks before implementation
  tasks).
- **Principle III (Calculation Robustness & Accuracy)**: No calculation
  formula is touched — each field's value, validation, and use in
  `calculate_*()` are unchanged; only the UI nudge increment changes. The
  existing `Decimal`-safe nudge arithmetic in `nudge_selected()` (already
  proven for 0.1-scale steps by 020/024) covers 0.1 in with no further
  change needed. PASS.
- **Principle IV (Python Packaging & Versioning)**: No public API surface
  changes — `NumberRow.step` is an existing, already-optional field; this
  feature only supplies non-default values at nine call sites and extends
  two internal helper signatures. No version bump beyond the standard
  PATCH-level UI-only change. PASS.
- **Principle V (Resource-Constrained Compatibility)**: No new dependency;
  O(1) constant per row, identical cost profile to every other row. PASS.
- **Principle VI (Extensibility by Design)**: Uses the already-shared,
  already-generic `step` mechanism exactly as designed — no
  operation-specific branching added to `split_pane.py`. PASS.
- **Principle VII (Documentation & Publishing)**: `docs/source/milling.rst`,
  `docs/source/drilling.rst`, and `docs/source/turning.rst` each describe
  the default nudge step in prose ("1 display unit for most fields" /
  "small step" / "1 display-unit step every other numeric field uses") and
  MUST be updated so they no longer imply all non-feed fields nudge by 1
  display unit under imperial; tracked as a task. PASS (planned).
- **Principle VIII (Internationalization)**: No new user-facing text — no
  message-catalog key is added or changed; only numeric constants change.
  N/A.
- **Principle IX (Automated Quality/Complexity/Security Gates)**: No CI
  gate configuration change; each changed function stays well within
  existing complexity thresholds (a two-branch step computation per field,
  same shape as the existing turning/milling equivalents). PASS.
- **Principle X (Licensing & Author Rights)**: No change. N/A.
- **Principle XI (Multi-Agent Coding-Tool Consistency)**: No skill files
  (`.github/skills/**`) are touched by this feature. N/A.
- **Principle XII (Long-Lived Feature Branches for Multi-PR Work)**: This
  feature's scope (nine rows' `step` values across three files, no new
  entity/mode) is comparable to or smaller than 024, which shipped as a
  single PR. Planned as a single PR. PASS.
- **Principle XIII (Manual Verification for Interactive & Reference-Fidelity
  Features, NON-NEGOTIABLE)**: This is an interactive-TUI behavior change
  (how nine fields across three screens respond to Left/Right arrow
  presses, and how that response changes the instant the unit-system
  toggle is flipped) — the constitution's manual-verification requirement
  applies regardless of automated step-value test coverage. `tasks.md`
  MUST carry a distinct manual-verification task — a real-terminal walk of
  `quickstart.md`'s scenarios across all three screens, pressing arrow
  keys under both unit systems and confirming the on-screen value moves by
  1 (metric) or 0.1 (imperial), including immediately after toggling unit
  system — performed by the developer or a reviewer, not the implementing
  agent alone, per the principle's interactive-TUI case. PASS (planned —
  tracked as a task, to be confirmed complete by the user before this
  feature is considered done, per the standing
  confirm-manual-verification-scope practice from `022-tui-min-size-25x80`).

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/025-imperial-geometry-nudge-step/
├── plan.md               # This file (/speckit.plan command output)
├── research.md           # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md         # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   └── cli-repl-imperial-geometry-nudge-step-delta.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mfgparams/console/tui/screens/milling.py     # 4 geometry rows gain step=; _number_row() already supports it
src/mfgparams/console/tui/screens/drilling.py    # _number_row() gains step=; 2 geometry rows use it
src/mfgparams/console/tui/screens/turning.py     # _number_row() gains step=; 3 geometry rows use it
tests/integration/test_tui_milling.py            # new nudge-step assertions for the 4 milling geometry fields
tests/integration/test_tui_drilling.py           # new nudge-step assertions for the 2 drilling geometry fields
tests/integration/test_tui_turning.py            # new nudge-step assertions for the 3 turning geometry fields
docs/source/milling.rst                          # updated nudge-step prose
docs/source/drilling.rst                         # updated nudge-step prose
docs/source/turning.rst                          # updated nudge-step prose
```

**Structure Decision**: Single Python package (`src/mfgparams/`), `src/`
layout, unchanged. This feature touches three existing screen modules and
their tests/docs — no new module, package, or directory beyond this
feature's own `specs/025-imperial-geometry-nudge-step/` documentation.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations. Table omitted.
