---
description: "Task list for the Turning Calculations Module feature"
---

# Tasks: Turning Calculations Module

**Input**: Design documents from `/specs/019-turning-calculations/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included as mandatory, not optional — Constitution Principle II
("Testing Standards (NON-NEGOTIABLE)") requires unit tests for every calculation
function and integration tests for every multi-step pipeline; this feature's tasks
follow that requirement exactly as drilling's and milling's original task sets did.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent
implementation and testing of each story, per Constitution Principle VI.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task names its exact file path

---

## Phase 1: Setup

**Purpose**: Create the new package skeleton and bundled reference data — no behavior yet.

- [X] T001 Create the `turning` package skeleton: `src/mfgparams/processes/machining/turning/__init__.py` (empty for now), `src/mfgparams/processes/machining/turning/data/__init__.py`, mirroring `drilling/`'s directory shape exactly (plan.md Project Structure).
- [X] T002 [P] Author `src/mfgparams/processes/machining/turning/data/tools.toml` with the bundled HSS/Cobalt/Carbide turning-tool reference factors, per [contracts/turning-tools-config-schema.md](./contracts/turning-tools-config-schema.md) "Bundled defaults" and research.md #5. (No separate task is needed to "register" the `turning_tools` table key anywhere central — verified against `src/mfgparams/registry_config.py`, `drilling/tools.py`, and `milling/end_milling/tools.py`: each operation's own `tools.py` module passes its own `table_key` string directly to the existing generic `build_registry(...)`/`load_registry_entries(...)` helpers. T015 below is where turning's own `tools.py` does this.)

**Checkpoint**: `turning/` package exists with bundled tool data loadable via the existing config-loading machinery; nothing calls it yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared model/infrastructure changes every user story's code depends on. No user story's tasks may start before this phase is done.

- [X] T003 Add `TURNING = "turning"` to the `MachiningOperation` enum in `src/mfgparams/models.py`, updating its docstring's member list (data-model.md; research.md #6).
- [X] T004 Add the optional `cutting_force: float | None = None` field to `CalculationResult` in `src/mfgparams/models.py`, documented following the exact precedent `material_removal_rate` already sets (populated for turning, `None` for drilling/milling) — data-model.md "CalculationResult (response, extended)".
- [X] T005 Add three new `Configuration` fields in `src/mfgparams/config.py` (dataclass defaults, docstring entries, and external-file override parsing, mirroring exactly how `max_mill_diameter_mm` was added alongside drilling's `max_diameter_mm`): `max_turning_diameter_mm: float = 500.0`, `max_turning_depth_of_cut_mm: float = 10.0`, `max_turning_length_of_cut_mm: float = 1000.0` (data-model.md "Configuration").
- [X] T006 Add `validate_turning_diameter_mm(diameter_mm, config, locale)` to `src/mfgparams/validation.py`, mirroring `validate_mill_diameter_mm`'s exact shape: reuses the `INVALID_DIAMETER` code, checks `config.max_turning_diameter_mm` (T005), with its own `error.invalid_turning_diameter.zero`/`.max` messages.
- [X] T007 Add `validate_turning_length_of_cut_mm(length_of_cut_mm, config, locale)` to `src/mfgparams/validation.py`, mirroring `validate_length_of_cut_mm`'s shape but checking `config.max_turning_length_of_cut_mm` (T005) instead of the shared `max_length_of_cut_mm`: reuses the existing `INVALID_LENGTH_OF_CUT` code (already defined for milling's `length_of_cut`) — zero new error codes.
- [X] T008 Add `validate_turning_depth_of_cut_mm(depth_of_cut_mm, diameter_mm, config, locale)` to `src/mfgparams/validation.py`: checks positive/finite, then `<= config.max_turning_depth_of_cut_mm` (T005), then strictly `< diameter_mm / 2` (the workpiece radius) — all three checks returning the existing `INVALID_DEPTH_OF_CUT` code (data-model.md "ErrorInfo — no new error codes") with three distinct `message_key`s: `error.invalid_turning_depth_of_cut.zero`, `.max`, `.exceeds_radius`.
- [X] T009 [P] Add new English message-catalog entries to `src/mfgparams/locales/en.py`: `error.invalid_turning_diameter.zero`/`.max` (T006), `error.invalid_turning_depth_of_cut.zero`/`.max`/`.exceeds_radius` (T008) — no new entries are needed for length of cut (T007 reuses milling's existing `error.invalid_length_of_cut.zero`/`.max` messages verbatim, since only the bound value differs, not the wording).
- [X] T010 [P] Add new English message-catalog entries to `src/mfgparams/console/locales/en.py`: `tui.machining_menu.turning` ("Turning"), `tui.label.turning_tool` ("Turning tool"), `tui.label.workpiece_diameter` ("Workpiece diameter"), `tui.label.depth_of_cut` ("Depth of cut"), `tui.result.cutting_force` ("Cutting force:      {value} {unit}"), per [contracts/cli-repl-turning.md](./contracts/cli-repl-turning.md). (`tui.label.length_of_cut` is reused verbatim from milling — no new entry.)
- [X] T011 [P] Add `"depth_of_cut"` and `"cutting_force"` entries to both unit-system dicts in `forms.UNIT_LABELS` (`src/mfgparams/console/tui/forms.py`): `{"depth_of_cut": "mm"/"in", "cutting_force": "N"/"lbf"}`.

**Checkpoint**: Shared models, validation, config, and message-catalog groundwork exist. User story implementation can now begin.

---

## Phase 3: User Story 1 — Calculate Core Turning Parameters Interactively (Priority: P1) 🎯 MVP

**Goal**: A user can select Turning in the console text GUI, enter workpiece diameter, depth of cut, length of cut, material, and turning tool, and see spindle speed, feed rate, machining time, cutting force, and power — standard mode only.

**Independent Test**: Launch the console, open the Turning screen, fill every required field with valid values, and confirm the result panel shows all five calculated quantities matching known reference values (quickstart.md Scenario 1 inputs, displayed via the TUI per Scenario 5).

### Tests for User Story 1

- [X] T012 [P] [US1] Unit tests for turning input validation in `tests/unit/test_validation_turning.py`: nominal, zero/negative/non-numeric diameter/depth-of-cut/length-of-cut, exceeds-configured-max for each, and depth-of-cut >= radius (T006, T007, T008).
- [X] T013 [P] [US1] Contract test for standard-mode `calculate_turning()` in `tests/contract/test_library_api_turning.py`: nominal calculation against a hand-computed/published reference value (SC-002's 5% tolerance, independently for each of spindle speed/feed rate/cutting force/power), a missing-material/tool case, an unsupported material/tool combination case, and the depth-of-cut-exceeds-radius rejection — asserting the library never raises (FR-016/contracts/library-api-turning.md).
- [X] T014 [P] [US1] Integration test for the console Turning screen in `tests/integration/test_tui_turning.py`, mirroring `tests/integration/test_tui_milling.py`'s shape: selecting Turning from the Machining tree opens its floating window; filling all required fields produces a result panel showing all five quantities; an invalid field shows the corresponding structured error inline instead of a result (quickstart.md Scenario 5).

### Implementation for User Story 1

- [X] T015 [US1] Implement `TurningTool` dataclass and `get_tool()`/loader in `src/mfgparams/processes/machining/turning/tools.py`, mirroring `drilling/tools.py`'s shape exactly (data-model.md "TurningTool").
- [X] T016 [US1] Implement `TurningMetrics` and `calculate_turning_metrics()` (standard mode only, for now) in `src/mfgparams/processes/machining/turning/formulas.py`, per research.md #1: spindle speed, feed rate, machining time (no point-engagement allowance — research.md #2), cutting force (`Fc = Kc * ap * fn`), torque (`Mc = Fc * (D/2) / 1000`), power (`Pc = Mc * n / 9550`) — citing the Sandvik Coromant / Machinery's Handbook source in a module docstring comment exactly as `drilling/formulas.py` does (Constitution Principle III).
- [X] T017 [US1] Implement `calculate_turning()` orchestration in `src/mfgparams/processes/machining/turning/__init__.py` — standard-mode path only for this story: validate diameter/depth-of-cut/length-of-cut/material/tool (turning's own `validate_turning_diameter_mm`/`validate_turning_depth_of_cut_mm`/`validate_turning_length_of_cut_mm` from T006-T008, plus reused `validate_material_present`/`validate_tool_present`), resolve material/tool, call `calculate_turning_metrics()`, convert to `CalculationResult` (populating the new `cutting_force` field, T004), apply imperial conversion at this layer (FR-017) — mirroring `drilling/__init__.py`'s shape exactly, never raising for expected validation failures.
- [X] T018 [US1] Add `TURNING`-branch wiring: `TreeRow("tui.machining_menu.turning", "open_turning", indent=0)` in `src/mfgparams/console/tui/machining_menu.py`'s `tree_rows()`, and `RowAction`'s `Literal` extended to include `"open_turning"` (contracts/cli-repl-turning.md).
- [X] T019 [US1] Implement `_open_turning()` in `src/mfgparams/console/tui/app.py`, mirroring `_open_drilling`/`_open_milling` exactly, and wire the new `"open_turning"` action into the tree's selection-handling `if`/`elif` chain (contracts/cli-repl-turning.md "App dispatch").
- [X] T020 [US1] Implement `TurningSessionState` and `rows_for()`/`calculate_result()` in `src/mfgparams/console/tui/screens/turning.py`, mirroring `screens/drilling.py`'s shape exactly, per contracts/cli-repl-turning.md's field order (unit system, mode, material type/material, turning tool, workpiece diameter, depth of cut, length of cut, mode-conditional power/RPM row) — standard mode fully working for this story; the mode `RadioRow` and mode-conditional rows may be included now (T027 in US3 fills in their calculation-time behavior) since `split_pane.power_and_rpm_rows()` and the `RadioRow` widget are pre-existing, generic components.
- [X] T021 [US1] Extend the result panel's rendering (wherever `tui.result.*` lines are assembled — likely alongside `screens/drilling.py` or a shared result-rendering helper in `forms.py`) to include the new Cutting force line (`tui.result.cutting_force`, T010) for any operation whose `CalculationResult.cutting_force` is not `None`.
- [X] T022 [US1] Add `depth_of_cut`/`length_of_cut` unit-conversion-on-switch handling in `screens/turning.py`'s `_convert_on_unit_change` equivalent, mirroring `screens/drilling.py`'s existing `diameter`/`depth` conversion (Copilot PR #94 precedent).

**Checkpoint**: Turning is fully usable end-to-end in standard mode via the console. US1 is independently testable and demoable.

---

## Phase 4: User Story 2 — Embed Turning Calculations in Another Application (Priority: P1)

**Goal**: `calculate_turning()` and `list_turning_tools()` are usable directly as a library, re-exported at the top level, with identical results to the console for identical inputs.

**Independent Test**: Call `calculate_turning(...)` directly with the quickstart.md Scenario 1 inputs with no console involved, and confirm the returned `CalculationResult` matches the console's displayed values field-by-field (quickstart.md Scenario 6).

### Tests for User Story 2

- [X] T023 [P] [US2] Contract test asserting the top-level re-export surface in `tests/contract/test_library_api_turning.py` (extends T013): `from mfgparams import calculate_turning, list_turning_tools` succeeds and both are callable without importing any `processes.machining.turning` submodule directly.
- [X] T024 [P] [US2] Integration test for identical-results parity in `tests/integration/test_turning_console_library_parity.py` (or extend an existing parity test file if one already covers drilling/milling this way): identical inputs through `calculate_turning()` directly and through `screens.turning.calculate_result()` (US1) produce identical `CalculationResult` values.

### Implementation for User Story 2

- [X] T025 [US2] Implement `list_turning_tools(config_path=None)` in `src/mfgparams/processes/machining/turning/tools.py` (alongside T015), mirroring `drilling/tools.py`'s `list_tools()`.
- [X] T026 [US2] Re-export `calculate_turning` and `list_turning_tools` at the top level in `src/mfgparams/__init__.py`, alongside the existing `calculate`/`calculate_end_milling`/`calculate_face_milling`/`list_tools` re-exports, and update this module's own docstring (which already names "a future process (turning, ...)" — mfgparams/__init__.py module docstring) to describe turning as now present rather than future.

**Checkpoint**: Turning is fully usable as a standalone library, independent of the console, with parity confirmed against US1.

---

## Phase 5: User Story 3 — Choose a Turning Calculation Mode (Priority: P2)

**Goal**: `calculate_turning()` supports `FIXED_RPM` and `POWER_CONSTRAINED` modes in addition to `STANDARD`, with the console's mode selector fully wired for turning.

**Independent Test**: Call `calculate_turning(..., mode=CalculationMode.FIXED_RPM, target_rpm=900)` and confirm the returned spindle speed is exactly 900; call it with `mode=CalculationMode.POWER_CONSTRAINED, available_power=<a value below the standard-mode requirement>` and confirm the returned spindle speed is reduced to fit (quickstart.md Scenarios 2-3), all independent of any console interaction.

### Tests for User Story 3

- [X] T027 [P] [US3] Contract tests for fixed-RPM mode in `tests/contract/test_library_api_turning_fixed_rpm.py` and its error cases in `tests/contract/test_library_api_turning_fixed_rpm_errors.py` (invalid/missing `target_rpm`, `MODE_CONFLICT` when combined with `available_power` as a hard constraint incorrectly), mirroring `tests/contract/test_library_api_milling_fixed_rpm*.py`'s shape.
- [X] T028 [P] [US3] Contract tests for power-constrained mode in `tests/contract/test_library_api_turning_power_constrained.py` and its error cases in `tests/contract/test_library_api_turning_power_constrained_errors.py` (missing `available_power`, infeasible budget → `INFEASIBLE_POWER_BUDGET`), mirroring `tests/contract/test_library_api_milling_power_constrained*.py`'s shape.
- [X] T029 [P] [US3] Integration test for the feasibility boundary in `tests/integration/test_turning_fixed_rpm_feasibility.py`, mirroring `tests/integration/test_milling_fixed_rpm_feasibility.py`: a fixed-RPM request whose resulting power exceeds a supplied `available_power` produces a `feasibility_warning`, not an error.

### Implementation for User Story 3

- [X] T030 [US3] Implement `calculate_turning_metrics_at_rpm()` in `src/mfgparams/processes/machining/turning/formulas.py` (extends T016), mirroring `calculate_drilling_metrics_at_rpm()` exactly — cutting force and torque independent of spindle speed (research.md #1), so `calculate_turning_metrics()` (standard mode) becomes a thin wrapper deriving nominal RPM and delegating here.
- [X] T031 [US3] Implement `calculate_turning_power_constrained_metrics()` in `src/mfgparams/processes/machining/turning/formulas.py`, mirroring `calculate_power_constrained_metrics()`'s closed-form `n_adjusted = n0 * (Pavail / Pc0)` solve exactly (research.md #1) — no new iterative logic.
- [X] T032 [US3] Extend `calculate_turning()` in `src/mfgparams/processes/machining/turning/__init__.py` (extends T017) with `mode`/`target_rpm` dispatch and `validate_mode_arguments`/`validate_target_rpm` reuse, mirroring `drilling/__init__.py`'s mode-dispatch branch exactly.
- [X] T033 [US3] Confirm `screens/turning.py`'s mode `RadioRow` and `split_pane.power_and_rpm_rows()` wiring (already added in T020) correctly drive `calculate_result()`'s `mode`/`target_rpm`/`available_power` arguments for all three modes; add any missing mode-changed-clears-stale-value guard (mirroring `screens/drilling.py`'s `_set_mode`) if not already covered by T020.

**Checkpoint**: All three calculation modes work for turning, via both the library and the console, matching drilling's/milling's mode parity exactly.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, `tui-design` sign-off, and end-to-end validation across all three stories.

- [X] T034 [P] Add `docs/source/turning.rst` (end-user docs) and `docs/source/turning-api.rst` (API reference), mirroring `docs/source/milling.rst`/`milling-api.rst`, and link them into the Sphinx toctree (Constitution Principle VII).
- [X] T035 [P] Update `src/mfgparams/__init__.py`'s module docstring's process list (if not already done by T026) to mention turning alongside drilling and milling.
- [X] T036 Run `/speckit-analyze` against this feature's `spec.md`/`plan.md`/`tasks.md` before implementation starts, and again after all tasks above are complete, per this repo's own established practice on prior features.
- [X] T037 Run every quickstart.md scenario (1 through 6) manually end-to-end as a final sanity check, beyond what the automated tests already cover.
- [X] T038 Confirm the `tui-design` skill's design-review note (contracts/cli-repl-turning.md "Design-review note") still holds once `screens/turning.py` is actually implemented — i.e., no new color/layout was invented beyond the existing `NumberRow`/`RadioRow`/result-line style classes; if any new visual element was introduced during implementation that isn't covered by that note, run the `tui-design` skill properly before merging.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: No hard dependency on Phase 1's files (Phase 2 only touches `models.py`/`config.py`/`validation.py`/the locale catalogs), but do Phase 1 first for a clean incremental history. BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2. No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Phase 2 and on T015-T017 (US1's `tools.py`/`formulas.py`/`__init__.py` implementation) existing to re-export — in practice, implement US1 and US2 together despite the story split, since T025/T026 are thin additions on top of US1's own files; they are split into a separate story here only because they are independently *testable* (SC-005/SC-006), not because they require separate implementation effort.
- **User Story 3 (Phase 5)**: Depends on Phase 2 and on US1's `calculate_turning_metrics()`/`calculate_turning()` (T016, T017) existing to extend.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### Parallel Opportunities

- T001, T002 (Setup) can run in parallel.
- T003, T004 (Foundational) can run in parallel with each other and with T005. T006, T007, and T008 (the three new `validate_turning_*` functions) each depend on T005 (their `Configuration` bound fields existing) but not on each other, so they can run in parallel once T005 lands. T009, T010, T011 can run in parallel with everything else in this phase.
- All three stories' *test* tasks (T012-T014, T023-T024, T027-T029) can be written in parallel with each other, and in parallel with their own story's implementation tasks being scaffolded (per Constitution Principle II, they should be written first and confirmed failing before the corresponding implementation task lands).
- T034, T035 (Polish) can run in parallel with each other and with T036-T038.

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1) — standard-mode turning, fully working end-to-end via the console.
3. **STOP and VALIDATE**: run quickstart.md Scenarios 1, 4, 5 and confirm SC-001/SC-002/SC-003/SC-004.
4. This is a legitimate, shippable MVP slice on its own (a working standard-mode turning calculator) — note, per the "Implementation notes" section below, that all three stories were in fact delivered together in a single PR rather than staged as separate merges.

### Incremental Delivery

1. Setup + Foundational → Foundation ready.
2. Add User Story 1 → validate independently (MVP).
3. Add User Story 2 → validate independently (library parity).
4. Add User Story 3 → validate independently (mode parity).
5. Polish → docs, `/speckit-analyze`, final quickstart run, `tui-design` sign-off confirmation.

**Superseded by actual delivery** (updated post-implementation, per a Copilot review
finding on PR #100): this section originally planned two pull requests (spec-only, then a
separate implementation PR) per Constitution Principle XII's condition in plan.md's
Constitution Check. In practice the feature was delivered as a **single** PR (`#100`)
containing the spec, plan, tasks, and the complete implementation together — see plan.md's
Constitution Check (Principle XII) for the corrected record. This PR was not merged to
`main` until Phase 6 above was fully complete, consistent with the spirit of the original
constraint even though the two-PR split itself never materialized.

## Implementation notes (post-completion)

All 38 tasks above are complete; the full test suite (1301 tests) and every quality gate
(ruff, black, mypy, radon MI, bandit) pass. A few small deviations from the literal task
text, discovered while implementing, are recorded here so the task list and the actual
code don't silently drift apart:

- **T024** landed in the existing `tests/integration/test_tui_calculation_parity.py`
  (drilling's/milling's own parity test file), not a new
  `test_turning_console_library_parity.py` — the task text itself flagged this as the
  preferred option once such a file was confirmed to exist.
- **A few small additions tasks.md didn't call out individually**, all following
  established per-operation precedents: `validate_turning_tool_present` (mirroring
  `validate_mill_tool_present` — drilling's `validate_tool_present` message says
  "drilling tool" specifically, which would have been wrong for turning);
  `n_to_lbf`/`lbf_to_n` in `units.py` (needed once `cutting_force` gained an imperial
  unit); a `turning_tools` section and `tui.configuration.section.turning_tools` catalog
  key in the Configuration screen (closing the same completeness gap PR #94's review
  found for milling, proactively rather than waiting for a review round); and a
  `CHANGELOG.md` entry plus a `__version__` bump to `2.2.0` (Constitution Principle IV:
  additive, non-breaking API surface → MINOR version).
- **Design-review note (T038) confirmed**: no new color/layout was introduced in
  `screens/turning.py` beyond the existing `NumberRow`/`RadioRow`/result-line style
  classes already used by `screens/drilling.py` — the `tui-design` skill's checklist
  does not need a separate run for this feature.
