# Contract Delta: Console Text GUI — Turning Feed Rate Per Rotation & Constrained Mode

**Feature**: [../spec.md](../spec.md) | **Library contract**: [./library-api-turning-feed-per-rotation-delta.md](./library-api-turning-feed-per-rotation-delta.md)

Extends `specs/019-turning-calculations/contracts/cli-repl-turning.md`
(unchanged except as noted below). Only the delta is documented here.

## Mode row (`screens/turning.py::rows_for`)

`_MODE_OPTION_KEYS` gains a fourth entry:

```python
_MODE_OPTION_KEYS = {
    CalculationMode.STANDARD: "tui.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "tui.mode.power_constrained",
    CalculationMode.FIXED_RPM: "tui.mode.fixed_rpm",
    CalculationMode.FEED_RATE_CONSTRAINED: "tui.mode.feed_rate_constrained",   # NEW
}
```

The mode `RadioRow` (already reused verbatim from
`019-turning-calculations`) automatically offers the new option — no other
change to that row.

## `TurningSessionState` — one new field

```python
@dataclass
class TurningSessionState:
    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    depth_of_cut: float | None = None
    length_of_cut: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    target_feed_rate: float | None = None   # NEW
    previous_mode: CalculationMode = CalculationMode.STANDARD
```

`_set_mode()`'s existing clearing logic (`if new_mode is not
state.previous_mode: state.available_power = None; state.target_rpm =
None`) gains `state.target_feed_rate = None` in the same block — a
feed-rate-constrained value is never carried over as an editable default
into a different mode, mirroring how `target_rpm` is already cleared on a
mode change.

`_convert_on_unit_change()` gains one new line, mirroring
`depth_of_cut`/`length_of_cut`/`available_power`'s existing treatment:

```python
if state.target_feed_rate is not None:
    state.target_feed_rate = forms.convert_length(
        state.target_feed_rate, state.unit_system, unit_system
    )
```

## New row: Feed rate per rotation (shown only in feed-rate-constrained mode)

`rows_for()` adds a `_feed_rate_row()` factory alongside the existing
`_power_row()`/`_rpm_row()`:

```python
def _feed_rate_row() -> split_pane.NumberRow:
    step = 0.1 if state.unit_system is UnitSystem.METRIC else 0.005  # see note below
    return split_pane.NumberRow(
        field_id=FieldId.TARGET_FEED_RATE,
        label=translate(locale, "tui.label.target_feed_rate"),
        unit=labels["feed_per_rotation"],
        value=state.target_feed_rate,
        required=True,
        on_commit=lambda value: setattr(state, "target_feed_rate", value),
        step=step,
    )
```

**Note (added by `025-imperial-geometry-nudge-step`, not a re-opening of
this spec)**: this line's inline ternary was later factored into a shared
`split_pane.step_for(unit_system, metric, imperial)` helper — the current
source reads `step = split_pane.step_for(state.unit_system, 0.1, 0.005)`,
same values, same behavior. Left here as historical record of the
decision this contract documents (research.md #7); see
`specs/025-imperial-geometry-nudge-step/research.md` #2 for the
extraction's own rationale.

and passes it through the shared `power_and_rpm_rows()` helper
(data-model.md), alongside the new `feed_rate_constrained` flag:

```python
rows.extend(
    split_pane.power_and_rpm_rows(
        power_constrained=state.mode is CalculationMode.POWER_CONSTRAINED,
        fixed_rpm=state.mode is CalculationMode.FIXED_RPM,
        feed_rate_constrained=state.mode is CalculationMode.FEED_RATE_CONSTRAINED,   # NEW
        power_row=_power_row,
        rpm_row=_rpm_row,
        feed_rate_row=_feed_rate_row,   # NEW
    )
)
```

Row visibility by mode (extends `019-turning-calculations`' existing
mode-conditional trailing rows):

| Mode | Trailing row(s) |
|---|---|
| Standard | Available power (optional) — unchanged |
| Power-constrained | Available power (required) — unchanged |
| Fixed-RPM | Target spindle speed (required), Available power (optional) — unchanged |
| **Feed-rate-constrained** | **NEW** — Feed rate per rotation (required), Available power (optional) |

## Arrow-key nudge step (FR-011)

The feed-rate-per-rotation row's `step` (0.1 under METRIC, 0.005 under
IMPERIAL — research.md #7) is distinct from every other turning row's
default `NUDGE_STEP` (1.0 display unit): diameter, depth of cut, length of
cut, available power, and target RPM are all unaffected and keep nudging by
1.0 per Left/Right arrow press, exactly as `019-turning-calculations`
shipped them.

## Spindle-speed mode label — required, not optional

`forms.py::_SPINDLE_SPEED_MODE_LABEL_KEYS` is a plain dict lookup
(`_SPINDLE_SPEED_MODE_LABEL_KEYS[result.mode]`), not an `if`/`elif` chain.
Without a `FEED_RATE_CONSTRAINED` entry, every feed-rate-constrained result
would raise `KeyError` the moment `format_result()` runs (research.md #9) —
this is a required correctness fix, not optional polish. New entry:
`CalculationMode.FEED_RATE_CONSTRAINED:
"tui.result.spindle_speed.mode.feed_rate_constrained"`, new catalog value
`"derived from cutting speed"` — spindle speed is derived from cutting
speed and diameter exactly as `STANDARD` mode's is (FR-005); the supplied
feed rate only affects downstream metrics, so a label implying feed
determines spindle speed would be physically inaccurate (Copilot review
finding on this PR: an earlier draft used `"derived from specified feed
rate"`).

## Result display: new "Feed per rotation" line

`forms.UNIT_LABELS` gains `"feed_per_rotation": "mm/rev"` (METRIC) /
`"in/rev"` (IMPERIAL). `format_result()` adds a new line, conditional on
`result.feed_per_rotation is not None` (research.md #10), following the
existing `tui.result.*` per-field convention, placed immediately after the
existing Feed rate line (so the two related feed values sit together):

```text
Spindle speed:     1018.6 RPM (recommended)
Feed rate:         100.0 mm/min
Feed per rotation: 0.0982 mm/rev      <- NEW
Machining time:    1.99 min
Torque:            6.0 N·m
Power required:    0.64 kW
Cutting force:     398.7 N
```

Shown for every turning result (all four modes) — never for drilling or
milling results, whose `CalculationResult.feed_per_rotation` is always
`None` (result-rendering code already skips any field that is `None`,
exactly as it already does for `cutting_force` on drilling/milling results).

## Design-review note (`tui-design` skill)

The new mode option, the new mode-conditional row, and the new result line
all reuse existing style classes verbatim (`RadioRow`, `NumberRow`, the
existing `tui.result.*` line format) — no new color, layout, or interaction
pattern is introduced. The one genuinely new interaction, a per-row nudge
step distinct from the shared default, is a numeric parameter on the
existing `NumberRow`, not a new visual element. Per the `tui-design` skill's
own criterion ("a net-new UI region with no exact prototype to copy" needs a
sign-off), nothing here qualifies: the mode row, the field row, and the
result line all have an exact prototype (the existing target-RPM row and its
result-line counterpart) — this is noted here rather than skipped silently,
per that skill's intent, mirroring `019-turning-calculations`' own
identically-reasoned note for its Depth of cut row.

## Identical-results guarantee (FR-016, unchanged contract)

The console's turning screen and the library continue to produce identical
`CalculationResult` values for identical inputs — `calculate_result()`
passes `target_feed_rate=state.target_feed_rate` through to
`calculate_turning()` unchanged, exactly as it already does for
`target_rpm`.
