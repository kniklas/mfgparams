# Tasks: TUI Minimum Terminal Size 25x80

**Input**: Design documents from `specs/022-tui-min-size-25x80/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/console-tui-terminal-size-contract.md, quickstart.md

**Tests**: Included as mandatory tasks (not optional) — the two existing boundary test files assert the *old* 80x30 floor and would misdescribe actual behavior once `MIN_LINES` changes, the exact class of drift Constitution Principle XIII's second bullet and this project's own history (018's retrospective) warn against; leaving them stale is not an option, per plan.md's Constitution Check (Principle II row).

**Organization**: Tasks are grouped by user story (US1 = launch and use every screen at 80x25, P1; US2 = still reject below 80x25, P2) per spec.md priorities, on top of a shared Foundational phase (the one-line floor edit and its two boundary-test-file updates, which both stories' independent tests depend on directly).

**A note on task nature**: most of this feature's substantive work is manual verification, not code an agent can write and run itself — Constitution Principle XIII (NON-NEGOTIABLE) applies because correctness here means "does this render without clipping in a real 80x25 terminal," which this project's state/text-only TUI test strategy cannot observe (research.md #3). Tasks below marked "requires a real terminal" MUST be performed by a developer or reviewer; if the implementing agent has no such access, leave that task unchecked and say so rather than marking it complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Paths follow the existing single-project `src/mfgparams/` + `tests/` layout (no changes to plan.md's Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new tooling/dependencies are introduced by this feature (plan.md Technical Context); this phase only confirms a clean starting point.

- [X] T001 Run `pytest tests/unit/console/tui/test_terminal_capability.py tests/integration/test_tui_terminal_too_small.py -v` and confirm both files pass against the current (pre-change) 80x30 floor, establishing a known-good baseline before any edits

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one-line floor edit both user stories' independent tests depend on directly, plus updating the two existing test files whose boundary assertions are tied to the old floor value.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Change `MIN_LINES = 30` to `MIN_LINES = 25` in `src/mfgparams/console/tui/terminal_capability.py`; update the module comment immediately above it (currently explains the 017→018 raise from 25 to 30) to instead explain this feature lowers it back to 25, citing `research.md #1` and noting `MIN_COLUMNS` is unaffected (FR-001/FR-002)
- [X] T003 [P] In `tests/unit/console/tui/test_terminal_capability.py`: change `test_not_supported_when_too_few_lines` from asserting `(80, 29)` is rejected to asserting `(80, 24)` is rejected, replacing its docstring's now-inapplicable "25→30, so use 29 not 24" reasoning with the new boundary's rationale; update `test_not_supported_when_too_few_columns`'s `(79, 30)` fixture to `(79, 25)` and its "lines held at exactly the floor" comment to say 25, not 30 (research.md #2; depends on T002)
- [X] T004 [P] In `tests/integration/test_tui_terminal_too_small.py`: update the module docstring's "below 30x80"/FR-008/FR-011/FR-013/Scenario-9 references to this feature's own FR-002/quickstart.md; change `test_main_exits_1_when_terminal_is_too_narrow`'s `(79, 30)` fixture to `(79, 25)` and its assertion of `"30"` in the error output to `"25"`; change `test_main_exits_1_when_terminal_is_too_short`'s `(80, 29)` fixture to `(80, 24)` and simplify its docstring (no longer need to disambiguate from an even-older floor); change `test_main_succeeds_at_exactly_the_minimum_size`'s `(80, 30)` fixture to `(80, 25)` and update its docstring's "30x80 is the minimum" to "25x80" (research.md #2; depends on T002)

**Checkpoint**: `MIN_LINES` is 25; both boundary test files pass against the new floor. User story phases below build on this.

---

## Phase 3: User Story 1 - Launch the text GUI on a classic 25x80 terminal (Priority: P1) 🎯 MVP

**Goal**: A user on a terminal reporting exactly 80x25 can launch the text GUI and reach every screen on the main menu without being rejected, and without any screen's content clipping or overlapping (spec.md User Story 1, FR-005/FR-006).

**Independent Test**: Launch `mfgparams` in a terminal reporting exactly 80x25 and confirm the application starts and every menu-reachable screen (Drilling, Milling, Turning, Configuration, About, Help) is visible and keyboard-operable (quickstart.md Part 1).

### Implementation for User Story 1

- [X] T005 [P] [US1] **Requires a real terminal.** Resize to exactly 80x25 (quickstart.md Part 1, step 1) and open the Drilling screen (Machining → Drilling); confirm every field, label, and the bottom status row are fully visible with no cut-off row and every field is keyboard-reachable. If not, compact `src/mfgparams/console/tui/screens/drilling.py`'s rendering (smallest change that closes the gap, per research.md #5) and re-verify (FR-005/FR-006)
- [X] T006 [P] [US1] **Requires a real terminal.** Same check as T005 for the Milling screen (Machining → Milling), in `src/mfgparams/console/tui/screens/milling.py` — the field-densest operation screen and highest a-priori risk (research.md #4: 14 fields, 16-17 rows measured pre-018-margin-removal)
- [X] T007 [P] [US1] **Requires a real terminal.** Same check as T005 for the Turning screen (Machining → Turning), in `src/mfgparams/console/tui/screens/turning.py` — never previously measured against a real terminal (research.md #4)
- [X] T008 [P] [US1] **Requires a real terminal.** Open Configuration (menu bar → Configuration), About, and Help; confirm each opens without crashing and, for Configuration specifically, that content taller than 25 lines remains reachable via the existing Up/Down scroll bindings rather than being silently cut off (research.md #3). **Correction, found by manual testing**: Help specifically was NOT just a content/scroll question as research.md #3 predicted — at 80 columns its dropdown (the rightmost bar entry) overflowed the screen edge and rendered squeezed to near-illegible, a horizontal-fit bug research.md's row-only analysis missed entirely. Fixed in `src/mfgparams/console/tui/app.py` (`_dropdown_float`'s new `right_aligned` option, applied to Help's call site) by anchoring Help's dropdown to the screen's right edge instead of its own left offset. Re-verified against the fix, and Configuration/About confirmed open/scroll correctly, on a real terminal.

**Checkpoint**: All six menu-reachable screens confirmed usable at 80x25 (compacted where needed). User Story 1 is fully functional and independently demoable.

---

## Phase 4: User Story 2 - Still reject terminals smaller than 25x80 (Priority: P2)

**Goal**: A terminal narrower than 80 columns or shorter than 25 lines continues to be rejected with a clear, accurate message before any UI renders (spec.md User Story 2, FR-002/FR-004).

**Independent Test**: Launch `mfgparams` in a terminal reporting 79x25, and separately in one reporting 80x24; confirm both are rejected with a message stating a minimum of 80x25 (quickstart.md Part 2).

### Implementation for User Story 2

- [X] T009 [US2] **Requires a real terminal.** Resize to 79x25, then separately to 80x24 (quickstart.md Part 2); run `mfgparams` at each size and confirm rejection with a message stating minimum 80x25 (not 80x30) before any prompt-toolkit UI appears — a human sanity-check of what T004's automated assertions already cover (FR-002/FR-004)

**Checkpoint**: Both stories independently verified. The feature's core behavior (accept 80x25, reject below it, every screen usable) is complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final sign-off spanning both user stories.

- [X] T010 [P] Add a `### Changed` bullet to `CHANGELOG.md`'s `[Unreleased]` section noting the minimum supported terminal size is lowered from 30x80 back to 25x80 (specs/022-tui-min-size-25x80), mirroring the existing 018 entry's style at `CHANGELOG.md:114-115`
- [X] T011 Run the full automated suite (`pytest`), lint (`ruff`), and type-check (`mypy`) to confirm no regression from the T002 constant edit and any T005-T007 compaction changes
- [X] T012 **REQUIRED (Constitution Principle XIII)** Manually walk `quickstart.md` end-to-end (Part 1 and Part 2) on a real terminal set to exactly 80x25, confirming every menu-reachable screen and both floor-rejection boundaries — not satisfied by automated tests alone. Completed by the user (developer) on a real terminal, per confirmation in-session, including re-verification of the Help dropdown fix.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories.
- **User Stories (Phase 3-4)**: Both depend on Foundational phase completion.
  - US1 and US2 can proceed in parallel (if staffed) or sequentially in priority order (P1 → P2).
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependency on US2.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — no dependency on US1; both exercise the same T002 edit from independent angles.

### Within Each Phase

- T003/T004 (Foundational) both depend on T002, but not on each other — different files.
- T005-T008 (US1) depend only on Phase 2's checkpoint — different files, no dependency on each other.
- T009 (US2) depends only on Phase 2's checkpoint.
- T012 (Polish) depends on T005-T009 all being complete (it re-walks the same ground as a consolidated sign-off).

### Parallel Opportunities

- T003 and T004 (Foundational tests) can run in parallel once T002 is done.
- T005, T006, T007, T008 (US1's four screen checks) can all run in parallel — different files, no shared state.
- T010 (CHANGELOG) can run in parallel with T011 (test/lint/type-check run) and with the US1/US2 manual-verification tasks — it depends on nothing but the feature's scope being settled, which it already is by Phase 2.

---

## Parallel Example: User Story 1

```bash
# Launch all four screen checks for User Story 1 together (different files, no shared state):
Task: "Requires a real terminal. Verify Drilling screen at 80x25, compact if needed, in src/mfgparams/console/tui/screens/drilling.py"
Task: "Requires a real terminal. Verify Milling screen at 80x25, compact if needed, in src/mfgparams/console/tui/screens/milling.py"
Task: "Requires a real terminal. Verify Turning screen at 80x25, compact if needed, in src/mfgparams/console/tui/screens/turning.py"
Task: "Requires a real terminal. Verify Configuration/About/Help open and scroll correctly at 80x25"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001).
2. Complete Phase 2: Foundational (T002-T004) — CRITICAL, blocks both stories.
3. Complete Phase 3: User Story 1 (T005-T008).
4. **STOP and VALIDATE**: the app launches and every screen is usable at 80x25 — this alone is the entire user-visible point of the feature (spec.md: "without [User Story 1], the feature delivers nothing").
5. User Story 2 (T009) and Polish (T010-T012) close out the remaining acceptance criteria and the required sign-off.

### Incremental Delivery

1. Setup + Foundational → floor is 25x80, both boundary test files green.
2. Add User Story 1 → every screen confirmed usable at 80x25 (MVP demoable).
3. Add User Story 2 → rejection-below-floor behavior confirmed unchanged in substance, updated in value.
4. Polish → CHANGELOG entry, full-suite confirmation, and the required Principle XIII sign-off.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- This feature has no automatable "implementation" beyond T002 (the constant) and whatever compaction T005-T007 turn up — the rest of its substance is the manual-verification pass itself, not code around it.
- Commit after each task or logical group (e.g., T002-T004 as one commit, each of T005-T008 as its own commit if it produces a code change, T010-T012 as a final commit).
- Stop at the Phase 3 checkpoint to validate User Story 1 independently before proceeding.
