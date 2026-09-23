# Quickstart: Milling Feed-Per-Tooth Nudge Step

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving this feature works end-to-end, once
implemented. Assumes the same setup as
`specs/018-tui-splitpane-redesign/quickstart.md` (editable install,
`pytest` available); not repeated here.

## Prerequisites

```bash
pip install -e ".[console,dev]"
```

## Scenario 1 — Metric arrow-key nudge (User Story 1, Acceptance Scenario 1)

Manual-verification scenario — **must be performed by the developer or a
reviewer against a real terminal** (Constitution Principle XIII; this is
an interactive-TUI behavior change, not something a fully passing
automated test suite alone establishes as correct to a human observer):

1. Launch the console (`mfgparams`, or the project's documented entry
   point), open Machining → Milling.
2. Select material type, material, milling sub-operation (End Milling or
   Face Milling), and tool, so the feed-per-tooth field is visible.
3. Confirm Unit system is Metric.
4. Select the Feed per tooth field. Press Right arrow once: value goes
   from unset/`0` to `0.1` — not `1.0`, confirming the field-specific
   nudge step (FR-001). Press Right three more times: `0.4`. Press Left
   once: `0.3`.
5. Press Left repeatedly until the value would go below `0`: confirm it
   clears to unset rather than going negative (FR-005, mirroring every
   other field's existing behavior).

**Expected**: Step 4's sequence lands on exactly `0.1`, `0.2`, `0.3`,
`0.4`, `0.3` — confirms FR-001/SC-001. Step 5 confirms FR-005.

## Scenario 2 — Imperial arrow-key nudge (User Story 1, Acceptance Scenario 2)

Manual-verification scenario, same setup as Scenario 1:

1. With the Feed per tooth field selected and a value already entered
   under Metric, switch Unit system to Imperial: confirm the value
   converts (mm → in) via the same conversion diameter/depth-of-cut
   already use, not silently relabeled (FR-004).
2. Press Right arrow once: value increases by `0.001` (in) — the
   researched imperial step (research.md #1) — not `0.1` and not the
   turning field's `0.005`.

**Expected**: Step 2's increment is exactly `0.001` in — confirms
FR-002/SC-002.

## Scenario 3 — Other fields unaffected (Edge Cases, FR-003)

1. On the same milling screen, select the tool diameter (or any other
   numeric) field.
2. Press Right arrow once: value increases by `1.0` — the unchanged
   shared default, confirming this feature did not change any other
   row's step.

**Expected**: Confirms FR-003/SC-003.

## Scenario 4 — Face milling and end milling both affected (Acceptance Scenario 4, FR-006)

1. Repeat Scenario 1 on an End Milling operation.
2. Repeat Scenario 1 on a Face Milling operation.

**Expected**: Both sub-operations show the same `0.1` mm/tooth step —
confirms FR-006.

## Regression check

```bash
pytest tests/unit/console/tui/ tests/integration/ -k milling -q
```

**Expected**: All pre-existing milling TUI tests continue to pass
unmodified in their assertions on every field other than
`feed_per_tooth`'s nudge step; only a new/extended assertion for
`feed_per_tooth`'s `step` value is additive.
