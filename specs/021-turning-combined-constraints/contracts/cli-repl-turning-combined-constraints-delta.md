# Contract Delta: Turning Console TUI — Combined-Constraint Modes

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

Extends `specs/020-turning-feed-per-rotation/contracts/cli-repl-turning-feed-per-rotation-delta.md`.
Only the delta is documented here. See `tui-machining-menu-auto-hide-delta.md` for the
separate, operation-agnostic Machining-menu visibility contract (User Story 3).

## Mode selector — two new options

The turning screen's Mode row (`FieldId.MODE`, a `RadioRow`) gains two new options,
appended after the existing four, cycling via Left/Right/Space per the existing
`RadioRow` convention:

| Catalog key | English value |
|---|---|
| `tui.mode.rotation_and_feed_constrained` | `"rotation-and-feed-constrained"` |
| `tui.mode.power_and_feed_constrained` | `"power-and-feed-constrained"` |

`turning.py`'s `_MODE_OPTION_KEYS` dict gains both entries, mapping
`CalculationMode.ROTATION_AND_FEED_CONSTRAINED`/`.POWER_AND_FEED_CONSTRAINED` to these
keys.

## Field rows per mode

`split_pane.power_and_rpm_rows()` gains two new defaulted keyword parameters —
`rotation_and_feed_constrained: bool = False` and `power_and_feed_constrained: bool =
False` — with two new branches, reusing the screen's existing `rpm_row()`,
`feed_rate_row()`, and `power_row()` factories unchanged:

| Mode | Rows shown (in order) | Required |
|---|---|---|
| `ROTATION_AND_FEED_CONSTRAINED` | Target spindle speed, Feed rate per rotation, Available power | Spindle speed **required**, feed **required**, power **optional** |
| `POWER_AND_FEED_CONSTRAINED` | Feed rate per rotation, Available power | Feed **required**, power **required** |

Both rows' nudge steps are unchanged from their existing definitions: target spindle
speed nudges by the shared default (1.0 RPM per Left/Right press); feed per rotation
nudges by the existing finer step (0.1 mm/rev METRIC, 0.005 in/rev IMPERIAL,
`020-turning-feed-per-rotation` FR-011). No new nudge-step value is introduced.

`turning.py`'s `rows_for()` passes both new booleans through, gated on
`state.mode is CalculationMode.ROTATION_AND_FEED_CONSTRAINED` /
`state.mode is CalculationMode.POWER_AND_FEED_CONSTRAINED` respectively, mirroring the
existing three modes' identical gating pattern.

## Result display — spindle-speed label (required addition, not optional)

`forms.py`'s `_SPINDLE_SPEED_MODE_LABEL_KEYS` dict lookup is a hard `KeyError` source
for any mode without an entry (`020-turning-feed-per-rotation` research.md #9) —
**both new modes MUST have an entry before this feature ships**, or every result in
either mode crashes the console's result rendering. New entries, both reusing
**existing** catalog values (no new string, Constitution Principle VIII):

| Mode | Label key | Reused catalog value |
|---|---|---|
| `ROTATION_AND_FEED_CONSTRAINED` | `tui.result.spindle_speed.mode.rotation_and_feed_constrained` | `tui.result.spindle_speed.mode.fixed_rpm`'s existing value, `"user-specified"` |
| `POWER_AND_FEED_CONSTRAINED` | `tui.result.spindle_speed.mode.power_and_feed_constrained` | `tui.result.spindle_speed.mode.power_constrained`'s existing value, `"adjusted to fit available power"` |

(Each mode still gets its own catalog *key*, since `_SPINDLE_SPEED_MODE_LABEL_KEYS`
maps one `CalculationMode` to one key; only the *value* those two new keys resolve to
is a reuse of an existing string, not a new one.)

The `feed_per_rotation` result line (`tui.result.feed_per_rotation`, `020`) is shown
for both new modes exactly as it already is for every mode — no change.

## Mode-switch behavior — unchanged

`turning.py`'s `_set_mode()` clears `available_power`/`target_rpm`/`target_feed_rate`
whenever the mode actually changes (comparing against `state.previous_mode`) — this
logic is mode-generic already and needs no change for the two new modes.

## Unit-system switch — unchanged

`_convert_on_unit_change()` already converts `target_feed_rate` and `available_power`
across a unit-system switch (`020`); `target_rpm` is unit-system-independent (already
true for `FIXED_RPM`, unchanged). Both new modes inherit this behavior unchanged since
they reuse the same session-state fields.
