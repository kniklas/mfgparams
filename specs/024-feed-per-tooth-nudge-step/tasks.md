---

description: "Task list for 024-feed-per-tooth-nudge-step"
---

# Tasks: Milling Feed-Per-Tooth Nudge Step

**Input**: Design documents from `specs/024-feed-per-tooth-nudge-step/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: A single user story (US1, P1) — spec.md has only one story,
since this feature is a scoped refinement of one already-shipped field's
arrow-key step, not new functionality. No Foundational phase is needed: the
generic per-row `step` mechanism this feature reuses was already built and
shipped by `020-turning-feed-per-rotation` (`split_pane.NumberRow.step`,
`nudge_selected()`'s `Decimal`-safe arithmetic) — unlike that feature, which
had to add the mechanism itself before it could use it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)

## Phase 1: Setup

No project-initialization tasks — this feature touches one existing file in
an already-scaffolded package. Nothing to set up.

---

## Phase 2: Foundational

None. The mechanism this feature configures (`NumberRow.step`,
`nudge_selected()`) already exists and needs no change — see research.md #2.

---

## Phase 3: User Story 1 - Fine-Tune Feed Per Tooth with Arrow Keys (Priority: P1) 🎯 MVP

**Goal**: In the TUI, milling's feed-per-tooth field nudges by 0.1 mm/tooth
(METRIC) / 0.001 in/tooth (IMPERIAL) via Left/Right arrows, distinct from
every other milling numeric field's existing 1.0-display-unit step
(spec.md User Story 1).

**Independent Test**: Select a milling operation, select the feed-per-tooth
field, press Right/Left arrows, and verify the value moves by 0.1 mm/tooth
under Metric and 0.001 in/tooth under Imperial, while every other milling
field's arrow-key step is unchanged (quickstart.md Scenarios 1-4).

### Tests for User Story 1

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation.

- [X] T001 [P] [US1] ~~Extend `test_number_row_step_defaults_to_nudge_step()`
  in `tests/integration/test_tui_field_editing.py`~~ — **post-implementation
  correction**: that test only ever exercised drilling's screen as the
  generic-default representative (never milling/turning individually,
  despite its docstring's broader claim); `020-turning-feed-per-rotation`'s
  own field-specific step tests likewise lived in `test_tui_turning.py`,
  not there. Folded into T002 instead: the "other milling rows keep
  `NUDGE_STEP`" assertion is now part of
  `test_feed_per_tooth_row_nudges_by_a_finer_step_than_other_milling_rows()`
  in `tests/integration/test_tui_milling.py`, alongside the step-value
  assertion itself — matching where the equivalent turning coverage
  actually lives, not the plan's original (mistaken) file guess.
- [X] T002 [P] [US1] Integration test: milling's feed-per-tooth field nudges
  by `0.1` under METRIC and `0.001` under IMPERIAL via Left/Right arrows,
  distinct from milling's other rows' default `1.0` step, in
  `tests/integration/test_tui_milling.py`
  (`test_feed_per_tooth_row_nudges_by_a_finer_step_than_other_milling_rows`,
  `test_feed_per_tooth_row_nudges_by_a_finer_step_under_imperial`,
  `test_feed_per_tooth_step_applies_to_face_milling_too`) — covers both
  End Milling and Face Milling sub-operations (spec.md Acceptance
  Scenario 4 / FR-006).
- [X] T003 [P] [US1] Integration test: the feed-per-tooth field's
  remembered value converts correctly (not silently relabeled) across a
  mid-session unit-system switch, and a nudge that would take it at or
  below zero clears it to unset, mirroring the existing pattern for other
  nudge-adjustable fields, in `tests/integration/test_tui_milling.py`
  (`test_feed_per_tooth_converts_across_a_unit_system_switch`,
  `test_feed_per_tooth_nudge_below_zero_clears_rather_than_going_negative`).

### Implementation for User Story 1

- [X] T004 [US1] Add an optional `step: float = split_pane.NUDGE_STEP`
  parameter to `_number_row()` in
  `src/mfgparams/console/tui/screens/milling.py`, passed through to the
  underlying `split_pane.NumberRow(..., step=step)` construction
  (contracts/cli-repl-feed-per-tooth-nudge-step-delta.md; depends on
  T001-T003 existing and failing).
- [X] T005 [US1] Compute `step = 0.1 if state.unit_system is
  UnitSystem.METRIC else 0.001` and pass it to the `feed_per_tooth` row's
  `_number_row(...)` call in `rows_for()`,
  `src/mfgparams/console/tui/screens/milling.py` (research.md #1;
  contracts/cli-repl-feed-per-tooth-nudge-step-delta.md; depends on T004).

**Checkpoint**: User Story 1 is fully functional and independently
testable — this is the entire feature (single-story scope).

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T006 [P] Check `docs/source/milling.rst` for any prose naming the old
  default nudge step for feed per tooth and update it if present. Found
  (line 42, generic "small step" prose) and updated to name the new
  0.1 mm/tooth / 0.001 in/tooth step explicitly, mirroring how
  `docs/source/turning.rst` documents its own equivalent field.
- [X] T007 Run `specs/024-feed-per-tooth-nudge-step/quickstart.md`'s
  Regression check (`pytest tests/unit/console/tui/ tests/integration/ -k
  milling -q`) and confirm all pre-existing milling TUI tests still pass.
  36 passed. Full suite also run: 1606 passed, 12 skipped.
- [ ] T008 **REQUIRED (Constitution Principle XIII)** Manually verify, on a
  real terminal, `quickstart.md` Scenarios 1-4 (metric nudge lands on
  exactly 0.1/0.2/0.3/0.4/0.3; nudge-below-zero clears to unset; imperial
  nudge is exactly 0.001 in, not 0.1 or 0.005; every other milling field's
  step is unchanged; both End Milling and Face Milling show the same
  behavior) — not satisfied by T001-T003's automated tests alone. This is
  the interactive-TUI case of Principle XIII: it MUST be performed by the
  developer or a reviewer, not the implementing agent alone (the agent MAY
  perform T001-T003, but not this task, on the developer's behalf). Leave
  unchecked and say so rather than marking it complete without that
  confirmation.

> **NOTE (Principle XIII)**: This feature is the interactive console/TUI
> case only (arrow-key nudge behavior) — the non-interactive
> reference-fidelity case does not apply, since this feature makes no claim
> of matching an external reference document/table exactly (research.md #1
> is a shop-practice judgement call, not a cited external reference to
> verify against).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: None — no tasks.
- **Foundational (Phase 2)**: None — no tasks; the mechanism this feature
  configures already exists.
- **User Story 1 (Phase 3)**: Can start immediately. Tests (T001-T003)
  before implementation (T004-T005); T004 before T005 (T005 calls the
  parameter T004 adds).
- **Polish (Phase 4)**: Depends on Phase 3 (T004, T005) being complete;
  T008 additionally depends on T007 (run the automated regression check
  first, so manual verification isn't spent catching something the
  existing suite would have caught for free).

### Parallel Opportunities

- T001, T002, T003 (all tests) can run in parallel with each other —
  different concerns, and T002/T003 can share one test module without
  conflicting since they're independent test functions.
- T006 (docs check) can run in parallel with T001-T005.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Extend test_number_row_step_defaults_to_nudge_step() for feed_per_tooth in tests/integration/test_tui_field_editing.py"
Task: "Integration test: feed_per_tooth nudge step under METRIC/IMPERIAL, both sub-operations, in tests/integration/test_tui_milling.py"
Task: "Integration test: feed_per_tooth unit-conversion and nudge-below-zero behavior, in tests/integration/test_tui_milling.py"
```

---

## Implementation Strategy

### MVP First (and only) — User Story 1

1. Skip Phase 1/2 (no tasks).
2. Complete Phase 3: User Story 1 (T001-T005).
3. **STOP and VALIDATE**: Run Phase 4's automated regression check (T007),
   then get Phase 4's manual verification (T008) confirmed by the
   developer/reviewer before considering this feature done.
4. This is the entire feature — there is no further story to add.
