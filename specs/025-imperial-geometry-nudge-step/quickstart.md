# Quickstart: Imperial Arrow-Key Nudge Step for Geometry Fields

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving this feature works end-to-end, once
implemented. Assumes the same setup as
`specs/018-tui-splitpane-redesign/quickstart.md` (editable install,
`pytest` available); not repeated here.

## Prerequisites

```bash
pip install -e ".[console,dev]"
```

## Scenario 1 — Imperial nudge on milling's four geometry fields (User Story 1, Acceptance Scenario 1)

Manual-verification scenario — **must be performed by the developer or a
reviewer against a real terminal** (Constitution Principle XIII; this is
an interactive-TUI behavior change, not something a fully passing
automated test suite alone establishes as correct to a human observer):

1. Launch the console (`mfgparams`, or the project's documented entry
   point), open Machining → Milling.
2. Select material type, material, milling sub-operation, and tool.
3. Switch Unit system to Imperial.
4. For each of Cutter diameter, Axial depth of cut, Radial depth (or
   Width of cut, depending on sub-operation), and Length of cut: select
   the field, press Right arrow once — confirm the value increases by
   exactly `0.1` (in), not `1.0`. Press Left once — confirm it decreases
   back by `0.1`.

**Expected**: All four fields nudge by exactly `0.1` in per press under
Imperial — confirms FR-001/SC-001.

## Scenario 2 — Imperial nudge on drilling's two geometry fields (User Story 1, Acceptance Scenario 2)

1. Open Machining → Drilling, select material type/material/tool.
2. Switch Unit system to Imperial.
3. For each of Drill diameter and Hole depth: select the field, press
   Right arrow once — confirm the value increases by exactly `0.1` (in).

**Expected**: Both fields nudge by exactly `0.1` in per press under
Imperial — confirms FR-002/SC-001.

## Scenario 3 — Imperial nudge on turning's three geometry fields (User Story 1, Acceptance Scenario 3)

1. Open Machining → Turning, select material type/material/tool.
2. Switch Unit system to Imperial.
3. For each of Workpiece diameter, Depth of cut, and Length of cut: select
   the field, press Right arrow once — confirm the value increases by
   exactly `0.1` (in).

**Expected**: All three fields nudge by exactly `0.1` in per press under
Imperial — confirms FR-003/SC-001.

## Scenario 4 — Metric unchanged (Acceptance Scenario 4, FR-004)

1. On any of the three screens, with Unit system set to Metric, select
   any of the nine geometry fields and press Right arrow once.

**Expected**: The value increases by exactly `1.0` (mm) — today's
existing default, unchanged — confirms FR-004/SC-002.

## Scenario 5 — Step follows the unit system immediately after switching (User Story 2)

Manual-verification scenario, same setup as Scenario 1:

1. On the milling screen, with Unit system set to Metric, enter a value
   for Cutter diameter (e.g. type `10`, navigate away to commit it).
2. Switch Unit system to Imperial: confirm the value converts (mm → in)
   via the existing conversion, not silently relabeled (FR-006).
3. Immediately — without any other action — select Cutter diameter and
   press Right arrow once: confirm the value increases by exactly `0.1`
   (in), not `1.0`.
4. Switch Unit system back to Metric, then immediately press Right arrow
   once on Cutter diameter: confirm the value increases by exactly `1.0`
   (mm), not `0.1`.
5. Repeat step 2–4's switch-then-nudge check once more (Metric → Imperial
   → Metric) to confirm the step keeps following the active unit system
   on repeated switches, not just the first one.

**Expected**: Every nudge immediately after a switch uses the
newly-active unit system's step, with no leftover step from before the
switch — confirms FR-005/SC-004 (User Story 2).

## Scenario 6 — Other fields and prior features unaffected (Edge Cases, FR-008)

1. On the milling screen under Imperial, select Feed per tooth and press
   Right arrow once: confirm the value increases by `0.001` (in) — its
   own existing `024-feed-per-tooth-nudge-step` step, not `0.1`.
2. On the turning screen under Imperial (feed-rate-constrained mode),
   select Feed rate per rotation and press Right arrow once: confirm the
   value increases by `0.005` (in) — its own existing
   `020-turning-feed-per-rotation` step, not `0.1`.
3. On any of the three screens, select Available power (or Target RPM,
   Number of teeth) and press Right arrow once: confirm the value
   increases by `1.0` — the unchanged shared default, under both unit
   systems.

**Expected**: Confirms FR-008/SC-003 — this feature changes only the nine
named geometry fields' imperial step.

## Regression check

```bash
pytest tests/unit/console/tui/ tests/integration/ -k "milling or drilling or turning" -q
```

**Expected**: All pre-existing milling/drilling/turning TUI tests continue
to pass unmodified in their assertions on every field other than the nine
geometry fields' imperial nudge step; only new/extended assertions for
those nine fields' `step` values are additive.
