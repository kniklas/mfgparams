# Implementation Plan: Turning Combined-Constraint Modes & Machining Menu Auto-Hide

**Branch**: `021-turning-combined-constraints` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-turning-combined-constraints/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Add two new turning-only `CalculationMode` members — `ROTATION_AND_FEED_CONSTRAINED`
(spindle speed + feed per rotation both supplied directly, neither derived) and
`POWER_AND_FEED_CONSTRAINED` (available power + feed per rotation both fixed; spindle
speed solved to the highest value feasible within that power at that feed) — and fix
the console TUI's Machining menu to hide while an operation screen is open and
reappear on exit, symmetrically for all three operations.

The key architectural finding from tracing the existing code (`019-turning-calculations`,
`020-turning-feed-per-rotation`): both new modes are **pure recombinations of inputs and
error codes `calculate_turning()` already has** (`target_rpm`, `available_power`,
`target_feed_rate`; `INVALID_TARGET_RPM`, `INVALID_TARGET_FEED_RATE`, `MODE_CONFLICT`,
`INFEASIBLE_POWER_BUDGET`, `CALCULATION_OVERFLOW`). No new parameter, no new
`CalculationResult` field, and no new error code are needed — only two new enum
members, one new formula function (`ROTATION_AND_FEED_CONSTRAINED` needs none at all;
it is a direct call to the existing `calculate_turning_metrics_at_rpm()`), and
extensions to five existing `if`/dispatch blocks reusing the exact precedence pattern
`020`'s own PR #101 review already established (mode-conflict checks before a mode's
own-value validity checks). The Machining-menu fix is a single-line change
(`view.body_mode = None` in `app.py`'s `_activate_tree_row()`) — the restore-on-exit
logic already exists in both Escape handlers, left over from an earlier revision that
deliberately decoupled the two, and happens to do exactly what this feature needs.

## Technical Context

**Language/Version**: Python >=3.9 (existing project baseline, `pyproject.toml`)

**Primary Dependencies**: None new. `prompt-toolkit>=3.0,<4.0` (existing `console` extra,
already used by every TUI file this feature touches).

**Storage**: N/A (stateless calculation library; TUI session state is in-memory only,
per existing `TurningSessionState`/`SessionUI` pattern).

**Testing**: `pytest` (existing suite: `tests/unit/`, `tests/contract/`, `tests/integration/`).

**Target Platform**: Existing cross-platform CLI/TUI (Debian-stable-compatible, per
Constitution Principle V); no new platform constraint.

**Project Type**: Single Python library + console TUI (existing `src/` layout).

**Performance Goals**: Both new modes are O(1) closed-form (no iteration/search) —
`ROTATION_AND_FEED_CONSTRAINED` is a direct formula evaluation;
`POWER_AND_FEED_CONSTRAINED` reuses `POWER_CONSTRAINED`'s existing linear-scaling
algebra (`020-turning-calculations/research.md #1`), just seeded from a
caller-supplied feed instead of a material/tool-derived one. Identical cost profile
to every existing turning mode; the 0.5-1.0s/legacy-hardware target (Principle V) is
unaffected.

**Constraints**: Same ~64-128MB RAM / single-threaded-CPU / Debian-stable envelope as
`019-turning-calculations`/`020-turning-feed-per-rotation` (Constitution Principle V);
no exceptions raised for expected validation failures — every new failure path reuses
an existing error code (`INVALID_TARGET_RPM`, `INVALID_TARGET_FEED_RATE`,
`MODE_CONFLICT`, `INFEASIBLE_POWER_BUDGET`, `CALCULATION_OVERFLOW`), none new.

**Scale/Scope**: Extends one existing process (`turning`) from four calculation modes
to six; no new process, no new registry, no new top-level library entry point, no new
`calculate_turning()` parameter, no new `CalculationResult` field. Also fixes one
existing TUI interaction bug (Machining menu visibility) shared by all three
operations, localized to a single function in `app.py`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Code Quality)**: `ROTATION_AND_FEED_CONSTRAINED` adds zero new
  formula code — it calls the existing `calculate_turning_metrics_at_rpm()` directly
  with both arguments supplied. `POWER_AND_FEED_CONSTRAINED` adds one new, single-
  responsibility wrapper function reusing the existing `_derive_standard_spindle_speed_rpm()`
  helper (itself extracted during `020`'s PR #101 review specifically to prevent
  formula duplication) — no duplicated formula chain. PASS.
- **Principle II (Testing Standards)**: New unit tests for the new formula function
  (nominal/boundary/zero/negative/non-finite feed and power), contract tests for both
  new modes' success shape, error codes, and mode-conflict symmetry (mirroring
  `test_library_api_turning_feed_rate_constrained*.py`'s existing structure), and an
  integration test for the TUI's Machining-menu hide/show behavior. PASS (detailed in
  Phase 1 `quickstart.md`/`tasks.md`).
- **Principle III (Calculation Robustness & Accuracy)**: Every new mode's result
  passes through the existing `_reject_if_invalid()` finiteness/positivity guard,
  unchanged — no new numerical edge case class is introduced (`POWER_AND_FEED_CONSTRAINED`'s
  algebra is the same linear scaling already exercised, at zero-budget and
  subnormal-input, by `POWER_CONSTRAINED`'s existing tests). PASS.
- **Principle IV (Python Packaging & Versioning)**: Additive-only public API surface
  (two new enum members; zero signature/field changes) — MINOR version bump, not
  MAJOR, consistent with `020`'s own precedent for the same kind of change. PASS.
- **Principle V (Resource-Constrained Compatibility)**: No new dependency; both new
  modes are O(1) closed-form, identical cost profile to the existing four. PASS.
- **Principle VI (Extensibility by Design)**: Both new modes extend already-shared,
  operation-agnostic infrastructure (`CalculationMode`, `validate_mode_arguments`) —
  turning-only calculation dispatch, mirroring `010-milling-calculation-modes`'s and
  `020`'s own precedent. Learning directly from `020`'s PR #101 review (a Copilot
  finding there: the shared enum member was reachable through drilling's/milling's own
  public signatures and silently fell through to a mislabeled standard-mode result),
  this feature adds the `UNSUPPORTED_MODE` guard for **both** new modes to drilling's
  and milling's own `_validate_mode_inputs()` from the start, in the same PR — not as
  a follow-up review fix. PASS.
- **Principle VII (Documentation & Publishing)**: Sphinx docs (`docs/source/turning.rst`,
  `docs/source/turning-api.rst`) updated to document the two new modes and the
  Machining-menu behavior change. PASS.
- **Principle VIII (Internationalization)**: Two new mode-selector catalog entries
  (`tui.mode.rotation_and_feed_constrained`, `tui.mode.power_and_feed_constrained`) are
  required (new mode names have no existing translation to reuse). Every other new
  user-facing string is a **reuse** of an existing catalog entry: both new modes'
  result-panel spindle-speed labels reuse `FIXED_RPM`'s ("user-specified") and
  `POWER_CONSTRAINED`'s ("adjusted to fit available power") existing keys respectively,
  since the spindle speed's own derivation nature is identical even though the feed
  value's source differs — avoiding the near-duplicate-string pattern Principle VIII's
  FR-013-style guidance (`020-turning-feed-per-rotation` FR-013) warns against. PASS.
- **Principle IX (Automated Gates)**: No change to CI configuration; existing
  complexity/security/dependency/CodeQL gates apply unchanged. `_compute_metrics()`'s
  and `_validate_mode_inputs()`'s cyclomatic complexity grow by two `if` branches
  each — within the same shape the existing four-mode dispatch already has; to be
  confirmed against the configured `max-complexity` threshold during implementation,
  not assumed. PASS (pending CI confirmation, not a known violation).
- **Principle X/XI/XII**: Not implicated (no licensing change; no per-agent
  instruction file touched; feature is scoped to fit one pull request, matching
  `020`'s own single-PR precedent — see Complexity Tracking below for why a long-lived
  integration branch is not used).

No unjustified violations. Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/021-turning-combined-constraints/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── library-api-turning-combined-constraints-delta.md
│   ├── cli-repl-turning-combined-constraints-delta.md
│   └── tui-machining-menu-auto-hide-delta.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mfgparams/
├── models.py                                    # MODIFY: + CalculationMode.ROTATION_AND_FEED_CONSTRAINED, .POWER_AND_FEED_CONSTRAINED (enum members + docstring)
├── validation.py                                 # MODIFY: validate_mode_arguments() gains two branches sharing POWER_CONSTRAINED's/FIXED_RPM's existing logic (no new validator functions -- validate_target_rpm()/validate_target_feed_rate() are reused as-is)
├── locales/en.py                                 # No new keys (every new error path reuses an existing error.* catalog entry)
├── console/locales/en.py                         # MODIFY: + tui.mode.rotation_and_feed_constrained, tui.mode.power_and_feed_constrained (2 new keys; every other new UI string reuses an existing key)
├── console/tui/forms.py                          # MODIFY: _SPINDLE_SPEED_MODE_LABEL_KEYS gains 2 entries (required -- FEED_RATE_CONSTRAINED's own dict-KeyError bug, research.md #9 in 020, is the exact class of bug this must not repeat)
├── console/tui/app.py                            # MODIFY: _activate_tree_row() gains one line (view.body_mode = None) -- Machining-menu auto-hide fix
├── console/tui/screens/split_pane.py             # MODIFY: power_and_rpm_rows() gains two new defaulted keyword parameters/branches (rotation_and_feed_constrained, power_and_feed_constrained)
├── console/tui/screens/turning.py                # MODIFY: + 2 _MODE_OPTION_KEYS entries; rows_for() passes the two new power_and_rpm_rows() booleans (reuses existing _rpm_row()/_feed_rate_row()/_power_row() closures unchanged)
└── processes/machining/
    ├── turning/
    │   ├── __init__.py                           # MODIFY: calculate_turning() -- ZERO new parameters; _validate_mode_inputs() extends 2 existing if-conditions + the reverse-conflict check; _compute_metrics() gains 2 new dispatch branches; _build_result()'s feasibility-warning exclusion extends to the new hard-constraint mode
    │   └── formulas.py                            # MODIFY: + calculate_turning_power_and_feed_constrained_metrics() (new, reuses _derive_standard_spindle_speed_rpm()); ROTATION_AND_FEED_CONSTRAINED needs no new formula function
    ├── drilling/__init__.py                       # MODIFY: _validate_mode_inputs()'s existing FEED_RATE_CONSTRAINED-rejection check extends to also reject the two new modes (UNSUPPORTED_MODE) -- proactively, not as a follow-up review fix (see Constitution Check, Principle VI)
    └── milling/_calculate.py                      # MODIFY: same extension as drilling/__init__.py, mirrored

docs/source/
├── turning.rst                                   # MODIFY: document the two new modes
└── turning-api.rst                               # MODIFY: document the two new CalculationMode members

tests/
├── unit/processes/machining/turning/
│   └── test_formulas_power_and_feed_constrained.py   # NEW: unit tests for the one new formula function
├── contract/
│   ├── test_library_api_turning_rotation_and_feed_constrained.py       # NEW
│   ├── test_library_api_turning_rotation_and_feed_constrained_errors.py # NEW
│   ├── test_library_api_turning_power_and_feed_constrained.py          # NEW
│   ├── test_library_api_turning_power_and_feed_constrained_errors.py   # NEW
│   ├── test_mode_conflict.py                                            # MODIFY: + drilling UNSUPPORTED_MODE tests for the two new modes
│   └── test_milling_mode_conflict.py                                    # MODIFY: + milling UNSUPPORTED_MODE tests for the two new modes
└── integration/
    ├── test_tui_turning.py                                              # MODIFY: + mode-selector/row-set tests for both new modes
    └── test_tui_navigation.py                                           # MODIFY: + assertion that body_mode is hidden while an operation is open, for all three operations
```

**Structure Decision**: No new modules. Every change lands inside the existing
`turning`/`drilling`/`milling` packages and the existing shared TUI infrastructure
(`app.py`, `split_pane.py`, `forms.py`), following the identical extension pattern
`020-turning-feed-per-rotation` already established (Constitution Principle VI). No
new top-level directory, no new test category.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

None — no violations.
