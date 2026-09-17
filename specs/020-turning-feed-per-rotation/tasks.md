# Tasks: Turning Feed Rate Per Rotation & Constrained Mode

**Input**: Design documents from `specs/020-turning-feed-per-rotation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/library-api-turning-feed-per-rotation-delta.md, contracts/cli-repl-turning-feed-per-rotation-delta.md, quickstart.md

**Tests**: Included as mandatory tasks (not optional) — Constitution Principle II (Testing Standards, NON-NEGOTIABLE) requires unit tests for every calculation function and ≥90% coverage on calculation modules, consistent with `019-turning-calculations`'s and `010-milling-calculation-modes`'s tasks.md.

**Organization**: Tasks are grouped by user story (US1 = feed-per-rotation on every mode, P1; US2 = feed-rate-constrained mode, P2; US3 = arrow-key nudge step, P3) per spec.md priorities, on top of a shared Foundational phase (every mode's result needs the same `feed_per_rotation` surfacing plumbing — research.md #1/#2/#4/#6/#9/#10 — before US2's new mode or US3's nudge step have anything to build on).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow the existing single-project `src/mfgparams/` + `tests/` layout (no changes to plan.md's Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new tooling/dependencies are introduced by this feature (plan.md Technical Context); this phase only confirms the existing tooling covers the new code paths.

- [X] T001 Confirm `pytest`, `pytest-cov`, `ruff`, `black`, `mypy` configuration in `pyproject.toml` already covers new/modified modules under `src/mfgparams/processes/machining/turning/` and `src/mfgparams/console/tui/` with no config changes needed (no new dependency added per plan.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Surface the `feed_per_rotation` value turning's formula layer already computes internally, on the `CalculationResult` every mode returns — required for User Story 1 directly, and the prerequisite every later story's own new code (US2's new mode, US3's nudge step) builds on top of.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add a `feed_per_rev_mm: float` field to `TurningMetrics` and give `calculate_turning_metrics_at_rpm()` a new optional `feed_per_rev_mm: float | None = None` parameter in `src/mfgparams/processes/machining/turning/formulas.py`: when `None` (every existing call site, unchanged), derive it from `material`/`tool` exactly as today; when supplied, use it directly and return it in the new field either way (research.md #1/#2; data-model.md)
- [X] T003 [P] Add `feed_per_rotation: float | None = None` to `CalculationResult` in `src/mfgparams/models.py`, appended after the existing `cutting_force` field (same positional-construction-compatibility placement `cutting_force`/`material_removal_rate` themselves established); add a matching `Attributes:` entry to the class docstring, mirroring the existing `cutting_force` paragraph (Constitution I) (research.md #4; data-model.md)
- [X] T004 Update `_build_result()` in `src/mfgparams/processes/machining/turning/__init__.py` to compute `feed_per_rotation` from `metrics.feed_per_rev_mm` (via `mm_to_in()` under IMPERIAL, as-is under METRIC — mirroring `cutting_force`'s existing conditional exactly) and pass it into the returned `CalculationResult`; update `_error_result()` to pass `feed_per_rotation=None` (depends on T002, T003)
- [X] T005 Extend `_reject_if_invalid()`'s finiteness/positivity guard tuple in `src/mfgparams/processes/machining/turning/__init__.py` to also check `metrics.feed_per_rev_mm` (research.md #6; depends on T002)
- [X] T006 [P] Add `"feed_per_rotation": "mm/rev"` (METRIC) / `"in/rev"` (IMPERIAL) to `UNIT_LABELS` in `src/mfgparams/console/tui/forms.py` (data-model.md)
- [X] T007 Add a `tui.result.feed_per_rotation` catalog key (`"Feed per rotation:  {value} {unit}"`) to `src/mfgparams/console/locales/en.py`, and update `format_result()` in `src/mfgparams/console/tui/forms.py` to append a new line — conditional on `result.feed_per_rotation is not None`, placed immediately after the existing `tui.result.feed_rate` line — mirroring the existing `material_removal_rate`/`cutting_force` optional-line pattern (research.md #10; depends on T003, T006)
- [X] T008 [P] Unit tests for the new `feed_per_rev_mm` field and optional parameter on `calculate_turning_metrics_at_rpm()`, `calculate_turning_metrics()`, and `calculate_turning_power_constrained_metrics()` (nominal derivation case, and that an explicitly supplied `feed_per_rev_mm` overrides the material/tool-derived one) in `tests/unit/processes/machining/turning/test_formulas.py` and `tests/unit/processes/machining/turning/test_formulas_at_rpm.py` (depends on T002)

**Checkpoint**: `TurningMetrics`/`CalculationResult` carry `feed_per_rotation` end-to-end for every mode that already exists; fully unit-tested. User story phases below add story-specific tests, the new mode, and the nudge step on top.

---

## Phase 3: User Story 1 - Read Turning Feed Rate as an Amount Per Workpiece Rotation (Priority: P1) 🎯 MVP

**Goal**: Every turning calculation result (standard, fixed-RPM, power-constrained) includes a feed-per-rotation value alongside the existing, unchanged feed rate (spec.md User Story 1).

**Independent Test**: Call `calculate_turning()` in each of the three existing modes and verify the result includes a populated `feed_per_rotation` (mm/rev/in/rev) while `feed_rate`'s value and meaning are identical to `019-turning-calculations`'s existing behavior (quickstart.md Scenario 1).

### Tests for User Story 1 ⚠️

- [X] T009 [P] [US1] Contract test: standard-mode `calculate_turning()` result includes a populated `feed_per_rotation` and `feed_per_rotation * spindle_speed_rpm` reconstructs `feed_rate` (within `math.isclose` tolerance), while every other field's value is unchanged from the existing baseline, in `tests/contract/test_library_api_turning.py`
- [X] T010 [P] [US1] Contract test: fixed-RPM mode result includes a populated `feed_per_rotation` in `tests/contract/test_library_api_turning_fixed_rpm.py`
- [X] T011 [P] [US1] Contract test: power-constrained mode result includes a populated `feed_per_rotation` in `tests/contract/test_library_api_turning_power_constrained.py`
- [X] T012 [P] [US1] Integration test: the turning TUI screen's result panel displays the new "Feed per rotation" line immediately after "Feed rate" for a standard-mode calculation, in `tests/integration/test_tui_turning.py`

### Implementation for User Story 1

- [X] T013 [US1] Update `calculate_turning()`'s docstring in `src/mfgparams/processes/machining/turning/__init__.py` to document the new `feed_per_rotation` result field and its units under each `UnitSystem` (Constitution I; depends on T004)

**Checkpoint**: User Story 1 is fully functional and independently testable — every existing turning mode reports feed rate per rotation, with zero change to any other reported value.

---

## Phase 4: User Story 2 - Choose a Feed-Rate-Constrained Turning Calculation Mode (Priority: P2)

**Goal**: A caller can select a new feed-rate-constrained mode, supplying a target feed rate per rotation directly; spindle speed is still derived exactly as standard mode, and every dependent metric (machining time, cutting force, torque, power) is recomputed from the supplied feed rate (spec.md User Story 2).

**Independent Test**: Call `calculate_turning(mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=...)` directly (library) and via the TUI's new mode option, and verify: (a) `spindle_speed_rpm` matches the standard-mode value for the same diameter/material/tool, (b) `feed_per_rotation` equals the supplied value exactly, (c) `cutting_force`/`torque`/`power_required` are recomputed from it, (d) a missing/invalid `target_feed_rate` is rejected as `INVALID_TARGET_FEED_RATE`, and (e) combining it with `target_rpm` or another mode is rejected as `MODE_CONFLICT` (quickstart.md Scenario 2).

### Tests for User Story 2 ⚠️

- [X] T014 [P] [US2] Unit tests for `validate_target_feed_rate()` (nominal positive value, zero, negative, non-numeric, `NaN`, `Infinity`, and `None`-is-not-an-error) in `tests/unit/test_validation_turning.py`
- [X] T015 [P] [US2] Unit tests for `calculate_turning_feed_rate_constrained_metrics()` (spindle speed matches `calculate_turning_metrics()`'s standard-mode derivation for the same inputs; `feed_per_rev_mm` echoes the supplied value; dependent metrics recomputed from it) in new `tests/unit/processes/machining/turning/test_formulas_feed_rate_constrained.py`
- [X] T016 [P] [US2] Contract test for the feed-rate-constrained success response shape (contracts/library-api-turning-feed-per-rotation-delta.md), including a case where a supplied `available_power` below the required power at the derived spindle speed produces `feasibility_warning` (and a sufficient one does not — FR-008), in new `tests/contract/test_library_api_turning_feed_rate_constrained.py`
- [X] T017 [P] [US2] Contract test for `INVALID_TARGET_FEED_RATE` (missing, zero, negative, non-numeric `target_feed_rate`) and `MODE_CONFLICT` (`target_feed_rate` supplied together with `target_rpm` under `mode=FEED_RATE_CONSTRAINED`; `target_feed_rate` supplied while `mode` is `STANDARD`/`POWER_CONSTRAINED`/`FIXED_RPM` — FR-007), plus a case confirming `MISSING_MATERIAL`/`MISSING_TOOL` is still returned (not superseded by a feed-rate-specific error) when material/tool are absent under `mode=FEED_RATE_CONSTRAINED` (FR-009), in new `tests/contract/test_library_api_turning_feed_rate_constrained_errors.py`
- [X] T018 [P] [US2] Integration test for the TUI's feed-rate-constrained mode selection: the mode row offers the new option; selecting it shows the required "Feed rate per rotation" row and hides the Target spindle speed row; the result panel renders without error and shows the new mode's spindle-speed label, in `tests/integration/test_tui_turning.py`

### Implementation for User Story 2

- [X] T019 [US2] Add `FEED_RATE_CONSTRAINED = "feed-rate-constrained"` to `CalculationMode` in `src/mfgparams/models.py`; add a matching `Attributes:` entry to the enum's docstring, mirroring the existing `STANDARD`/`POWER_CONSTRAINED`/`FIXED_RPM` entries (Constitution I) (data-model.md)
- [X] T020 [US2] Add a `CalculationMode.FEED_RATE_CONSTRAINED` entry to `_SPINDLE_SPEED_MODE_LABEL_KEYS` (`"tui.result.spindle_speed.mode.feed_rate_constrained"`) in `src/mfgparams/console/tui/forms.py`, and add that catalog key (`"derived from cutting speed"` — corrected from an earlier draft's physically-inaccurate `"derived from specified feed rate"` per a Copilot review finding) to `src/mfgparams/console/locales/en.py` — required to prevent a `KeyError` on every feed-rate-constrained result (research.md #9; depends on T019)
- [X] T021 [US2] Add `validate_target_feed_rate(target_feed_rate, locale)` to `src/mfgparams/validation.py`, mirroring `validate_target_rpm()`'s shape exactly (positive/finite required when supplied, `None` is not itself an error); add the `error.invalid_target_feed_rate` catalog entry to `src/mfgparams/locales/en.py` (research.md #5; depends on T019)
- [X] T022 [US2] Extend `validate_mode_arguments()` in `src/mfgparams/validation.py` with a `CalculationMode.FEED_RATE_CONSTRAINED` branch: reject a simultaneously supplied `target_rpm` as `MODE_CONFLICT` (mirroring `POWER_CONSTRAINED`'s existing rejection), otherwise delegate to the existing `_validate_advisory_available_power()` (research.md #3; depends on T019)
- [X] T023 [US2] Add `calculate_turning_feed_rate_constrained_metrics(diameter_mm, depth_of_cut_mm, length_of_cut_mm, material, tool, target_feed_per_rev_mm)` to `src/mfgparams/processes/machining/turning/formulas.py`: derive spindle speed exactly as `calculate_turning_metrics()`, then delegate to `calculate_turning_metrics_at_rpm(..., feed_per_rev_mm=target_feed_per_rev_mm)` (research.md #2; depends on T002, T019)
- [X] T024 [US2] Add a `target_feed_rate: float | None = None` parameter to `calculate_turning()`. Extend `_validate_mode_inputs()` to: (a) reject `target_feed_rate` supplied while `mode is not FEED_RATE_CONSTRAINED` as `MODE_CONFLICT` (turning-local check — the shared `validate_mode_arguments()` is not touched for this direction); (b) validate it via T021 and require it when `mode is FEED_RATE_CONSTRAINED`. Add a `target_feed_rate_mm = to_metric_length(target_feed_rate, unit_system)` conversion step in `_validate_and_prepare()`, mirroring the existing `available_power_kw` conversion, and add it to that function's returned tuple. Add `target_feed_rate_mm` as a new parameter to `_compute_metrics()`, with a new `FEED_RATE_CONSTRAINED` dispatch branch calling T023's function and `_reject_if_invalid()`. All in `src/mfgparams/processes/machining/turning/__init__.py` (depends on T020, T021, T022, T023)
- [X] T025 [P] [US2] Add `tui.mode.feed_rate_constrained` (`"feed-rate-constrained"`) and `tui.label.target_feed_rate` (`"Feed rate per rotation"`) catalog keys to `src/mfgparams/console/locales/en.py`
- [X] T026 [P] [US2] Add `FieldId.TARGET_FEED_RATE = "target_feed_rate"` to `src/mfgparams/console/tui/app.py`
- [X] T027 [P] [US2] Extend `power_and_rpm_rows()` in `src/mfgparams/console/tui/screens/split_pane.py` with two new, defaulted keyword parameters — `feed_rate_constrained: bool = False` and `feed_rate_row: Callable[[], NumberRow] | None = None` — dispatching to `[feed_rate_row(), power_row(optional)]` when `feed_rate_constrained` is true, before the existing standard-mode fallback (data-model.md; drilling's/milling's existing call sites are unaffected since neither passes these new parameters)
- [X] T028 [US2] In `src/mfgparams/console/tui/screens/turning.py`: add a fourth `_MODE_OPTION_KEYS` entry for `CalculationMode.FEED_RATE_CONSTRAINED`; add `target_feed_rate: float | None = None` to `TurningSessionState`; extend `_convert_on_unit_change()` to convert it via `forms.convert_length()`; extend `_set_mode()`'s existing clearing block to also clear `target_feed_rate` on a mode change; add a `_feed_rate_row()` factory (required `NumberRow`, `FieldId.TARGET_FEED_RATE`, `tui.label.target_feed_rate`, `labels["feed_per_rotation"]`) and pass it plus `feed_rate_constrained=state.mode is CalculationMode.FEED_RATE_CONSTRAINED` into `power_and_rpm_rows()`; pass `target_feed_rate=state.target_feed_rate` through in `calculate_result()` (depends on T024, T025, T026, T027)
- [X] T029 [US2] Update `calculate_turning()`'s docstring in `src/mfgparams/processes/machining/turning/__init__.py` to document `target_feed_rate` and `FEED_RATE_CONSTRAINED` mode (Constitution I; depends on T024)

**Checkpoint**: User Story 2 (feed-rate-constrained mode) is fully functional and independently testable via both the library and the TUI.

---

## Phase 5: User Story 3 - Fine-Tune Feed Rate Per Rotation with Arrow Keys (Priority: P3)

**Goal**: In the TUI, the feed-rate-per-rotation field nudges by 0.1 mm/rev (METRIC) / 0.005 in/rev (IMPERIAL) via Left/Right arrows, distinct from every other numeric field's existing 1.0-display-unit step (spec.md User Story 3).

**Independent Test**: With feed-rate-constrained mode selected, select the Feed rate per rotation field and press Right/Left arrows, verifying the value changes by 0.1 (METRIC) / 0.005 (IMPERIAL) per press, while every other turning row (diameter, depth of cut, length of cut, available power, target RPM) still nudges by 1.0, unchanged (quickstart.md Scenario 3).

**Note**: This story depends on User Story 2's new field existing (spec.md: "a usability refinement on top of User Story 2's new editable field") — it is not independently deliverable before US2, only independently *testable* once both are in place.

### Tests for User Story 3 ⚠️

- [X] T030 [P] [US3] Unit/integration test confirming `NumberRow.step` defaults to the existing `NUDGE_STEP` (`1.0`) and that every pre-existing drilling/milling/turning row's nudge amount is unchanged by this feature, in `tests/integration/test_tui_field_editing.py`
- [X] T031 [P] [US3] Integration test: turning's Feed rate per rotation field nudges by `0.1` under METRIC and `0.005` under IMPERIAL via Left/Right arrows, distinct from turning's other rows' default `1.0` step, in `tests/integration/test_tui_turning.py`
- [X] T032 [P] [US3] Integration test: the Feed rate per rotation field's remembered value converts correctly (not silently relabeled) across a mid-session unit-system switch, mirroring milling's existing `feed_per_tooth` field test, in `tests/integration/test_tui_turning.py`

### Implementation for User Story 3

- [X] T033 [US3] Add a `step: float = NUDGE_STEP` field to `NumberRow`, and change `nudge_selected()` to compute `new_value = current + direction * row.step` instead of using the module-level `NUDGE_STEP` constant directly, in `src/mfgparams/console/tui/screens/split_pane.py` (research.md #7; depends on T027)
- [X] T034 [US3] Set `step=0.1 if state.unit_system is UnitSystem.METRIC else 0.005` on the `_feed_rate_row()` factory in `src/mfgparams/console/tui/screens/turning.py` (research.md #7; depends on T028, T033)

**Checkpoint**: All three user stories are independently functional; the feed-rate-per-rotation field is fully usable by typing or by arrow-key nudge, in either unit system.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression validation, and quality gates spanning all three user stories.

- [X] T035 [P] Update `docs/source/turning.rst` (end-user docs) and `docs/source/turning-api.rst` (API reference) to document `feed_per_rotation`, the feed-rate-constrained mode, and `target_feed_rate`, mirroring how `019-turning-calculations` documented `cutting_force` (Constitution VII)
- [X] T036 [P] Add a `CHANGELOG.md` bullet under `## [Unreleased]` → `### Added` documenting the new `feed_per_rotation` result field and the feed-rate-constrained calculation mode, and bump `src/mfgparams/__init__.py`'s `__version__` from `2.2.0` to `2.3.0` (Constitution Principle IV: additive, non-breaking API surface → MINOR version)
- [X] T037 Regression test: run the full existing `019-turning-calculations` turning test suite unmodified and confirm 100% pass with no assertion changed, proving SC-005 (no behavior change to any pre-existing turning result value)
- [X] T038 Run `pytest --cov=mfgparams --cov-report=term-missing` (unfiltered — the full suite, including drilling's and milling's existing tests) and confirm ≥90% coverage is maintained on calculation modules including the new `formulas.py`/`validation.py`/`turning/__init__.py` code paths (Constitution II); address any gaps. This full-suite run is what proves FR-014's no-regression guarantee for the shared-file edits (`CalculationMode`, `validate_mode_arguments`, `NumberRow`, `power_and_rpm_rows`, `FieldId`) — T037 alone only re-runs turning's own suite
- [X] T039 Execute all 3 quickstart.md scenarios (including the manual TUI scenario) plus the regression check, and confirm actual behavior matches documented expected outcomes
- [X] T040 [P] Static check confirming no literal user-facing strings were introduced in `turning.py`'s/`forms.py`'s new mode-option/field-label/result-line code paths outside the message catalog (Constitution VIII; `tests/static/test_no_hardcoded_strings.py`)
- [X] T041 Run the full quality-gate suite (`mypy`, `ruff`, `radon`/`xenon` complexity, `bandit`, `pip-audit`) per Constitution Principle IX and confirm no new findings introduced by this feature's changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all three user stories (US2's new formula function calls the T002-extended `calculate_turning_metrics_at_rpm()`; US1 needs T002-T007 directly; US3 needs a field that only exists once US2 lands).
- **User Story 1 (Phase 3)**: Depends only on Foundational completion.
- **User Story 2 (Phase 4)**: Depends only on Foundational completion — independent of User Story 1's own tasks (different tests, one shared docstring-adjacent file touched non-conflictingly).
- **User Story 3 (Phase 5)**: Depends on User Story 2's `_feed_rate_row()`/`TurningSessionState.target_feed_rate` (T028) existing — not independent of US2, per spec.md's own framing of US3 as a refinement on US2's field.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependency on User Story 2 or 3.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2). No dependency on User Story 1's tasks (though both may be worked in parallel by different contributors without conflict, since they touch different tests and mostly non-overlapping lines of the shared files).
- **User Story 3 (P3)**: Can start its tests (T030) after Foundational, but its turning-specific tests (T031, T032) and implementation (T033, T034) require User Story 2's T027/T028 to exist first.

### Within Each User Story

- Tests are written before/alongside implementation and MUST fail before the corresponding implementation task lands (Constitution II).
- Foundational plumbing (T002-T008) before any story-specific implementation.
- Within US2: T019 (enum member) before T020-T024 (everything else references it); T024 (library dispatch) before T028 (TUI wiring that calls it via `calculate_result()`).
- Within US3: T033 (generic `step` mechanism) before T034 (turning's specific step values).

### Parallel Opportunities

- T002, T003, T006 (different files, no dependency between them) can run in parallel; T004, T005 both depend on T002/T003 and touch the same file (sequential).
- T009-T012 (US1 tests) can run in parallel with each other, and with T014-T018 (US2 tests) and T030 (US3's generic test) once Phase 2 completes.
- T014, T015, T016, T017, T018 (US2 tests, different files) can run in parallel with each other.
- T025, T026, T027 (US2 implementation, different files) can run in parallel with each other; T028 depends on all three.
- T030, T031, T032 (US3 tests) can run in parallel with each other.
- T035, T036, T040 (Polish) can run in parallel; T037, T038, T039, T041 are sequential validation gates run after implementation is complete.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent Foundational tasks together:
Task: "Add feed_per_rev_mm field + optional parameter to formulas.py"
Task: "Add feed_per_rotation field to CalculationResult in models.py"
Task: "Add feed_per_rotation unit labels to forms.py"
```

## Parallel Example: User Story 2 Implementation

```bash
# Launch independent US2 implementation tasks together (after T019-T024 land):
Task: "Add tui.mode.feed_rate_constrained / tui.label.target_feed_rate catalog keys"
Task: "Add FieldId.TARGET_FEED_RATE to app.py"
Task: "Extend power_and_rpm_rows() in split_pane.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all three stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md Scenario 1 and confirm SC-001/SC-005
5. Deploy/demo if ready — every existing turning calculation already shows feed rate per rotation, the foundational correctness fix the feature request opened with

### Incremental Delivery

1. Complete Setup + Foundational → `feed_per_rotation` surfaced on every existing mode
2. Add User Story 1 → test independently → deploy/demo (MVP!)
3. Add User Story 2 (feed-rate-constrained mode) → test independently → deploy/demo
4. Add User Story 3 (arrow-key nudge step) → test independently → deploy/demo
5. Polish (docs, changelog/version, coverage, quickstart validation, quality gates) → final release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (mostly tests + docstring — quick)
   - Developer B: User Story 2 (the bulk of the new logic)
3. Developer A joins Developer B (or starts User Story 3's tests) once US1 is done, since US3 needs US2's field to exist before its own implementation tasks can start

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing (Constitution II)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- No new runtime dependencies, CI workflows, or top-level modules are introduced by this feature (plan.md); Polish phase reuses the existing CI/CD, Sphinx, and README infrastructure from `019-turning-calculations`
- No task above modifies drilling's or milling's own calculation behavior (FR-014) — every shared-infrastructure task (T003, T019, T022, T027, T033) is additive/defaulted so drilling's and milling's existing call sites are unaffected. Phase 8 (added after a Copilot review round found the enum member was reachable through drilling's/milling's own public signatures) adds one small, explicit guard to each — see below.

---

## Phase 7: Convergence

- [X] T042 Add a contract test asserting `CALCULATION_OVERFLOW` (not a silently-wrong success) for an extreme-input feed-rate-constrained request (e.g. a subnormal `target_feed_rate` combined with a subnormal `diameter`/`depth_of_cut`) in `tests/contract/test_library_api_turning_feed_rate_constrained_errors.py`, mirroring the existing `test_extreme_subnormal_geometry_returns_structured_overflow_error_not_a_stale_success` test already covering `STANDARD` mode per spec.md Edge Cases (partial)

---

## Phase 8: PR #101 review-round fixes

Added after this feature's implementation was opened as a PR and reviewed;
not part of the original task breakdown above. Each item traces to a
specific Copilot review finding.

- [X] T043 Append `target_feed_rate` after the pre-existing
  `materials_config_path` parameter in `calculate_turning()`
  (`src/mfgparams/processes/machining/turning/__init__.py`), instead of
  before it, to keep positional callers backward compatible (CRITICAL
  finding); add a regression test pinning `materials_config_path`'s
  positional index in `tests/contract/test_library_api_turning.py`
- [X] T044 Add an explicit `CalculationMode.FEED_RATE_CONSTRAINED` →
  `UNSUPPORTED_MODE` rejection to drilling's `_validate_mode_inputs()`
  (`src/mfgparams/processes/machining/drilling/__init__.py`) and milling's
  `_validate_mode_inputs()` (`src/mfgparams/processes/machining/milling/
  _calculate.py`); add the `error.unsupported_mode` catalog entry
  (`src/mfgparams/locales/en.py`) and contract tests in
  `tests/contract/test_mode_conflict.py`/`test_milling_mode_conflict.py`
  (HIGH finding)
- [X] T045 Reorder turning's `_validate_mode_inputs()` so the shared
  `validate_mode_arguments()` mode-conflict check runs before
  `target_feed_rate`'s own positive/finite validation, mirroring
  `POWER_CONSTRAINED`'s own established precedent; add a mixed-invalid
  regression test in `tests/contract/test_library_api_turning_feed_rate_constrained_errors.py`
  (HIGH finding)
- [X] T046 Reword the shared `error.mode_conflict` catalog entry
  (`src/mfgparams/locales/en.py`) to be mode-generic instead of naming
  only power-constrained/fixed-RPM inputs (two HIGH findings, one message)
- [X] T047 Correct `tui.result.spindle_speed.mode.feed_rate_constrained`
  from `"derived from specified feed rate"` to `"derived from cutting
  speed"` (`src/mfgparams/console/locales/en.py`); update the matching
  test assertion in `tests/integration/test_tui_turning.py` (MEDIUM
  finding)
- [X] T048 Replace `nudge_selected()`'s blanket `round(..., 6)` (a same-
  round local-review fix for fractional-step float drift that also
  truncated legitimate high-precision input on unrelated fields) with
  `Decimal(str(x))`-based addition in
  `src/mfgparams/console/tui/screens/split_pane.py` (MEDIUM finding)
- [X] T049 Add an IMPERIAL round-trip contract test for
  `target_feed_rate` in
  `tests/contract/test_library_api_turning_feed_rate_constrained.py`,
  asserting `feed_per_rotation`, spindle speed, machining time, cutting
  force, torque, and power required all round-trip correctly (MEDIUM
  finding, then a MEDIUM follow-up finding that torque/power were missing
  from the first draft's assertions)
- [X] T050 Guard `calculate_turning_metrics_at_rpm()`'s externally-supplied
  `feed_per_rev_mm` against `OverflowError` for an arbitrary-precision
  int, mirroring the existing `spindle_speed_rpm` guard
  (`src/mfgparams/processes/machining/turning/formulas.py`); add a
  regression test in
  `tests/unit/processes/machining/turning/test_formulas_feed_rate_constrained.py`
  (LOW finding)
- [X] T051 Correct every spec-kit artifact (`data-model.md`, `research.md`,
  `plan.md`, `spec.md` Assumptions, both `contracts/*.md` deltas,
  `docs/source/turning-api.rst`, this file) that still stated the
  pre-T043/T044 claims — parameter order, "drilling/milling untouched",
  and the stale result label — after a second Copilot review round found
  the T043-T050 fixes had left those documents internally inconsistent
  with the code they describe (multiple MEDIUM findings)
