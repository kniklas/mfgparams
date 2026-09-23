---

description: "Task list for 025-imperial-geometry-nudge-step"
---

# Tasks: Imperial Arrow-Key Nudge Step for Geometry Fields

**Input**: Design documents from `specs/025-imperial-geometry-nudge-step/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Two user stories (US1 P1, US2 P2) per spec.md. No
Foundational phase is needed: the generic per-row `step` mechanism both
stories reuse was already built and shipped by
`020-turning-feed-per-rotation` (`split_pane.NumberRow.step`,
`nudge_selected()`'s `Decimal`-safe arithmetic) and already extended onto
one screen by `024-feed-per-tooth-nudge-step` (milling's `_number_row()`
`step` parameter) — this feature only extends that same, already-proven
mechanism to nine more call sites across three screens, two of which
(drilling, turning) still need their `_number_row()` helper extended the
way milling's already was.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Phase 1: Setup

No project-initialization tasks — this feature touches three existing
files in an already-scaffolded package. Nothing to set up.

---

## Phase 2: Foundational

None. The mechanism this feature configures (`NumberRow.step`,
`nudge_selected()`) already exists and needs no change — see research.md
#2.

---

## Phase 3: User Story 1 - Fine-Tune Geometry Fields with Arrow Keys Under Imperial (Priority: P1) 🎯 MVP

**Goal**: In the TUI, all nine listed geometry fields (milling's cutter
diameter, axial depth of cut, radial depth, length of cut; drilling's
drill diameter, hole depth; turning's workpiece diameter, depth of cut,
length of cut) nudge by 0.1 in via Left/Right arrows under IMPERIAL,
while keeping today's 1.0 mm step under METRIC (spec.md User Story 1).

**Independent Test**: On each of the three screens, switch to Imperial,
select each listed field, press Right/Left arrows, and verify the value
moves by exactly 0.1 in, while every other field on that screen (and the
same nine fields under Metric) keeps its existing step (quickstart.md
Scenarios 1-4, 6).

### Tests for User Story 1

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation.

- [X] T001 [P] [US1] Integration test: milling's cutter diameter, axial
  depth of cut, radial engagement, and length of cut rows each nudge by
  `0.1` under IMPERIAL and by the unchanged `split_pane.NUDGE_STEP`
  (`1.0`) under METRIC, distinct from and without disturbing
  feed-per-tooth's own existing `0.1`/`0.001` step, in
  `tests/integration/test_tui_milling.py`.
- [X] T002 [P] [US1] Integration test: drilling's drill diameter and hole
  depth rows each nudge by `0.1` under IMPERIAL and by the unchanged
  `split_pane.NUDGE_STEP` (`1.0`) under METRIC, while available
  power/other rows keep the default step, in
  `tests/integration/test_tui_drilling.py`.
- [X] T003 [P] [US1] Integration test: turning's workpiece diameter, depth
  of cut, and length of cut rows each nudge by `0.1` under IMPERIAL and by
  the unchanged `split_pane.NUDGE_STEP` (`1.0`) under METRIC, distinct
  from and without disturbing the feed-rate-per-rotation field's own
  existing `0.1`/`0.005` step, in `tests/integration/test_tui_turning.py`.

### Implementation for User Story 1

- [X] T004 [US1] Compute `geometry_step = split_pane.NUDGE_STEP if
  state.unit_system is UnitSystem.METRIC else 0.1` and pass it as `step=`
  to the cutter diameter, axial depth of cut, radial engagement, and
  length of cut rows' `_number_row(...)` calls in `rows_for()`,
  `src/mfgparams/console/tui/screens/milling.py` (milling's `_number_row()`
  already accepts `step`, added by `024-feed-per-tooth-nudge-step`;
  research.md #1; contracts/cli-repl-imperial-geometry-nudge-step-delta.md;
  depends on T001 existing and failing). **Post-implementation
  correction**: superseded by T015 — this call site now reads
  `geometry_step = split_pane.geometry_nudge_step(state.unit_system)`.
- [X] T005 [US1] Add an optional `step: float = split_pane.NUDGE_STEP`
  parameter to `_number_row()` in
  `src/mfgparams/console/tui/screens/drilling.py`, passed through to the
  underlying `split_pane.NumberRow(..., step=step)` construction, mirroring
  milling's existing shape
  (contracts/cli-repl-imperial-geometry-nudge-step-delta.md; depends on
  T002 existing and failing).
- [X] T006 [US1] Compute `geometry_step = split_pane.NUDGE_STEP if
  state.unit_system is UnitSystem.METRIC else 0.1` and pass it as `step=`
  to the drill diameter and hole depth rows' `_number_row(...)` calls in
  `rows_for()`, `src/mfgparams/console/tui/screens/drilling.py`
  (research.md #1; depends on T005). **Post-implementation correction**:
  superseded by T015, same as T004.
- [X] T007 [US1] Add an optional `step: float = split_pane.NUDGE_STEP`
  parameter to `_number_row()` in
  `src/mfgparams/console/tui/screens/turning.py`, passed through to the
  underlying `split_pane.NumberRow(..., step=step)` construction, mirroring
  milling's existing shape
  (contracts/cli-repl-imperial-geometry-nudge-step-delta.md; depends on
  T003 existing and failing).
- [X] T008 [US1] Compute `geometry_step = split_pane.NUDGE_STEP if
  state.unit_system is UnitSystem.METRIC else 0.1` and pass it as `step=`
  to the workpiece diameter, depth of cut, and length of cut rows'
  `_number_row(...)` calls in `rows_for()`,
  `src/mfgparams/console/tui/screens/turning.py` (research.md #1; depends
  on T007). **Post-implementation correction**: superseded by T015, same
  as T004.

**Checkpoint**: User Story 1 is fully functional and independently
testable — all nine fields nudge by 0.1 in under Imperial across the
three screens.

---

## Phase 4: User Story 2 - Correct Step Applies Immediately After Switching Unit System (Priority: P2)

**Goal**: The very next arrow-key nudge on any of the nine fields after
the user toggles the unit-system radio row uses the newly-active unit
system's step, not a leftover step from before the switch (spec.md User
Story 2).

**Independent Test**: Enter a value under one unit system, switch the
screen to the other, and immediately nudge the same field, verifying the
step used matches the unit system now active (quickstart.md Scenario 5).

### Tests for User Story 2

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation
> — though given how T004-T008 compute `geometry_step` (freshly, from
> `state.unit_system`, inline in `rows_for()`, never cached), these tests
> are expected to pass as soon as Phase 3 is done; they exist to make that
> property explicit and regression-proof rather than to drive new code.

- [X] T009 [P] [US2] Integration test: after switching milling's unit
  system Metric→Imperial then Imperial→Metric mid-session, the very next
  nudge on cutter diameter (or any of the four geometry fields) uses the
  newly-active unit system's step (`0.1` / `1.0` respectively), repeated
  across two switches, in `tests/integration/test_tui_milling.py`.
- [X] T010 [P] [US2] Integration test: same switch-then-nudge check for
  drilling's drill diameter/hole depth, in
  `tests/integration/test_tui_drilling.py`.
- [X] T011 [P] [US2] Integration test: same switch-then-nudge check for
  turning's workpiece diameter/depth of cut/length of cut, in
  `tests/integration/test_tui_turning.py`.

### Implementation for User Story 2

None. T004-T008 already satisfy this story: each screen's `rows_for()`
recomputes `geometry_step` fresh from `state.unit_system` on every render
— it is never stored or cached — so the property T009-T011 assert is a
direct consequence of Phase 3's implementation shape, not additional code
(research.md #2; contracts/cli-repl-imperial-geometry-nudge-step-delta.md
"Arrow-key nudge step").

**Checkpoint**: User Story 2 is verified — no code beyond Phase 3 is
needed; T009-T011 confirm it holds.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T015 Extract the `geometry_step` computation
  (`NUDGE_STEP if state.unit_system is UnitSystem.METRIC else 0.1`),
  duplicated verbatim by T004/T006/T008 across
  `screens/milling.py`/`screens/drilling.py`/`screens/turning.py`, into
  one shared `split_pane.geometry_nudge_step(unit_system)` function; update
  all three call sites to call it instead. Found by a local `/code-review`
  pass (very-high intensity, `pr-review-loop`, run in local-only mode
  after Copilot review credits were exhausted): Constitution Principle I
  ("absence of duplicated logic"; magic numbers tied to physical meaning
  named) — a future revision to the imperial geometry step value would
  require editing three files, and missing one would silently leave that
  screen's fields on the old step with no test catching the
  *inconsistency*. research.md #2's correction and the contract delta have
  the full before/after.
- [X] T012 [P] Check `docs/source/milling.rst`, `docs/source/drilling.rst`,
  and `docs/source/turning.rst` for prose describing the default nudge
  step ("1 display unit for most fields" / "small step" / "1
  display-unit step every other numeric field uses") and update each so it
  no longer implies the nine geometry fields nudge by 1 display unit under
  Imperial.
- [X] T013 Run `specs/025-imperial-geometry-nudge-step/quickstart.md`'s
  Regression check (`pytest tests/unit/console/tui/ tests/integration/ -k
  "milling or drilling or turning" -q`) and confirm all pre-existing
  milling/drilling/turning TUI tests still pass. 92 passed. Full suite
  also run: 1615 passed, 12 skipped, 95.96% coverage.
- [X] T014 **REQUIRED (Constitution Principle XIII)** — confirmed complete
  by the user (2026-09-23) on a real terminal: all 6 `quickstart.md`
  scenarios (all nine fields nudge by exactly 0.1 in under Imperial;
  unchanged 1.0 mm under Metric; the step used immediately after switching
  unit system, twice, matches the newly active system;
  feed-per-tooth/feed-rate-per-rotation and non-geometry fields are
  unaffected) confirmed working — not satisfied by T001-T003/T009-T011's
  automated tests alone. This is the interactive-TUI case of Principle
  XIII, performed by the user, not the implementing agent.

> **NOTE (Principle XIII)**: This feature is the interactive console/TUI
> case only (arrow-key nudge behavior) — the non-interactive
> reference-fidelity case does not apply, since this feature makes no claim
> of matching an external reference document/table exactly (research.md #1
> is a direct restatement of the feature request's own explicit value, not
> a derived shop-practice judgement call requiring external citation).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: None — no tasks.
- **Foundational (Phase 2)**: None — no tasks; the mechanism this feature
  configures already exists.
- **User Story 1 (Phase 3)**: Can start immediately. Tests (T001-T003)
  before implementation (T004-T008); within each screen, the `step=`
  parameter task (T005 for drilling, T007 for turning) must complete
  before that screen's call-site task (T006, T008 respectively); T004
  (milling) has no such prerequisite since milling's `_number_row()`
  already has `step`.
- **User Story 2 (Phase 4)**: Depends on Phase 3 (T004-T008) being
  complete — T009-T011 assert a property of that same implementation, so
  they cannot be meaningfully written/run before it exists.
- **Polish (Phase 5)**: Depends on Phase 3 and Phase 4 being complete;
  T014 additionally depends on T013 (run the automated regression check
  first, so manual verification isn't spent catching something the
  existing suite would have caught for free).

### Parallel Opportunities

- T001, T002, T003 (all US1 tests) can run in parallel — different files,
  no shared dependencies.
- T009, T010, T011 (all US2 tests) can run in parallel — different files.
- T004 (milling) has no dependency on T005-T008 and can run in parallel
  with them; T005/T007 (the two `step=` parameter additions) can run in
  parallel with each other.
- T012 (docs check) can run in parallel with T001-T011.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Integration test: milling's 4 geometry rows' step under METRIC/IMPERIAL, other rows unaffected, in tests/integration/test_tui_milling.py"
Task: "Integration test: drilling's 2 geometry rows' step under METRIC/IMPERIAL, other rows unaffected, in tests/integration/test_tui_drilling.py"
Task: "Integration test: turning's 3 geometry rows' step under METRIC/IMPERIAL, other rows unaffected, in tests/integration/test_tui_turning.py"
```

---

## Implementation Strategy

### MVP First — User Story 1

1. Skip Phase 1/2 (no tasks).
2. Complete Phase 3: User Story 1 (T001-T008) — all nine fields nudge by
   0.1 in under Imperial.
3. **STOP and VALIDATE**: Independently test User Story 1 per
   quickstart.md Scenarios 1-4, 6.

### Incremental Delivery

1. Complete Phase 3 (US1) → deploy/demo the imperial-step behavior alone.
2. Add Phase 4 (US2) → confirm the switch-then-nudge correctness guarantee
   holds, with its own regression tests.
3. Complete Phase 5: run the automated regression check (T013), then get
   the manual verification (T014) confirmed by the developer/reviewer
   before considering this feature done.
