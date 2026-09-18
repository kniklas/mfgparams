# Tasks: Turning Combined-Constraint Modes & Machining Menu Auto-Hide

**Input**: Design documents from `specs/021-turning-combined-constraints/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/library-api-turning-combined-constraints-delta.md, contracts/cli-repl-turning-combined-constraints-delta.md, contracts/tui-machining-menu-auto-hide-delta.md, quickstart.md

**Tests**: Included as mandatory tasks (not optional) — Constitution Principle II (Testing Standards, NON-NEGOTIABLE) requires unit tests for every calculation function and ≥90% coverage on calculation modules, consistent with `019-turning-calculations`'s and `020-turning-feed-per-rotation`'s tasks.md.

**Organization**: Tasks are grouped by user story (US1 = rotation-and-feed-constrained mode, P1; US2 = power-and-feed-constrained mode, P2; US3 = Machining menu auto-hide, P2) per spec.md priorities, on top of a thin Foundational phase. Unlike `020`'s tasks.md, this feature's Foundational phase is deliberately small: research.md's key finding is that both new modes reuse existing parameters/fields/error codes almost entirely (zero new `calculate_turning()` parameter, zero new `CalculationResult` field, zero new error code) — the only genuinely *shared* prerequisite is the small set of existing `if` conditions that naturally cover **both** new modes in a single edit (the two new enum members, the reverse-conflict check, the `target_feed_rate`-required check, and the drilling/milling `UNSUPPORTED_MODE` guard). Everything else is independent per mode and lives in that mode's own story phase. US3 (Machining menu) is fully independent of US1/US2, touching only `app.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow the existing single-project `src/mfgparams/` + `tests/` layout (no changes to plan.md's Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new tooling/dependencies are introduced by this feature (plan.md Technical Context); this phase only confirms the existing tooling covers the new code paths.

- [X] T001 Confirm `pytest`, `pytest-cov`, `ruff`, `black`, `mypy` configuration in `pyproject.toml` already covers new/modified modules under `src/mfgparams/processes/machining/turning/`, `src/mfgparams/processes/machining/drilling/`, `src/mfgparams/processes/machining/milling/`, and `src/mfgparams/console/tui/` with no config changes needed (no new dependency added per plan.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The handful of edits that genuinely cover **both** new modes in one change — done once here rather than touched twice across two story phases (research.md #4/#7). `CalculationResult`, `validate_target_rpm()`, `validate_target_feed_rate()`, and every error code already exist (added by `019`/`020`) and are reused **unmodified** — no foundational task recreates them.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `ROTATION_AND_FEED_CONSTRAINED = "rotation-and-feed-constrained"` and `POWER_AND_FEED_CONSTRAINED = "power-and-feed-constrained"` to `CalculationMode` in `src/mfgparams/models.py`; add matching `Attributes:` docstring entries for both, mirroring the existing `FEED_RATE_CONSTRAINED` entry's shape (data-model.md "CalculationMode")
- [X] T003 In `src/mfgparams/processes/machining/turning/__init__.py`'s `_validate_mode_inputs()`, extend the reverse-conflict check (`if target_feed_rate is not None and mode is not CalculationMode.FEED_RATE_CONSTRAINED:`) to also permit `ROTATION_AND_FEED_CONSTRAINED` and `POWER_AND_FEED_CONSTRAINED` (research.md #4; depends on T002)
- [X] T004 In `src/mfgparams/processes/machining/turning/__init__.py`'s `_validate_mode_inputs()`, extend the existing `if mode is CalculationMode.FEED_RATE_CONSTRAINED:` own-value-validity block (`validate_target_feed_rate`) to also run for `ROTATION_AND_FEED_CONSTRAINED` and `POWER_AND_FEED_CONSTRAINED` — both new modes require `target_feed_rate` identically (data-model.md "Validation"; depends on T002, T003)
- [X] T005 [P] In `src/mfgparams/processes/machining/drilling/__init__.py`'s `_validate_mode_inputs()`, extend the existing `if mode is CalculationMode.FEED_RATE_CONSTRAINED:` → `UNSUPPORTED_MODE` rejection to also cover `ROTATION_AND_FEED_CONSTRAINED` and `POWER_AND_FEED_CONSTRAINED` (research.md #7; depends on T002)
- [X] T006 [P] Mirror T005 in `src/mfgparams/processes/machining/milling/_calculate.py`'s `_validate_mode_inputs()` (research.md #7; depends on T002)
- [X] T007 [P] Contract tests for T005/T006: `UNSUPPORTED_MODE` for both new modes, for drilling (`calculate()`) in `tests/contract/test_mode_conflict.py`, and for both milling sub-operations (`calculate_end_milling()`/`calculate_face_milling()`) in `tests/contract/test_milling_mode_conflict.py`, mirroring the existing `FEED_RATE_CONSTRAINED` test in each file (depends on T005, T006)

**Checkpoint**: Both new `CalculationMode` members exist; `target_feed_rate` is accepted (and required) under either; drilling/milling reject both with a structured error instead of silently computing a mislabeled standard-mode result. User story phases below add each mode's own remaining validation, formula/dispatch wiring, and TUI surface.

---

## Phase 3: User Story 1 - Run Turning with a Directly Fixed Spindle Speed and Feed Together (Priority: P1) 🎯 MVP

**Goal**: A machinist who already knows their exact spindle speed and feed per rotation gets machining time, cutting force, torque, and power for that exact combination, with neither value derived (spec.md User Story 1).

**Independent Test**: Call `calculate_turning(mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED, target_rpm=..., target_feed_rate=...)` directly and via the console's new mode option; verify the returned `spindle_speed_rpm`/`feed_per_rotation` equal the supplied values exactly, and that machining time/cutting force/torque/power are computed from them (quickstart.md Scenarios 1-2).

### Tests for User Story 1 ⚠️

> **NOTE**: The formulas-layer combination this mode needs (`calculate_turning_metrics_at_rpm()` given both an explicit spindle speed *and* an explicit `feed_per_rev_mm` override simultaneously) is **already covered** by `020`'s existing `test_at_rpm_feed_per_rev_mm_override_replaces_material_tool_derived_value()` in `tests/unit/processes/machining/turning/test_formulas_at_rpm.py` (it asserts both `overridden.spindle_speed_rpm == 500` and `overridden.feed_per_rev_mm == 0.5` from the same call) — no new formulas-layer unit test is needed for this story (research.md #2).
>
> **NOTE**: FR-006 (this mode's optional advisory `available_power`) needs **no implementation task** — `_build_result()`'s existing feasibility-warning condition (`mode is not CalculationMode.POWER_CONSTRAINED`) already includes `ROTATION_AND_FEED_CONSTRAINED`, since it's an exclusion list, not an inclusion list (research.md #6). T009 below exists to prove this stays true, not to implement it.

- [X] T008 [P] [US1] Contract test for the rotation-and-feed-constrained success response shape (`spindle_speed_rpm`/`feed_per_rotation` equal the supplied values exactly, differ from standard mode's derived values, `mode=ROTATION_AND_FEED_CONSTRAINED`) per contracts/library-api-turning-combined-constraints-delta.md in `tests/contract/test_library_api_turning_rotation_and_feed_constrained.py`
- [X] T009 [P] [US1] Contract test for the optional advisory `available_power` behavior in this mode (feasibility warning included when exceeded, absent when not, estimated power still returned when omitted — FR-006) in `tests/contract/test_library_api_turning_rotation_and_feed_constrained.py`
- [X] T010 [P] [US1] Contract test for `INVALID_TARGET_RPM`/`INVALID_TARGET_FEED_RATE` (missing/zero/negative/non-numeric, each field independently, and both simultaneously missing — asserting `INVALID_TARGET_RPM` wins per the parameter-declaration-order precedence, data-model.md); that a directly-supplied `target_rpm` is *accepted*, not rejected as `MODE_CONFLICT` (unlike `POWER_CONSTRAINED`/`FEED_RATE_CONSTRAINED`, this mode has no `MODE_CONFLICT` trigger of its own — `target_rpm` is one of its own two required inputs, corrected by a Copilot review finding on PR #102 that caught this description still describing an original, since-dropped `MODE_CONFLICT` case); and `MISSING_MATERIAL`/`MISSING_TOOL` precedence, in `tests/contract/test_library_api_turning_rotation_and_feed_constrained_errors.py`
- [X] T011 [P] [US1] Contract test asserting `CALCULATION_OVERFLOW` (not a silently-wrong success) for an extreme-input request (e.g. a subnormal `target_feed_rate` combined with subnormal geometry) in `tests/contract/test_library_api_turning_rotation_and_feed_constrained_errors.py`, mirroring `020`'s existing extreme-input test for `FEED_RATE_CONSTRAINED`
- [X] T012 [P] [US1] Integration test for the TUI's rotation-and-feed-constrained mode: the mode row offers the new option; selecting it shows the required Target spindle speed and Feed rate per rotation rows plus the optional Available power row; the resulting `CalculationResult` matches a direct `calculate_turning(mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED, ...)` call field-by-field (FR-009's identical-results guarantee — mirroring the existing per-mode pattern already used by every other mode's test in this file, e.g. `test_feed_rate_constrained_mode_reaches_a_result_matching_the_core_calculation`); the result panel renders without error and shows the "user-specified" spindle-speed label, in `tests/integration/test_tui_turning.py`

### Implementation for User Story 1

- [X] T013 [US1] In `validation.py`'s `validate_mode_arguments()`, update the final fallback branch's comment from `# mode is CalculationMode.FIXED_RPM` to name both `FIXED_RPM` and `ROTATION_AND_FEED_CONSTRAINED` (no functional change — both already reach this branch by not matching any earlier `if`, and both want identical treatment: `target_rpm` never conflicts, `available_power` is advisory); update the function's docstring to add a `ROTATION_AND_FEED_CONSTRAINED` paragraph (research.md #4; depends on T002)
- [X] T014 [US1] In `turning/__init__.py`'s `_validate_mode_inputs()`, extend the existing `if mode is CalculationMode.FIXED_RPM:` own-value-validity block (`validate_target_rpm`) to also run for `ROTATION_AND_FEED_CONSTRAINED` (data-model.md "Validation"; depends on T002, T004)
- [X] T015 [US1] In `turning/__init__.py`'s `_compute_metrics()`, add an `if mode is CalculationMode.ROTATION_AND_FEED_CONSTRAINED:` branch calling the existing `calculate_turning_metrics_at_rpm(diameter_mm, depth_of_cut_mm, length_of_cut_mm, resolved_material, resolved_tool, target_rpm, feed_per_rev_mm=target_feed_rate_mm)` directly (no new formula function, research.md #2), then `_reject_if_invalid(..., error_code="CALCULATION_OVERFLOW", ...)`, mirroring the existing `FIXED_RPM`/`FEED_RATE_CONSTRAINED` branch shapes exactly (depends on T013, T014)
- [X] T016 [P] [US1] Add `tui.mode.rotation_and_feed_constrained` (`"rotation-and-feed-constrained"`) catalog key to `src/mfgparams/console/locales/en.py`
- [X] T017 [P] [US1] Add a `CalculationMode.ROTATION_AND_FEED_CONSTRAINED` entry to `_SPINDLE_SPEED_MODE_LABEL_KEYS` (`"tui.result.spindle_speed.mode.rotation_and_feed_constrained"`) in `src/mfgparams/console/tui/forms.py`, and add that catalog key reusing `FIXED_RPM`'s existing value (`"user-specified"`) in `src/mfgparams/console/locales/en.py` — required to prevent a `KeyError` on every result in this mode (contracts/cli-repl-turning-combined-constraints-delta.md; research.md #8)
- [X] T018 [US1] Extend `power_and_rpm_rows()` in `src/mfgparams/console/tui/screens/split_pane.py` with a new defaulted keyword parameter `rotation_and_feed_constrained: bool = False`, dispatching to `[rpm_row(), feed_rate_row(), power_row("tui.label.power", False)]` when true — reusing the existing `rpm_row`/`feed_rate_row`/`power_row` factory parameters unchanged (contracts/cli-repl-turning-combined-constraints-delta.md)
- [X] T019 [US1] In `src/mfgparams/console/tui/screens/turning.py`: add a `CalculationMode.ROTATION_AND_FEED_CONSTRAINED: "tui.mode.rotation_and_feed_constrained"` entry to `_MODE_OPTION_KEYS`, and pass `rotation_and_feed_constrained=state.mode is CalculationMode.ROTATION_AND_FEED_CONSTRAINED` through to `power_and_rpm_rows()` in `rows_for()` (depends on T016, T018)

**Checkpoint**: `ROTATION_AND_FEED_CONSTRAINED` is fully functional and independently testable end-to-end (library + console), per spec.md User Story 1.

---

## Phase 4: User Story 2 - Run Turning Within a Fixed Power Budget at a Fixed Feed (Priority: P2)

**Goal**: A machinist who knows their available power and required feed per rotation gets a feasible spindle speed and the resulting machining time/cutting force/power, solved within that budget at that exact feed (spec.md User Story 2).

**Independent Test**: Call `calculate_turning(mode=CalculationMode.POWER_AND_FEED_CONSTRAINED, available_power=..., target_feed_rate=...)` directly and via the console's new mode option; verify `power_required` is at or within the supplied budget, `feed_per_rotation` equals the supplied value exactly, and `spindle_speed_rpm` is the highest value feasible at that budget/feed (quickstart.md Scenarios 3-4).

### Tests for User Story 2 ⚠️

- [X] T020 [P] [US2] Unit tests for the new `calculate_turning_power_and_feed_constrained_metrics()` (nominal-sufficient-budget no-op case, exact-equality boundary via `math.isclose(rel_tol=1e-9)`, reduced-spindle-speed case, zero budget, negative budget (added by a Copilot review finding on PR #102 that caught this description promising negative-budget coverage the original test file never shipped), subnormal feed underflow, arbitrary-precision-int budget) in new `tests/unit/processes/machining/turning/test_formulas_power_and_feed_constrained.py`, mirroring `test_formulas_at_rpm.py`'s existing `POWER_CONSTRAINED` test coverage
- [X] T021 [P] [US2] Contract test for the power-and-feed-constrained success response shape (`feed_per_rotation` equals the supplied value exactly, `power_required` within budget, spindle speed reduced only when the nominal exceeds the budget) per contracts/library-api-turning-combined-constraints-delta.md in `tests/contract/test_library_api_turning_power_and_feed_constrained.py`
- [X] T022 [P] [US2] Contract test confirming this mode never emits the advisory `feasibility_warning` (the budget is a hard constraint already satisfied by construction, research.md #6) in `tests/contract/test_library_api_turning_power_and_feed_constrained.py`
- [X] T023 [P] [US2] Contract test for `MODE_CONFLICT` (missing `available_power`, or a `target_rpm` supplied under this mode), `INFEASIBLE_POWER_BUDGET` (zero/negative/non-finite budget), `INVALID_TARGET_FEED_RATE` (missing/zero/negative/non-numeric feed), `MISSING_MATERIAL`/`MISSING_TOOL` precedence, and the mixed-invalid case where `target_feed_rate` is missing/invalid **and** `available_power` is simultaneously missing — asserting `MODE_CONFLICT` wins, since the shared `validate_mode_arguments()` call (available_power's own check) runs before `target_feed_rate`'s own-value check (data-model.md's precedence rule; mirrors T010's analogous case for `ROTATION_AND_FEED_CONSTRAINED`, and the exact precedence bug PR #101's review found for `020`) — in `tests/contract/test_library_api_turning_power_and_feed_constrained_errors.py`
- [X] T024 [P] [US2] Contract test asserting `INFEASIBLE_POWER_BUDGET` (not `CALCULATION_OVERFLOW` -- this mode solves for spindle speed within a power budget, exactly like `POWER_CONSTRAINED`, so it reuses that mode's own error code for an invalid extreme-input result; corrected by a Copilot review finding on PR #102 that caught the original draft accepting either code) for an extreme-input request in `tests/contract/test_library_api_turning_power_and_feed_constrained_errors.py`, mirroring `020`'s existing extreme-input test
- [X] T025 [P] [US2] Integration test for the TUI's power-and-feed-constrained mode: the mode row offers the new option; selecting it shows the required Feed rate per rotation and Available power rows (no spindle-speed row); the resulting `CalculationResult` matches a direct `calculate_turning(mode=CalculationMode.POWER_AND_FEED_CONSTRAINED, ...)` call field-by-field (FR-009's identical-results guarantee — same pattern as T012); the result panel renders without error and shows the "adjusted to fit available power" spindle-speed label, in `tests/integration/test_tui_turning.py`

### Implementation for User Story 2

- [X] T026 [US2] Add `calculate_turning_power_and_feed_constrained_metrics(diameter_mm, depth_of_cut_mm, length_of_cut_mm, material, tool, available_power_kw, target_feed_per_rev_mm) -> TurningMetrics` to `src/mfgparams/processes/machining/turning/formulas.py`: derive the nominal spindle speed via the existing `_derive_standard_spindle_speed_rpm()`, compute the nominal metrics at that speed with `feed_per_rev_mm=target_feed_per_rev_mm`, return it as-is if its power already fits the budget (`math.isclose(rel_tol=1e-9)` boundary treated as sufficient, mirroring `calculate_turning_power_constrained_metrics()`), otherwise scale the spindle speed down linearly and recompute (research.md #3; depends on T002)
- [X] T027 [US2] In `validation.py`'s `validate_mode_arguments()`, extend the existing `if mode is CalculationMode.POWER_CONSTRAINED:` branch's condition to `if mode is CalculationMode.POWER_CONSTRAINED or mode is CalculationMode.POWER_AND_FEED_CONSTRAINED:` — identical treatment (`target_rpm` supplied is `MODE_CONFLICT`, missing `available_power` is `MODE_CONFLICT`, invalid is `INFEASIBLE_POWER_BUDGET`); update the docstring with a `POWER_AND_FEED_CONSTRAINED` paragraph (research.md #4; depends on T002)
- [X] T028 [US2] In `turning/__init__.py`'s `_compute_metrics()`, add an `if mode is CalculationMode.POWER_AND_FEED_CONSTRAINED:` branch: the existing `available_power_kw <= 0` → `INFEASIBLE_POWER_BUDGET` guard (mirroring `POWER_CONSTRAINED`'s), then T026's formula function, then `_reject_if_invalid(..., error_code="INFEASIBLE_POWER_BUDGET", ...)` (depends on T026, T027)
- [X] T029 [US2] In `turning/__init__.py`'s `_build_result()`, extend the feasibility-warning exclusion condition from `mode is not CalculationMode.POWER_CONSTRAINED` to also exclude `POWER_AND_FEED_CONSTRAINED` (research.md #6; depends on T002)
- [X] T030 [P] [US2] Add `tui.mode.power_and_feed_constrained` (`"power-and-feed-constrained"`) catalog key to `src/mfgparams/console/locales/en.py`
- [X] T031 [P] [US2] Add a `CalculationMode.POWER_AND_FEED_CONSTRAINED` entry to `_SPINDLE_SPEED_MODE_LABEL_KEYS` (`"tui.result.spindle_speed.mode.power_and_feed_constrained"`) in `src/mfgparams/console/tui/forms.py`, and add that catalog key reusing `POWER_CONSTRAINED`'s existing value (`"adjusted to fit available power"`) in `src/mfgparams/console/locales/en.py` — required to prevent a `KeyError` on every result in this mode (contracts/cli-repl-turning-combined-constraints-delta.md; research.md #8)
- [X] T032 [US2] Extend `power_and_rpm_rows()` in `src/mfgparams/console/tui/screens/split_pane.py` with a new defaulted keyword parameter `power_and_feed_constrained: bool = False`, dispatching to `[feed_rate_row(), power_row("tui.label.power_required", True)]` when true
- [X] T033 [US2] In `src/mfgparams/console/tui/screens/turning.py`: add a `CalculationMode.POWER_AND_FEED_CONSTRAINED: "tui.mode.power_and_feed_constrained"` entry to `_MODE_OPTION_KEYS`, and pass `power_and_feed_constrained=state.mode is CalculationMode.POWER_AND_FEED_CONSTRAINED` through to `power_and_rpm_rows()` in `rows_for()` (depends on T030, T032)

**Checkpoint**: `POWER_AND_FEED_CONSTRAINED` is fully functional and independently testable end-to-end (library + console), per spec.md User Story 2. Both new turning modes now work independently of each other.

---

## Phase 5: User Story 3 - Machining Menu Steps Out of the Way During an Operation (Priority: P2)

**Goal**: Opening any operation (turning, drilling, or milling) hides the Machining menu; exiting the operation restores it, in the same state, symmetrically for all three (spec.md User Story 3). Fully independent of US1/US2 — touches only `app.py`.

**Independent Test**: Open the Machining menu, select each of turning, drilling, and milling in turn; verify the Machining menu is not visible while the operation's screen is open; exit and verify it reappears (quickstart.md Scenario 6).

### Tests for User Story 3 ⚠️

- [X] T034 [P] [US3] Extend `tests/integration/test_tui_navigation.py`'s existing `test_escaping_the_operation_pane_closes_it_and_reveals_the_tree_underneath` with a new assertion, immediately after opening Milling and before the first escape, that `body_mode is None` while `open_operation is not None` (contracts/tui-machining-menu-auto-hide-delta.md's example) — this snapshot index is not currently asserted by that test, so no existing assertion changes
- [X] T035 [P] [US3] Add new integration tests in `tests/integration/test_tui_navigation.py` confirming the identical hide-on-open/restore-on-exit behavior for Drilling and for Turning (FR-013's symmetry), mirroring T034's shape

### Implementation for User Story 3

- [X] T036 [US3] In `src/mfgparams/console/tui/app.py`'s `_activate_tree_row()`, add `view.body_mode = None` immediately after the branch that opens an operation (`_open_milling`/`_open_drilling`/`_open_turning`) — the single shared call site for all three (research.md #9). No other change: the existing restore-on-exit logic in `_escape_bar`/`_escape_body` (`view.body_mode = "tree" if ui.tree.expanded else None`) already does what FR-012 needs, unmodified.

**Checkpoint**: The Machining menu hides/restores correctly and symmetrically for all three operations. All three user stories are now independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, versioning, and final validation across all three stories.

- [X] T037 [P] Update `docs/source/turning.rst` (end-user docs) and `docs/source/turning-api.rst` (API reference) to document both new modes, mirroring how `020` documented `FEED_RATE_CONSTRAINED` (Constitution VII)
- [X] T038 [P] Add a `CHANGELOG.md` bullet under `## [Unreleased]` → `### Added` documenting the two new turning calculation modes and the Machining-menu auto-hide fix, and bump `src/mfgparams/__init__.py`'s `__version__` from `2.3.0` to `2.4.0` (Constitution Principle IV: additive, non-breaking API surface → MINOR version)
- [X] T039 Regression test: run the full existing `019`/`020` turning test suite unmodified and confirm 100% pass with no assertion changed, proving neither new mode nor the Machining-menu fix changes any existing mode's or operation's behavior (spec.md Assumptions)
- [X] T040 Run `pytest --cov=mfgparams --cov-report=term-missing` (unfiltered — the full suite, including drilling's and milling's existing tests) and confirm ≥90% coverage is maintained on calculation modules including the new `formulas.py`/`validation.py`/`turning/__init__.py`/`drilling/__init__.py`/`milling/_calculate.py`/`app.py` code paths (Constitution II); address any gaps
- [X] T041 [P] Static check confirming no literal user-facing strings were introduced in `turning.py`'s/`forms.py`'s new mode-option/field-label/result-line code paths outside the message catalog (Constitution VIII; `tests/static/test_no_hardcoded_strings.py`)
- [X] T042 Run the full quality-gate suite (`mypy`, `ruff`, `radon`/`xenon` complexity, `bandit`, `pip-audit`) per Constitution Principle IX and confirm no new findings introduced by this feature's changes — in particular, confirm `_compute_metrics()`'s and `_validate_mode_inputs()`'s cyclomatic complexity (each gaining two more `if` branches) stays within the configured `max-complexity` threshold (plan.md Constitution Check)
- [X] T043 Execute all 6 quickstart.md scenarios and confirm actual behavior matches documented expected outcomes
- [ ] T044 **REQUIRED (Constitution Principle XIII)** Manually verify, against a real terminal, both new modes' field rows (Target spindle speed + Feed rate per rotation + optional Available power for `ROTATION_AND_FEED_CONSTRAINED`; Feed rate per rotation + required Available power for `POWER_AND_FEED_CONSTRAINED`) and the Machining menu's hide-on-select/restore-on-exit behavior for all three operations — layout, focus highlighting, and visibility are not directly asserted by the headless integration tests above. If the implementing agent has no access to a real terminal, leave this task unchecked and say so rather than marking it complete on the agent's behalf.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all three user stories.
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion.
  - US1 (Phase 3) and US2 (Phase 4) touch overlapping shared files (`validation.py`, `turning/__init__.py`) at different, non-overlapping `if` branches — safe to implement in either order, or in parallel by different developers, but not truly file-parallel within those two files.
  - US3 (Phase 5) touches only `app.py` and `test_tui_navigation.py` — fully independent of US1/US2, safe to implement in parallel with either or both.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Depends only on Foundational (Phase 2). No dependency on US2 or US3.
- **User Story 2 (P2)**: Depends only on Foundational (Phase 2). No dependency on US1 or US3.
- **User Story 3 (P2)**: Depends on nothing but Setup — does not even require Foundational (Phase 2), since it touches no turning/drilling/milling file at all. Listed after US1/US2 only because spec.md's own story numbering places it third.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Principle II).
- Validation extensions before dispatch-branch wiring (a dispatch branch that trusts an unvalidated `target_rpm`/`target_feed_rate`/`available_power` would violate the existing "guaranteed non-None" assertions the codebase already relies on).
- Library-layer implementation before TUI wiring (the TUI calls the library; nothing in `split_pane.py`/`turning.py` can be meaningfully tested against a mode that doesn't calculate correctly yet).
- Story complete before moving to the next priority (though, per the Phase Dependencies note above, US1/US2/US3 may also proceed in parallel across developers).

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (there is only one).
- T002, T005, T006 (Foundational, different files) can run in parallel; T003, T004 both depend on T002 and touch the same file (sequential); T007 depends on T005, T006.
- T008-T012 (US1 tests, different files/independent assertions within one file) can run in parallel with each other, and with T020-T025 (US2 tests) and T034-T035 (US3 tests) once Foundational completes.
- T016, T017 (US1 implementation, different catalog entries) can run in parallel with each other; T018 is independent of both; T019 depends on T016 and T018.
- T030, T031 (US2 implementation, different catalog entries) can run in parallel with each other; T032 is independent of both; T033 depends on T030 and T032.
- T037, T038, T041 (Polish) can run in parallel; T039, T040, T042, T043, T044 are sequential validation gates run after implementation is complete.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent Foundational tasks together:
Task: "Add ROTATION_AND_FEED_CONSTRAINED and POWER_AND_FEED_CONSTRAINED to CalculationMode in models.py"
Task: "Extend drilling's UNSUPPORTED_MODE guard to reject both new modes"
Task: "Extend milling's UNSUPPORTED_MODE guard to reject both new modes"
```

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 contract/integration tests together (after Foundational lands):
Task: "Contract test for rotation-and-feed-constrained success shape"
Task: "Contract test for rotation-and-feed-constrained advisory available_power"
Task: "Contract test for rotation-and-feed-constrained error codes"
Task: "Contract test for rotation-and-feed-constrained extreme-input overflow"
Task: "Integration test for the TUI's rotation-and-feed-constrained mode"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks US1 and US2; US3 doesn't need it)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md Scenarios 1-2 and confirm SC-001/SC-003
5. Deploy/demo if ready — the more commonly requested of the two new modes (spec.md User Story 1's own priority rationale: it needs no additional power input)

### Incremental Delivery

1. Complete Setup + Foundational → both new `CalculationMode` members exist, `target_feed_rate` accepted under either, drilling/milling reject both
2. Add User Story 1 (rotation-and-feed-constrained) → test independently → deploy/demo (MVP!)
3. Add User Story 2 (power-and-feed-constrained) → test independently → deploy/demo
4. Add User Story 3 (Machining menu auto-hide) → test independently → deploy/demo (can also be done first or in parallel — it has no dependency on US1/US2)
5. Polish (docs, changelog/version, coverage, quickstart validation, manual TUI verification, quality gates) → final release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3 (can start immediately after Setup, even before Foundational, since it has no dependency on it)
3. All three stories integrate independently — no cross-story merge conflicts expected beyond the shared Foundational edits already landed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
