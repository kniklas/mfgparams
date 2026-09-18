# Implementation Plan: Turning Feed Rate Per Rotation & Constrained Mode

**Branch**: `020-turning-feed-per-rotation` | **Date**: 2026-09-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-turning-feed-per-rotation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Extend the existing turning entry point (`calculate_turning()`,
`019-turning-calculations`) so every calculation mode also reports a new,
additive `feed_per_rotation` result value (mm/rev METRIC, in/rev IMPERIAL) —
the value turning's own formula layer already computes internally
(`feed_per_rev_mm`) but currently discards — without changing the existing
`feed_rate` field's meaning or value for turning, drilling, or milling (per
the resolved Clarification). Add a fourth, turning-only `CalculationMode`
member, `FEED_RATE_CONSTRAINED`, letting a caller supply that feed-per-
rotation value directly (spindle speed still derived exactly as standard
mode) instead of it being derived from the material/tool's reference feed
value; this reuses the existing at-RPM formula helper with one new optional
parameter rather than duplicating the feed→time→force→torque→power chain a
fourth time (research.md #2). Finally, give the console's `NumberRow` a
per-row arrow-key nudge step (default unchanged at 1.0 display unit) so the
new feed-per-rotation field can nudge by 0.1 mm/rev (0.005 in/rev under
imperial) instead of the coarser step every other numeric field keeps.

## Technical Context

**Language/Version**: Python (>=3.9, unchanged from `019-turning-calculations`
— no new version requirement introduced)

**Primary Dependencies**: None new. Reuses `mfgparams.models` (`CalculationMode`,
`CalculationResult`), `mfgparams.validation` (`validate_target_rpm`,
`validate_mode_arguments`, the new sibling `validate_target_feed_rate`),
`mfgparams.units` (`to_metric_length`, `mm_to_in` — already imported by
`turning/__init__.py`), `mfgparams.i18n`/`mfgparams.console.i18n` (message
catalogs), and the console's existing `prompt-toolkit`-based split-pane TUI
(`mfgparams.console.tui`).

**Storage**: N/A (stateless per-request calculations, unchanged).

**Testing**: `pytest`, extending turning's existing three-tier layout
(`tests/unit/`, `tests/contract/`, `tests/integration/`); tolerance-based
float comparisons (`math.isclose`) per Constitution Principle III for the
new `feed_per_rotation`/spindle-speed-derivation checks.

**Target Platform**: Cross-platform CLI/TUI (unchanged from
`019-turning-calculations`), including resource-constrained legacy hardware
per Constitution Principle V.

**Project Type**: Single Python package (library + console front-end),
`src/` layout — no new project/subsystem; extends the existing
`mfgparams.processes.machining.turning` package and the shared console TUI
infrastructure.

**Performance Goals**: Each turning calculation, including feed-rate-
constrained mode, completes within the same 0.5-1.0s Constitution Principle V
target as the existing three modes — the new mode's spindle-speed derivation
is the same closed-form cutting-speed formula standard mode already uses
(research.md #2), not iterative, so it adds negligible overhead.

**Constraints**: Same ~64-128MB RAM / single-threaded-CPU / Debian-stable
envelope as `019-turning-calculations` (Constitution Principle V); no
exceptions raised for expected validation failures, including the new
`INVALID_TARGET_FEED_RATE` and reused `MODE_CONFLICT` failure modes
(spec.md FR-006/FR-007); the existing `feed_rate` field's meaning, value, and
unit are unchanged for every operation (spec.md FR-002, resolved
Clarification); application logging remains English-only regardless of
locale (Constitution VIII).

**Scale/Scope**: Extends one existing process (`turning`) only — no new
process, no new registry, no new top-level library entry point. Touches:
one shared enum member (`CalculationMode`), one shared result field
(`CalculationResult.feed_per_rotation`), one shared validator extension
(`validate_mode_arguments`), one new shared validator
(`validate_target_feed_rate`), turning's own formula/orchestration/TUI
files, and one small, backward-compatible extension to the shared
`split_pane.py`/`app.py` TUI infrastructure (a per-row nudge step, a new
`FieldId` member, two new defaulted parameters on `power_and_rpm_rows()`).
Neither drilling's nor milling's own calculation behavior changes
(FR-014); each does gain one small, operation-local guard in its own
`_validate_mode_inputs()` rejecting a directly-supplied
`CalculationMode.FEED_RATE_CONSTRAINED` as `UNSUPPORTED_MODE` — a Copilot
review finding during implementation established this call shape is
reachable through their own public signatures, not merely a hypothetical
one an initial draft of this plan assumed away.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Code Quality)**: The new mode's arithmetic is added by
  giving the existing `calculate_turning_metrics_at_rpm()` one new optional
  parameter and adding one new thin wrapper function
  (`calculate_turning_feed_rate_constrained_metrics`), not a duplicated
  formula chain (research.md #2); `validate_target_feed_rate()` mirrors
  `validate_target_rpm()`'s single-responsibility shape exactly. PASS.
- **Principle II (Testing Standards)**: New unit tests for
  `calculate_turning_feed_rate_constrained_metrics()` (nominal/boundary/
  zero/negative/non-finite target feed rate) and the extended
  `_reject_if_invalid()` guard; new contract tests for the new mode's
  success/error responses and for `feed_per_rotation` on every existing
  mode; ≥90% coverage maintained. PASS (planned — `/speckit-tasks` enumerates
  test tasks before implementation tasks).
- **Principle III (Calculation Robustness & Accuracy)**: No new formula is
  introduced — feed-rate-constrained mode reuses turning's already-cited
  formulas (`019-turning-calculations` research.md #1) with the feed-per-
  revolution term taken as a direct input instead of a derived one;
  tolerance-based comparisons (`math.isclose`) for
  `feed_per_rotation * spindle_speed_rpm == feed_rate`-style test
  assertions; `feed_per_rev_mm` added to `_reject_if_invalid()`'s existing
  finiteness/positivity guard (research.md #6) so this feature does not
  reintroduce the underflow/overflow bug class PR #100 already fixed for
  every other field. PASS.
- **Principle IV (Python Packaging & Versioning)**: `calculate_turning()`
  gains one new, optional, defaulted parameter (`target_feed_rate`) and
  `CalculationResult` gains one new, optional, defaulted field
  (`feed_per_rotation`) — both additive/backward-compatible → MINOR version
  bump, not MAJOR. PASS.
- **Principle V (Resource-Constrained Compatibility)**: No new dependency;
  the new mode's calculation is O(1) closed-form, identical cost profile to
  the existing three modes. PASS.
- **Principle VI (Extensibility by Design)**: The new mode is added by
  extending already-shared, operation-agnostic infrastructure
  (`CalculationMode`, `validate_mode_arguments`, `CalculationResult`) — the
  same pattern `010-milling-calculation-modes` used to extend mode support
  to milling without touching drilling's files; here the new mode's
  *calculation* is turning-only, so drilling's and milling's own dispatch
  gains no `FEED_RATE_CONSTRAINED` branch and their existing calculation
  behavior is unaffected (FR-014, research.md #3). Each does gain one
  small, operation-local guard in its own `_validate_mode_inputs()`
  rejecting the mode with `UNSUPPORTED_MODE` if a caller supplies it
  directly — necessary because the enum member itself is shared and still
  reachable through their own public signatures (research.md #3, Copilot
  review finding). The TUI's per-row nudge step and the
  `power_and_rpm_rows()` extension are both additive/defaulted, so
  drilling's and milling's screens require zero code changes. PASS.
- **Principle VII (Documentation & Publishing)**: Sphinx docs
  (`docs/source/turning.rst`, `docs/source/turning-api.rst`) updated to
  document `feed_per_rotation`, the new mode, and `target_feed_rate`,
  mirroring how `019-turning-calculations` documented `cutting_force`.
  PASS (planned, tracked as a task).
- **Principle VIII (Internationalization)**: All new user-facing text (the
  new mode option, the new field label, the new result line, the new error
  message) is sourced from the existing message-catalog mechanism with
  English entries only for this feature (data-model.md "Message Catalog —
  new keys"), reusing existing catalog infrastructure — no new locale
  mechanism. PASS.
- **Principle IX (Automated Quality/Complexity/Security Gates)**: No CI gate
  configuration change; new/changed functions stay within existing
  complexity/MI thresholds (each new function has a single, narrow
  responsibility, mirroring the existing at-RPM/power-constrained
  functions' size). PASS.
- **Principle X (Licensing & Author Rights)**: No change. N/A.
- **Principle XI (Multi-Agent Coding-Tool Consistency)**: No skill files
  (`.github/skills/**`) are touched by this feature. N/A.
- **Principle XII (Long-Lived Feature Branches for Multi-PR Work)**: This
  feature's scope (one process's formula/validation/TUI extension, no new
  process, no new registry) is comparable in size to
  `010-milling-calculation-modes`, which shipped as a single pull request
  without needing a long-lived integration branch. Planned as a single PR
  unless implementation reveals otherwise; re-evaluated at `/speckit-tasks`
  if the task count suggests a multi-PR split is warranted. PASS (tentative).

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/020-turning-feed-per-rotation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md         # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   ├── library-api-turning-feed-per-rotation-delta.md
│   └── cli-repl-turning-feed-per-rotation-delta.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

Single project, `src/` layout (existing structure — no new option introduced):

```text
src/mfgparams/
├── models.py                          # MODIFY: + CalculationMode.FEED_RATE_CONSTRAINED; + CalculationResult.feed_per_rotation (appended last)
├── validation.py                      # MODIFY: + validate_target_feed_rate() (new); extend validate_mode_arguments() with a FEED_RATE_CONSTRAINED branch
├── locales/
│   └── en.py                          # MODIFY: + error.invalid_target_feed_rate
├── console/
│   ├── locales/
│   │   └── en.py                      # MODIFY: + tui.mode.feed_rate_constrained, tui.label.target_feed_rate, tui.result.feed_per_rotation
│   └── tui/
│       ├── app.py                     # MODIFY: + FieldId.TARGET_FEED_RATE
│       └── screens/
│           ├── split_pane.py          # MODIFY: NumberRow.step (new field, defaults to existing NUDGE_STEP); nudge_selected() reads row.step; power_and_rpm_rows() gains feed_rate_constrained/feed_rate_row (both defaulted)
│           ├── forms.py               # MODIFY: + UNIT_LABELS[*]["feed_per_rotation"] (mm/rev, in/rev); + _SPINDLE_SPEED_MODE_LABEL_KEYS[FEED_RATE_CONSTRAINED] (research.md #9 — required, prevents KeyError); format_result() gains the new feed_per_rotation line (research.md #10)
│           └── turning.py             # MODIFY: + _MODE_OPTION_KEYS entry; TurningSessionState.target_feed_rate; _convert_on_unit_change; _set_mode clearing; _feed_rate_row(); calculate_result() passes target_feed_rate through
└── processes/
    └── machining/
        └── turning/                   # existing package, extended (no new file)
            ├── __init__.py            # MODIFY: calculate_turning() gains target_feed_rate param; _compute_metrics() gains a FEED_RATE_CONSTRAINED branch; _validate_mode_inputs() gains target_feed_rate validation + metric conversion; _build_result()/_error_result() gain feed_per_rotation; _reject_if_invalid() guards feed_per_rev_mm
            └── formulas.py            # MODIFY: TurningMetrics.feed_per_rev_mm (new field); calculate_turning_metrics_at_rpm() gains optional feed_per_rev_mm param; + calculate_turning_feed_rate_constrained_metrics() (new)

# Calculation behavior NOT modified (reused verbatim, research.md #3):
#   src/mfgparams/processes/machining/drilling/**     # no FEED_RATE_CONSTRAINED calculation branch added
#   src/mfgparams/processes/machining/milling/**      # no FEED_RATE_CONSTRAINED calculation branch added
#   src/mfgparams/console/tui/screens/drilling.py     # power_and_rpm_rows() call site unchanged (new params defaulted)
#   src/mfgparams/console/tui/screens/milling.py      # power_and_rpm_rows() call site unchanged (new params defaulted)
#
# Each of drilling/__init__.py and milling/_calculate.py DOES gain one
# small addition: an operation-local _validate_mode_inputs() guard
# rejecting a directly-supplied FEED_RATE_CONSTRAINED as UNSUPPORTED_MODE
# (added after a Copilot review round found the enum member reachable
# through their own public signatures regardless of the console's
# restricted mode list; research.md #3).

docs/source/
├── turning.rst                        # MODIFY: document feed_per_rotation and the new mode
└── turning-api.rst                    # MODIFY: document target_feed_rate parameter

tests/
├── unit/
│   └── test_validation_turning.py     # MODIFY: + validate_target_feed_rate() cases
├── contract/
│   ├── test_library_api_turning.py                          # MODIFY: + feed_per_rotation assertions on standard mode
│   ├── test_library_api_turning_fixed_rpm.py                 # MODIFY: + feed_per_rotation assertions
│   ├── test_library_api_turning_power_constrained.py         # MODIFY: + feed_per_rotation assertions
│   ├── test_library_api_turning_feed_rate_constrained.py     # NEW
│   └── test_library_api_turning_feed_rate_constrained_errors.py  # NEW
└── integration/
    └── test_tui_turning.py            # MODIFY: + feed-rate-constrained mode row visibility, nudge-step assertions
```

**Structure Decision**: Reuses the existing single-package `src/` layout
unmodified. Every change is additive to already-existing files; no new
top-level package or module is introduced. Genuinely shared, operation-
agnostic infrastructure (`CalculationMode`, `CalculationResult`,
`validate_mode_arguments`, `NumberRow`/`power_and_rpm_rows`/`FieldId`) is
extended in place, with every extension defaulted/optional so drilling's and
milling's own files and call sites require zero changes (Constitution
Principle VI) — only `processes/machining/turning/` and
`console/tui/screens/turning.py` gain feature-specific logic.

## Complexity Tracking

*No entries — the Constitution Check above found no violations requiring justification.*
