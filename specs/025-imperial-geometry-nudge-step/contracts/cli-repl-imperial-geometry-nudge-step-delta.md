# Contract Delta: Imperial Arrow-Key Nudge Step for Geometry Fields

**Feature**: `025-imperial-geometry-nudge-step` | **Date**: 2026-09-23

Mirrors this repo's existing delta-contract style (e.g.
`specs/024-feed-per-tooth-nudge-step/contracts/cli-repl-feed-per-tooth-nudge-step-delta.md`).
Documents the row-level behavior change this feature makes to
`specs/018-tui-splitpane-redesign/contracts/console-tui-splitpane-contract.md`'s
generic "Left/Right nudges the buffer's value by a small step" row —
every other part of that contract is unaffected and remains authoritative.

## Drilling's and turning's `_number_row()` gain an optional `step` parameter

Both currently have no way to override `split_pane.NumberRow`'s default
step (shown here for drilling; turning's is identically shaped):

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

After this feature, each gains a defaulted `step` parameter — identical
in shape to milling's existing one (`024-feed-per-tooth-nudge-step`) — so
every existing call site (available power, target RPM, feed rate, number
of teeth) is unaffected:

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

## A shared helper computes the geometry step

**Post-implementation correction**: an earlier draft of this contract had
each of the nine call sites compute the two-branch expression inline
(`NUDGE_STEP if state.unit_system is UnitSystem.METRIC else 0.1`),
duplicated verbatim across three files. A local `/code-review` pass
(very-high intensity, `pr-review-loop`) flagged this as real duplication
of this feature's own logic under Constitution Principle I (see
research.md #2's correction) and it was extracted into one shared
function in `split_pane.py` before merge:

```python
def geometry_nudge_step(unit_system: UnitSystem) -> float:
    return NUDGE_STEP if unit_system is UnitSystem.METRIC else 0.1
```

Each of the nine call sites calls this helper and passes the result as
`step=`:

```python
geometry_step = split_pane.geometry_nudge_step(state.unit_system)
```

Applied at:

- `screens/milling.py`: `diameter` (cutter diameter), `axial_depth_of_cut`,
  `radial_engagement`, `length_of_cut` rows.
- `screens/drilling.py`: `diameter` (drill diameter), `depth` (hole depth)
  rows.
- `screens/turning.py`: `diameter` (workpiece diameter), `depth_of_cut`,
  `length_of_cut` rows.

Example (drilling's drill diameter row):

```python
geometry_step = split_pane.geometry_nudge_step(state.unit_system)
rows.append(
    _number_row(
        FieldId.DIAMETER,
        translate(locale, "tui.label.diameter"),
        labels["diameter"],
        state.diameter,
        True,
        lambda value: setattr(state, "diameter", value),
        step=geometry_step,
    )
)
```

## Arrow-key nudge step

Each of the nine rows' `step` is `split_pane.NUDGE_STEP` (1.0) under
METRIC — unchanged from today — and `0.1` under IMPERIAL (research.md
#1). Because each screen's `rows_for()` recomputes this expression fresh
on every render from `state.unit_system`, the correct step applies
immediately after the user toggles the unit-system `RadioRow`, with no
additional transition-specific logic (User Story 2) — the same property
the 020/024 precedents already rely on.

Every other row on these three screens — available power, target RPM,
number of teeth, milling's feed-per-tooth (0.1/0.001,
`024-feed-per-tooth-nudge-step`), turning's feed-rate-per-rotation
(0.1/0.005, `020-turning-feed-per-rotation`) — is unaffected and keeps its
existing step exactly as it is today.

## What this contract does NOT change

- Any of the nine fields' value, validation, or use in
  `calculate_end_milling()`/`calculate_face_milling()`/`calculate_drilling()`/
  `calculate_turning()` (or mode-specific variants) — unchanged.
- Unit-system conversion of any field's remembered value
  (`_convert_on_unit_change` in each screen module) — unchanged; the step
  value itself is simply re-evaluated against the current unit system on
  every render, the same way milling's and turning's existing custom-step
  fields already are.
- Every other row's nudge step, label, or layout — unchanged.
- The interaction model itself (buffer-only edits until commit,
  nudge-below-zero clears to unset, radio-row cycling) — unchanged from
  `018-tui-splitpane-redesign`.
