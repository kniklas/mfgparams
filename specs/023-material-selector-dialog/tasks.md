---

description: "Task list template for feature implementation"
---

# Tasks: Multi-Notation Metal Material Selector Dialog

**Input**: Design documents from `specs/023-material-selector-dialog/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/materials-config-schema-delta.md, contracts/dialog-interaction-contract.md, quickstart.md

**Tests**: Included as mandatory tasks (not optional) — mirrors this repo's own recent precedent (e.g. `021-turning-combined-constraints`'s tasks.md) of treating tests as mandatory even outside the calculation modules Constitution Principle II names explicitly, and this feature's own plan.md Testing section already commits to specific test files.

**Organization**: Tasks are grouped by user story (US1 = search/select by common name, P1; US2 = search by EN material number + column switching, P2; US3 = search by shortened designation, P3) per spec.md priorities, on top of a Foundational phase that builds the dialog's full open/navigate/confirm/cancel plumbing against the *unfiltered* candidate list. Each story then adds one column's worth of search behavior to the shared `candidates()` filter — mirroring `021`'s own pattern of extending one shared function once per story rather than duplicating it. The data model change (`WorkpieceMaterial`'s two new optional fields) is Foundational since all three columns' data must exist before any of them can be searched.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow the existing single-project `src/mfgparams/` + `tests/` layout (no changes to plan.md's Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new tooling/dependencies are introduced by this feature (plan.md Technical Context); this phase only confirms the existing tooling covers the new code paths.

- [X] T001 Confirm `pytest`, `ruff`, `mypy`, `radon`/`xenon`, `bandit` configuration in `pyproject.toml` already covers new/modified modules under `src/mfgparams/registry.py`, `src/mfgparams/console/tui/material_picker.py`, and `src/mfgparams/console/tui/app.py` with no config changes needed (no new dependency added per plan.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two new `WorkpieceMaterial` fields, the `material_picker.py` module's state/skeleton, and the `app.py` wiring that opens, navigates (Up/Down), confirms (Enter), and cancels (Escape) the dialog against the full, unfiltered metal-material list. No column is searchable yet — that is each user story's own increment.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `material_number: str | None = None` and `short_notation: str | None = None` fields to `WorkpieceMaterial` in `src/mfgparams/registry.py`, with `Attributes:` docstring entries mirroring the existing `translations` entry's shape (data-model.md "Extended entity")
- [X] T003 In `src/mfgparams/registry.py`'s `_to_material()`, extract `entry.fields.get("material_number")`/`entry.fields.get("short_notation")`, validate each against `_FORBIDDEN_NAME_CATEGORIES` (warn-and-continue: record a validation issue and fall back to `None` on violation, mirroring `_parse_material_type`'s existing pattern — never `RegistryConfigError`), and pass both into the `WorkpieceMaterial(...)` constructor call (contracts/materials-config-schema-delta.md rule 8; depends on T002)
- [X] T004 In `src/mfgparams/registry.py`, add `"material_number"` and `"short_notation"` to `_STICKY_FIELDS` alongside the existing `"material_type"` (research.md Decision 5, contracts/materials-config-schema-delta.md rule 10; depends on T002)
- [X] T005 [P] Unit tests for T002-T004: valid values round-trip onto `WorkpieceMaterial`; a non-string or control-character value is dropped with a recorded validation issue rather than raising; a user override entry that omits both keys carries over the bundled entry's values (sticky-field merge) — in `tests/unit/shared/test_registry_material_notations.py`, mirroring the existing `tests/unit/shared/test_registry_material_types.py` (depends on T002, T003, T004)
- [X] T006 [P] Create `src/mfgparams/console/tui/material_picker.py` with the `MaterialPickerState` dataclass (`query_common: str = ""`, `query_number: str = ""`, `query_short: str = ""`, `active_column: Literal["common", "number", "short"] = "common"`, `highlighted_name: str | None = None`) per data-model.md "New entity"; module docstring notes it implements spec.md's "Material Selection Window" entity, so the spec's business-language name stays traceable into the code
- [X] T007 In `material_picker.py`, implement `open_state(current_material_name: str | None, materials: list[WorkpieceMaterial]) -> MaterialPickerState`: empty queries, `active_column="common"`, `highlighted_name` set to `current_material_name` only if it matches a `name` in `materials`, else `None` (FR-011, Clarification 2; depends on T006)
- [X] T008 In `material_picker.py`, implement `move_highlight(state: MaterialPickerState, candidates: list[WorkpieceMaterial], delta: int) -> None`: moves `highlighted_name` to the previous/next entry in `candidates` (no wraparound; a `None`/absent-from-list highlight or an empty `candidates` leaves `highlighted_name` at the first entry or `None` respectively) (FR-005; depends on T006)
- [X] T009 In `material_picker.py`, implement `render(state: MaterialPickerState, candidates: list[WorkpieceMaterial], locale: str, display_locale: str) -> StyleAndTextTuples`: three-column table (common name via `display_name(display_locale)`, material number, shortened designation), translated column headers, a blank cell for a missing `material_number`/`short_notation` (FR-002, FR-010), the highlighted row shown in reverse video (matching `split_pane.render_left_pane`'s existing row-highlight convention), and a translated empty-state line when `candidates` is empty (FR-013; depends on T006)
- [X] T010 [P] Add `tui.material_picker.title`, `tui.material_picker.column_common`, `tui.material_picker.column_number`, `tui.material_picker.column_short`, and `tui.material_picker.empty` keys to `src/mfgparams/console/locales/en.py` (FR-013; used by T009)
- [X] T011 [P] Unit tests for `open_state()`/`move_highlight()`: previously-selected material present/absent from the list, single-candidate list, empty-candidate list, moving past either end — in `tests/unit/console/tui/test_material_picker.py` (depends on T007, T008)
- [X] T012 In `src/mfgparams/console/tui/app.py`'s `_ViewState`, add `material_picker: MaterialPickerState | None = None`, with a docstring note mirroring `confirming_exit`'s (research.md Decision 1)
- [X] T013 In `app.py`'s `build_app()`, add `material_picker_control = FormattedTextControl(lambda: material_picker.render(...), focusable=True, show_cursor=False)` and a centered `Float` (`Box(body=Shadow(Frame(...)), style="class:dialog")`, matching `operation_window`'s existing centering pattern) wrapped in a `ConditionalContainer(filter=Condition(lambda: view.material_picker is not None))`, appended to the root `FloatContainer`'s `floats=[...]` list after the operation-window `Float`. Until T021 (User Story 1) introduces `candidates()`, this and every other Foundational call site below (T016, T018, T019) MUST pass the full, unfiltered metal-material list directly as `render()`'s/`move_highlight()`'s `candidates` argument — no query can be edited yet (T022, User Story 1), so the unfiltered list and "the current candidate list" are identical during this phase (depends on T009, T012)
- [X] T014 In `app.py`, add a `pane_material_picker_trigger` Condition (`_pane_is_focused()` and `isinstance(_current_pane_row(), split_pane.RadioRow)` and the current row's `field_id is FieldId.MATERIAL` and `ui.open_operation.session_state.material_type == "metal"`) (research.md Decision 3; depends on T012). **Post-implementation correction (2026-09-23, direct user feedback)**: this task originally also narrowed `pane_radio_focused` to exclude the metal Material row, disabling its Left/Right/Space cycle in favor of Enter-only. That narrowing was reverted — `pane_radio_focused` is left unmodified, so Left/Right/Space keep cycling the row exactly as before, with `pane_material_picker_trigger`/Enter as an additive second path, not a replacement. See research.md Decision 3's updated text and spec.md's Session 2026-09-23 Clarifications entry.
- [X] T015 In `app.py`, bind `enter` under `pane_material_picker_trigger` to build the current operation's metal-material list (`list_materials(materials_config_path, material_type="metal")` + `get_material(...)`, mirroring `drilling.py`'s existing Material-row option-building), call `material_picker.open_state(session_state.material, materials)`, assign it to `view.material_picker`, and focus `material_picker_control` (FR-001; depends on T007, T013, T014)
- [X] T016 In `app.py`, add a `material_picker_focused` Condition (`view.material_picker is not None and app.layout.has_focus(material_picker_control)`) and bind `up`/`down` under it to `move_highlight()` against the full unfiltered metal-material list (T013's note — `candidates()` does not exist yet in this phase) (FR-005; depends on T008, T015)
- [X] T017 In `app.py`, bind `escape` under `material_picker_focused` to clear `view.material_picker` and focus `left_control`, and extend `_escape_body`'s filter from `not on_bar() and not view.confirming_exit` to also require `view.material_picker is None` (research.md Decision 4, FR-009; depends on T015)
- [X] T018 In `app.py`, bind `enter` under `material_picker_focused` to: if `state.highlighted_name is not None`, set `session_state.material = state.highlighted_name`, clear `view.material_picker`, and focus `left_control` (FR-007); otherwise no-op, leaving the dialog open (FR-008; depends on T015)
- [X] T019 [P] Integration tests for the Foundational plumbing (against the full unfiltered metal-material list, per T013's note): Enter on the metal Material row opens the dialog with the previously-selected material highlighted and all three columns visible (blank cells rendered correctly for a material missing a notation); Up/Down move the highlight; Escape closes without changing `session_state.material`; Enter with a highlight confirms and closes; Enter with no highlight (an already-empty starting list, e.g. no metal materials configured) is a no-op. Parametrize (or duplicate) the open/confirm case across all three operations (drilling, turning, milling) — the first automated regression coverage for FR-012/SC-004's "identical across operations" claim, which otherwise relies on manual verification alone (T041, T042) — in `tests/integration/test_tui_material_picker.py` (depends on T013-T018)

**Checkpoint**: The dialog opens (pre-highlighting the current selection), shows all three columns, navigates, confirms, and cancels correctly against the unfiltered list. No column is searchable yet.

---

## Phase 3: User Story 1 - Find a metal material by its common name in a dedicated picker (Priority: P1) 🎯 MVP

**Goal**: Typing into the (so far, only reachable) common-name column narrows the candidate list; Up/Down/Enter/Escape behave exactly as in the Foundational phase, now against the filtered list (spec.md User Story 1).

**Independent Test**: Open the metal Material picker, type a partial common name, confirm the list narrows to case-insensitive substring matches, move the highlight, and confirm Enter/Escape behave as described — delivers a working, searchable replacement for today's material selection on its own (spec.md User Story 1 "Independent Test").

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T020 [P] [US1] Unit tests for `candidates()` filtering on `query_common` only: empty query returns the full list unfiltered; a substring match (case-insensitive) narrows correctly; no match returns an empty list — in `tests/unit/console/tui/test_material_picker.py`

### Implementation for User Story 1

- [X] T021 [US1] In `material_picker.py`, implement `candidates(state: MaterialPickerState, materials: list[WorkpieceMaterial], display_locale: str) -> list[WorkpieceMaterial]`, filtering on `query_common` (case-insensitive substring against `display_name(display_locale)`, Clarification 1) — the query fields for the other two columns exist on `state` but are not yet consulted here (US2/US3 extend this same function) (FR-004; depends on T006, T020)
- [X] T022 [US1] In `app.py`, bind a printable-character handler and `backspace` under `material_picker_focused` to append to / remove from `state.query_common` (the only column reachable until US2 adds column-switching) and re-derive the candidate list via `candidates()`. This is also the task that switches T013's/T016's/T018's/T019's list source: `render()`'s and `move_highlight()`'s `candidates` argument, and the Enter-confirm check, now come from `candidates(state, materials, display_locale)` instead of the raw unfiltered `materials` list T013 specified for the Foundational phase (FR-003, FR-004; depends on T021)
- [X] T023 [US1] In `app.py`, after each query edit from T022, re-derive `state.highlighted_name` against the freshly-filtered candidate list (the first candidate, or `None` if the list is now empty) — data-model.md's "Edit query" transition (depends on T022)
- [X] T024 [P] [US1] Integration test: type a partial common name and confirm the list narrows live as each character is typed/removed; confirm Up/Down and Enter operate on the filtered list, not the full one — in `tests/integration/test_tui_material_picker.py` (depends on T022, T023)

**Checkpoint**: User Story 1 is fully functional and independently testable — searching and selecting a metal material by common name works end-to-end.

---

## Phase 4: User Story 2 - Find a metal material by its EN material number (Priority: P2)

**Goal**: Column-switching becomes possible (Left/Right/Tab/Shift+Tab), and the material-number column becomes searchable, combining (AND) with any common-name filter already typed (spec.md User Story 2).

**Independent Test**: Open the picker, switch column focus to the material-number column, type a partial number, and confirm the list narrows to materials whose material number contains that text — independent of User Story 3's shortened-designation column (spec.md User Story 2 "Independent Test").

### Tests for User Story 2 ⚠️

- [X] T025 [P] [US2] Unit tests for `candidates()` also filtering on `query_number`: a substring match narrows correctly; a material with no `material_number` is excluded the moment `query_number` is non-empty (FR-010); combined with a non-empty `query_common`, only materials matching both remain — in `tests/unit/console/tui/test_material_picker.py`
- [X] T026 [P] [US2] Unit tests for `cycle_column()`: cycles `"common" → "number" → "short" → "common"` moving right, and the reverse moving left, from any starting column — in `tests/unit/console/tui/test_material_picker.py`

### Implementation for User Story 2

- [X] T027 [US2] In `material_picker.py`, extend `candidates()` (T021) to also require a `query_number` substring match against `material_number` when `query_number` is non-empty, excluding materials with a `None`/blank `material_number` in that case (FR-004, FR-010; depends on T021, T025)
- [X] T028 [US2] In `material_picker.py`, implement `cycle_column(state: MaterialPickerState, delta: int) -> None`, wrapping among `"common"`/`"number"`/`"short"` (research.md Decision 7; depends on T006, T026)
- [X] T029 [US2] In `app.py`, bind `left`/`s-tab` and `right`/`tab` under `material_picker_focused` to `cycle_column()` (FR-006; depends on T028, T016)
- [X] T030 [US2] In `app.py`, generalize T022's character/backspace bindings to edit whichever of `query_common`/`query_number`/`query_short` matches `state.active_column`, instead of always `query_common` (depends on T029, T022)
- [X] T031 [P] [US2] Integration test: switch column focus to material-number (Right or Tab), type a partial number, confirm the list narrows and a material with no recorded number drops out; confirm Left/Shift+Tab returns focus to the common-name column and its previously-typed text is preserved — in `tests/integration/test_tui_material_picker.py` (depends on T029, T030)

**Checkpoint**: User Stories 1 and 2 both work independently — searching by common name or by EN material number, and switching between them, all function correctly.

---

## Phase 5: User Story 3 - Find a metal material by its shortened designation (Priority: P3)

**Goal**: The shortened-designation column becomes searchable, completing all three identification methods and the three-way combined (AND) filter (spec.md User Story 3).

**Independent Test**: Open the picker, switch column focus to the shortened-designation column, type a partial designation, and confirm the list narrows accordingly — delivers standalone value on top of User Stories 1 and 2 (spec.md User Story 3 "Independent Test").

### Tests for User Story 3 ⚠️

- [X] T032 [P] [US3] Unit tests for `candidates()` also filtering on `query_short`: a substring match narrows correctly; a material with no `short_notation` is excluded when `query_short` is non-empty (FR-010); all three queries non-empty simultaneously returns only materials matching all three (spec.md User Story 3 Acceptance Scenario 2) — in `tests/unit/console/tui/test_material_picker.py`

### Implementation for User Story 3

- [X] T033 [US3] In `material_picker.py`, extend `candidates()` (T027) to also require a `query_short` substring match against `short_notation` when `query_short` is non-empty, excluding materials with a `None`/blank `short_notation` in that case (FR-004, FR-010; depends on T027, T032)
- [X] T034 [P] [US3] Integration test: switch column focus to the shortened-designation column (cycling already works from US2), type a partial designation, confirm the list narrows; type into all three columns simultaneously and confirm only materials matching all three remain — in `tests/integration/test_tui_material_picker.py` (depends on T033)

**Checkpoint**: All three user stories are independently functional. The dialog now fully matches contracts/dialog-interaction-contract.md.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Data population, documentation, versioning, and final validation across all three stories.

- [X] T035 [P] Evaluate `material_number`/`short_notation` population for each of the 6 bundled metal materials in `src/mfgparams/data/materials.toml` against a known EN/DIN designation (plan.md Project Structure; contracts/materials-config-schema-delta.md) — a data-entry task, not an interaction-behavior change. **Outcome (PR #106 review, rounds 1-2)**: none qualify. Every bundled name (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium) is a generic material family, not a single grade unambiguous enough across standards traditions (e.g. EN 10025-2's S235JR vs. ASTM's A36 for "mild steel") to stamp a specific EN/DIN number onto — both fields stay `None` on every bundled entry, per `materials.toml`'s own top-of-file comment and T049's test coverage. This is a final decision for the *generic-family* entries specifically: a future convergence pass MUST NOT reintroduce population on Mild Steel/Stainless Steel/Aluminum/Cast Iron/Brass/Titanium. **Superseded in part by T052**: real manual testing found leaving *every* bundled metal blank made the feature have nothing real to search out of the box, so a 7th, grade-specific bundled entry was added there instead.
- [X] T036 [P] Update `docs/source/index.rst` and `docs/source/drilling.rst` (the existing docs source referencing the materials-config schema) to mention the two new optional TOML keys, `material_number` and `short_notation` (Constitution VII)
- [X] T037 [P] Add a `CHANGELOG.md` bullet under `## [Unreleased]` → `### Added` documenting the new material selector dialog and the two new optional materials-config keys, and bump `src/mfgparams/__init__.py`'s `__version__` from `2.4.0` to `2.5.0` (Constitution IV: additive, non-breaking schema/TUI change → MINOR version)
- [X] T038 [P] Static check confirming no hard-coded user-facing strings were introduced in `material_picker.py`'s/`app.py`'s new code paths outside the message catalog (Constitution VIII; `tests/static/test_no_hardcoded_strings.py`)
- [X] T039 Run `pytest --cov=mfgparams --cov-report=term-missing` and confirm ≥90% coverage is maintained on the new `material_picker.py` and modified `registry.py`/`app.py` code paths (Constitution II)
- [X] T040 Run the full quality-gate suite (`mypy`, `ruff`, `radon`/`xenon` complexity, `bandit`, `pip-audit`) and confirm no new findings; in particular confirm `app.py`'s key-binding block's cyclomatic complexity stays within the configured threshold after the ~9 new bindings/Conditions added across Phases 2-5 (Constitution IX; plan.md Constitution Check)
- [ ] T041 Execute all 5 quickstart.md scenarios on a real terminal and confirm actual behavior matches documented expected outcomes — traced (not executed on a real terminal) via a direct Python simulation against `material_picker.py`'s real functions during a `/speckit-converge` pass, which caught and fixed two scenario-script bugs (see quickstart.md's Scenario 1/3 correction history), but per Constitution Principle XIII that trace does not substitute for the real-terminal pass this task requires; leave unchecked alongside T042 until one is performed
- [X] T043 **Post-implementation addition (2026-09-23, direct user feedback)** Restore Left/Right/Space cycling on the metal Material row (revert T014's original narrowing of `pane_radio_focused` — see that task's correction note) so it stays available alongside Enter's dialog, and add FR-014's hint: `split_pane.py::render_bottom_bar` shows a new `tui.material_picker.pane_hint` catalog key ("↑↓ move   ←→/Space change   ↵ detailed search   Esc back") in place of the generic `tui.pane.hint` whenever the metal Material row is selected and the dialog is closed (research.md Decision 9). Covered by a new regression test (`test_left_right_space_still_cycle_the_metal_material_row_directly` in `tests/integration/test_tui_material_picker.py`) and spec.md's Session 2026-09-23 Clarifications entry/FR-001/FR-014
- [ ] T042 **REQUIRED (Constitution Principle XIII)** Manually verify the material selector dialog against a real terminal, at exactly 80x25 (the 022-tui-min-size-25x80 floor) and at a larger size, for drilling, turning, and milling, per quickstart.md's 5 scenarios — column alignment, highlight visibility, Shadow/Frame border fit within the floor, and focus transfer in/out of the dialog are not directly asserted by the headless integration tests above. If the implementing agent has no access to a real terminal, leave this task unchecked and say so rather than marking it complete on the agent's behalf.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all three user stories.
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion, AND on each other in this specific case: US2 (Phase 4) extends the same `candidates()` function US1 (Phase 3) introduces, and US3 (Phase 5) extends the version US2 leaves behind — each story's `candidates()` edit must land after the previous story's, so **US1 → US2 → US3 is a real, not merely priority-ordered, dependency chain** for the `material_picker.py` implementation tasks specifically (T021 → T027 → T033). Each story's *test* tasks and its `app.py` key-binding tasks are otherwise independent of the others' non-`candidates()` work.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Depends only on Foundational (Phase 2).
- **User Story 2 (P2)**: Depends on Foundational (Phase 2) AND on User Story 1's `candidates()` (T021), since T027 extends it in place rather than duplicating it.
- **User Story 3 (P3)**: Depends on Foundational (Phase 2) AND on User Story 2's `candidates()` (T027), for the same reason.

### Within Each User Story

- Tests MUST be written and FAIL before implementation.
- `material_picker.py` logic before `app.py` key-binding wiring that calls it.
- Story complete before moving to the next priority (US1 → US2 → US3, per the real `candidates()` dependency chain above — these three stories cannot be parallelized across developers the way `021`'s US1/US2/US3 could).

### Parallel Opportunities

- T002 (Foundational, `registry.py` dataclass fields) has no dependency and can start immediately; T003, T004 both depend on it and touch the same file (sequential, not parallel with each other).
- T006 (Foundational, new file `material_picker.py`) can run in parallel with T002-T005 (different files).
- T010 (locale keys) can run in parallel with T006-T009 (different file).
- T005, T011 (Foundational tests, different files) can run in parallel with each other once their respective implementation tasks land.
- T012-T018 (Foundational `app.py` wiring) are sequential — each binds against state/Conditions the previous task introduces, all in the same file.
- T020 (US1 test) can be written in parallel with Foundational Phase 2 work, since it only needs `MaterialPickerState`'s shape (T006), not the full dialog.
- T025, T026 (US2 tests, same file but independent assertions) can run in parallel with each other.
- T032 (US3 test) has no parallel sibling within its own story.
- T035-T038 (Polish) can run in parallel; T039-T042 are sequential validation gates run after implementation is complete.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent Foundational tasks together:
Task: "Add material_number/short_notation fields to WorkpieceMaterial in registry.py"
Task: "Create material_picker.py with the MaterialPickerState dataclass"
Task: "Add tui.material_picker.* message keys to locales/en.py"
```

## Parallel Example: User Story 2 Tests

```bash
# Launch both US2 unit test tasks together (after User Story 1 lands):
Task: "Unit tests for candidates() filtering on query_number, including FR-010 blank-cell exclusion"
Task: "Unit tests for cycle_column() wrapping in both directions"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories; delivers open/navigate/confirm/
   cancel against the unfiltered list)
3. Complete Phase 3: User Story 1 (common-name search)
4. **STOP and VALIDATE**: Run quickstart.md Scenario 1 manually; confirm User Story 1's
   Independent Test passes
5. Deploy/demo if ready — this alone already adds a searchable dialog alongside today's
   Left/Right-cycle interaction, which remains available unchanged

### Incremental Delivery

1. Complete Setup + Foundational → dialog plumbing ready, nothing searchable yet
2. Add User Story 1 → common-name search works → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → column-switching + material-number search work → Test independently →
   Deploy/Demo
4. Add User Story 3 → shortened-designation search completes the three-column contract → Test
   independently → Deploy/Demo
5. Each story adds value without breaking the previous stories' behavior

### Sequential-Only Note

Unlike a typical multi-story feature, US1/US2/US3 here cannot be split across developers to
work in parallel (see Dependencies & Execution Order above) — `candidates()` is one function
that each story extends in place, by design (Constitution I: no duplicated filter logic across
three near-identical column checks). A single implementer (or pair) should carry Phases 3-5 in
order.

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

---

## Phase 7: Convergence

**Purpose**: Gaps found by `/speckit-converge` between spec.md/plan.md/tasks.md and the current code, after the Session 2026-09-23 "restore Left/Right cycling + FR-014 hint" amendment. None of these block the feature's core behavior — each is a coverage or documentation gap, not a functional defect.

- [X] T044 Add a test asserting FR-014's pane-hint behavior in `split_pane.py::render_bottom_bar`: the metal Material row (selected, dialog closed) shows the `tui.material_picker.pane_hint` catalog text; a non-metal material type, a different selected field, or a set `screen.status` all still show the pre-existing generic `tui.pane.hint`/status text per FR-014 (missing)
- [X] T045 Add an automated integration test in `tests/integration/test_tui_material_picker.py` opening the metal Material selection dialog from Milling (not just Drilling/Turning), using Milling's own row order (`screens/milling.py::rows_for` inserts `FieldId.SUB_OPERATION` between `MODE` and `MATERIAL_TYPE`, unlike Drilling/Turning) — the last of the three operations FR-012/SC-004 requires identical behavior across that currently has no automated regression coverage per FR-012, SC-004 (missing)
- [X] T046 Correct plan.md's Project Structure entry for `material_picker.py` (the line naming `edit_active_query()`/`backspace_active_query()`): the implementation performs query editing inline in `app.py`'s `_material_picker_char`/`_material_picker_backspace` handlers via a `_MATERIAL_PICKER_QUERY_ATTR` lookup, not as separate functions in `material_picker.py` per plan: Project Structure (partial)

---

## Phase 8: Convergence

**Purpose**: Gaps found by a second `/speckit-converge` pass, after Phase 7's tasks landed. All three are documentation/coverage gaps, not functional defects — the dialog's actual interactive behavior is unaffected.

- [X] T047 Document the metal Material selection window on `docs/source/turning.rst` and `docs/source/milling.rst` (mirroring the "Selecting a metal material" section `drilling.rst` already has from T036, whose scope was narrower than the feature's actual reach): both pages currently have zero mention of it, even though FR-012/SC-004 requires identical behavior from all three operations per FR-012, SC-004, Constitution VII (missing)
- [X] T048 Add a step to `quickstart.md` (Scenario 1 or a new scenario) verifying that Left/Right/Space still cycle the metal Material row directly before Enter is pressed, and that the `tui.material_picker.pane_hint` bottom-bar text renders correctly (visible, not clipped or overlapping) on a real terminal — the Session 2026-09-23 "restore Left/Right cycling + FR-014 hint" amendment added both behaviors after quickstart.md was written, and T042 (the only gate that can verify rendering correctness) currently has no script coverage for either per Constitution XIII, plan.md Summary (missing)
- [X] T049 Add a unit test in `tests/unit/shared/test_registry_material_notations.py` asserting the real bundled registry (`get_material(name)`, no config override) reports `None` for both `material_number`/`short_notation` on every bundled metal — mirroring `test_registry_material_types.py`'s `TestBundledCategorization` precedent, which tests real bundled values directly rather than only synthetic `tmp_path` configs per T035 (missing). **Updated during PR #106 review round 2**: T035 initially populated Mild Steel/Stainless Steel/Brass; Brass's values were removed in round 1 for the same generic-family ambiguity, then Mild Steel/Stainless Steel's were removed in round 2 after the identical objection was raised against them too — every bundled entry is now blank, consistently, per `data/materials.toml`'s own comment.

---

## Phase 9: Convergence

**Purpose**: One gap found by a third `/speckit-converge` pass, in the content T048 itself added — a documentation-only defect in the manual-verification script, not a functional regression.

- [X] T050 Fix `quickstart.md` Scenario 1 steps 5–6 (added by T048): step 5 claims pressing Right, Right, Left cycles the metal Material row through "Mild Steel → Stainless Steel → Aluminum → back to Stainless Steel", but tracing `split_pane.nudge_selected`'s actual wraparound logic for those three presses from unset gives Mild Steel → Stainless Steel → **Mild Steel** (Aluminum is never reached, and the final state is Mild Steel, not Stainless Steel); step 6's claim that the dialog opens with "Stainless Steel" pre-highlighted must be corrected to "Mild Steel" to match — the two subsequent steps (typing "steel" then Down then Enter) already reach the same final "Stainless Steel" outcome regardless, since typing a query re-highlights to the first match, so nothing past step 6 needs to change per Constitution XIII, quickstart.md Scenario 1 (contradicts)

---

## Phase 10: Convergence

**Purpose**: One gap found by a fourth `/speckit-converge` pass, in a column-navigation parenthetical quickstart.md has carried since the original `/speckit-plan` draft — a documentation-only defect, not a functional regression.

- [X] T051 Fix `quickstart.md` Scenario 3 step 1's parenthetical: it says the shortened-designation column is reachable via "Left/Shift+Tab once from material number," but executing `material_picker.cycle_column()` directly shows one Left from `"number"` lands on `"common"`, not `"short"` — the correct one-press alternative is Left/Shift+Tab **from `"common"`** (`cycle_column` wraps backward directly to `"short"` from there), which is also the column reopening the dialog always starts on (`open_state()` always resets `active_column` to `"common"`), so "from material number" was never the step's actual starting state to begin with per Constitution XIII, quickstart.md Scenario 3 (contradicts)

## Phase 11: Post-review usability fix

**Purpose**: A real defect found by the user's own manual testing after PR #106's review loop closed: with every bundled metal's `material_number`/`short_notation` blanked out (T035's final outcome, above), the picker had nothing real to search at all without a user-supplied `--materials-config` — the review loop's iterative caution over-corrected past the point of leaving the feature usable out of the box.

- [X] T052 Add a 7th bundled metal, `S235JR Structural Steel`, to `src/mfgparams/data/materials.toml` with `material_number = "1.0038"`/`short_notation = "S235JR"` populated — its own name states the specific grade, so (unlike the generic-family entries T035 left blank) there is no ambiguity to misrepresent. Reuses "Mild Steel"'s existing machining constants (25.0/0.20/1900.0), since S235JR is itself a mild/structural steel in that same class. Updated: `materials.toml`'s top-of-file comment; `_EXPECTED_BUNDLED_MATERIALS`/expected-name-order assertions in `test_registry.py`/`test_registry_config.py`; `_METALS` in `test_registry_material_types.py`; `TestBundledNotations` in `test_registry_material_notations.py` (split into generic-blank vs. grade-specific-populated cases); `quickstart.md`'s fixture (no longer needs to redeclare this entry itself) and its dependent candidate counts; `README.md`'s metal-materials list (missing)
