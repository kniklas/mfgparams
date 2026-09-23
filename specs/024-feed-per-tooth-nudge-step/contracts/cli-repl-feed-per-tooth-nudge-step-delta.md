# Contract Delta: Milling Feed-Per-Tooth Nudge Step

**Feature**: `024-feed-per-tooth-nudge-step` | **Date**: 2026-09-23

Mirrors this repo's existing delta-contract style (e.g.
`specs/020-turning-feed-per-rotation/contracts/cli-repl-turning-feed-per-rotation-delta.md`).
Documents the one row-level behavior change this feature makes to
`specs/018-tui-splitpane-redesign/contracts/console-tui-splitpane-contract.md`'s
generic "Left/Right nudges the buffer's value by a small step" row —
every other part of that contract is unaffected and remains authoritative.

## `_number_row()` gains an optional `step` parameter

`src/mfgparams/console/tui/screens/milling.py`'s shared row-construction
helper currently has no way to override `split_pane.NumberRow`'s default
step:

```python
def _number_row(
    field_id: FieldId, label: str, unit: str, value: float | None, required: bool, setter
) -> split_pane.NumberRow:
    return split_pane.NumberRow(
        field_id=field_id,
        label=label,
        unit=unit,
        value=value,
        required=required,
        on_commit=setter,
    )
```

After this feature, it gains a defaulted `step` parameter, so every
existing call site is unaffected:

```python
def _number_row(
    field_id: FieldId,
    label: str,
    unit: str,
    value: float | None,
    required: bool,
    setter,
    step: float = split_pane.NUDGE_STEP,
) -> split_pane.NumberRow:
    return split_pane.NumberRow(
        field_id=field_id,
        label=label,
        unit=unit,
        value=value,
        required=required,
        on_commit=setter,
        step=step,
    )
```

## `feed_per_tooth`'s row passes a unit-system-dependent step

```python
step = 0.1 if state.unit_system is UnitSystem.METRIC else 0.001
rows.append(
    _number_row(
        FieldId.FEED_PER_TOOTH,
        translate(locale, "tui.label.feed_per_tooth"),
        labels["feed_per_tooth"],
        state.feed_per_tooth,
        True,
        lambda value: setattr(state, "feed_per_tooth", value),
        step=step,
    )
)
```

**Note (added by `025-imperial-geometry-nudge-step`, not a re-opening of
this spec)**: the `step = ...` line's inline ternary was later factored
into a shared `split_pane.step_for(unit_system, metric, imperial)`
helper — the current source reads
`feed_per_tooth_step = split_pane.step_for(state.unit_system, 0.1, 0.001)`,
same values, same behavior. Left here as historical record of this
spec's own decision; see
`specs/025-imperial-geometry-nudge-step/research.md` #2 for the
extraction's rationale.

## Arrow-key nudge step

The feed-per-tooth row's `step` (0.1 under METRIC, 0.001 under IMPERIAL —
research.md #1) is distinct from every other milling row's default
`NUDGE_STEP` (1.0 display unit): tool diameter, axial depth of cut, radial
engagement/width of cut, number of teeth, available power, and target RPM
are all unaffected and keep nudging by 1.0 per Left/Right arrow press,
exactly as they do today.

## What this contract does NOT change

- `feed_per_tooth`'s value, validation, or its use in
  `calculate_end_milling()`/`calculate_face_milling()` — unchanged.
- Unit-system conversion of the field's remembered value
  (`_convert_on_unit_change` in `screens/milling.py`) — unchanged; the step value
  itself is simply re-evaluated against the current unit system on every
  render, the same way `screens/turning.py`'s equivalent step already is.
- Every other row's nudge step, label, or layout — unchanged.
- The interaction model itself (buffer-only edits until commit,
  nudge-below-zero clears to unset, radio-row cycling) — unchanged from
  `018-tui-splitpane-redesign`/`020-turning-feed-per-rotation`.
