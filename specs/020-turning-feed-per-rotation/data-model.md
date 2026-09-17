# Phase 1 Data Model: Turning Feed Rate Per Rotation & Constrained Mode

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This document extends `specs/019-turning-calculations/data-model.md` (turning's
entities) and `specs/002-constrained-calculation-modes/data-model.md` (the
`CalculationMode` model this feature adds a fourth, turning-only member to).
Entities not mentioned here (`WorkpieceMaterial`, `TurningTool`,
`MaterialToolCompatibility`, `Configuration`, `ErrorInfo`'s existing codes) are
unchanged and not repeated.

## CalculationMode (enum) — one new member

| Member | Value | Notes |
|---|---|---|
| `STANDARD` | `"standard"` | Unchanged. |
| `POWER_CONSTRAINED` | `"power-constrained"` | Unchanged. |
| `FIXED_RPM` | `"fixed-rpm"` | Unchanged. |
| `FEED_RATE_CONSTRAINED` | `"feed-rate-constrained"` | **NEW.** Spindle speed is derived exactly as `STANDARD` (from the material's/tool's reference cutting speed and the diameter); the caller supplies a target feed rate per workpiece rotation directly instead of it being derived from the material's/tool's reference feed value (spec.md FR-004/FR-005). Turning-only by convention (research.md #3) — drilling's and milling's own dispatch never construct this member, and explicitly reject it (`UNSUPPORTED_MODE`) if a caller supplies it directly, since their own dispatch has no calculation branch for it. |

## TurningOperation (request) — extended

Extends `019-turning-calculations/data-model.md`'s `TurningOperation` with one
new optional field:

| Field | Type | Notes |
|---|---|---|
| `target_feed_rate` | float \| None | **NEW.** Required when `mode == FEED_RATE_CONSTRAINED`; rejected (via `MODE_CONFLICT`, see below) if supplied together with a `target_rpm`. In the units of the selected `unit_system` (mm/rev under METRIC, in/rev under IMPERIAL) — unlike `target_rpm`, this quantity is **not** unit-system-independent. |

**Validation** (extends `019-turning-calculations/data-model.md`'s ordering —
the existing nine-step material/tool/geometry validation still runs first,
unchanged; mode-argument validation still runs after):

- `target_feed_rate`, when supplied, MUST be a positive, finite number in its
  as-supplied (display-unit) form; zero, negative, non-numeric, `NaN`, or
  `Infinity` values are all rejected under `ErrorInfo(code=
  "INVALID_TARGET_FEED_RATE")` (FR-006) — **new** `validate_target_feed_rate()`
  (`src/mfgparams/validation.py`), byte-for-byte mirroring
  `validate_target_rpm()`'s shape (research.md #5). No additional maximum
  bound is checked, mirroring `target_rpm`'s existing posture.
- `mode`/`target_feed_rate`/`target_rpm` mutual exclusivity extends the
  existing shared `validate_mode_arguments()` (research.md #3): supplying
  `target_rpm` while `mode is FEED_RATE_CONSTRAINED` is `MODE_CONFLICT`,
  mirroring `POWER_CONSTRAINED`'s existing rejection of a simultaneously
  supplied `target_rpm`. `available_power` remains optional/advisory in
  `FEED_RATE_CONSTRAINED` mode (FR-008), type/finiteness-checked the same
  way `STANDARD`/`FIXED_RPM` already are (`INVALID_AVAILABLE_POWER`).
- Supplying `target_feed_rate` while `mode is not FEED_RATE_CONSTRAINED` is
  also rejected as `MODE_CONFLICT` — checked locally in turning's own
  `_validate_mode_inputs()` (not the shared `validate_mode_arguments()`,
  which never receives `target_feed_rate` and is left untouched for this
  direction), mirroring the mode-conflict symmetry `target_rpm` already has
  with `POWER_CONSTRAINED`.
- Once validated, `target_feed_rate` converts to metric
  (`to_metric_length(target_feed_rate, unit_system)`) at the same point in
  `_validate_and_prepare()` diameter/depth-of-cut/length-of-cut already
  convert (research.md #8), before the formula layer runs.

## TurningMetrics (internal calculation output) — one new field

Extends `019-turning-calculations/data-model.md`'s `TurningMetrics`:

| Field | Type | Notes |
|---|---|---|
| `spindle_speed_rpm` | float | Unchanged. |
| `feed_rate_mm_min` | float | Unchanged — still mm/min; **not** redefined by this feature (spec.md FR-002, resolved Clarification). |
| `feed_per_rev_mm` | float | **NEW.** mm/rev — the value every mode already computes internally (research.md #1); now returned instead of discarded. In `FEED_RATE_CONSTRAINED` mode this equals the caller-supplied `target_feed_rate` (converted to mm); in the other three modes it is `material.reference_feed_per_rev_mm * tool.feed_factor`, exactly as today. |
| `machining_time_min` | float | Unchanged. |
| `cutting_force_n` | float | Unchanged. |
| `torque_nm` | float | Unchanged. |
| `power_kw` | float | Unchanged. |

`calculate_turning_metrics_at_rpm()` gains one new optional parameter,
`feed_per_rev_mm: float | None = None` (research.md #2): `None` (every
existing call site) preserves today's material/tool-derived behavior exactly;
a supplied value is used directly instead, and is also what populates the new
`TurningMetrics.feed_per_rev_mm` field.

One new function, mirroring `calculate_turning_power_constrained_metrics()`'s
shape:

- `calculate_turning_feed_rate_constrained_metrics(diameter_mm,
  depth_of_cut_mm, length_of_cut_mm, material, tool,
  target_feed_per_rev_mm) -> TurningMetrics` — derives spindle speed exactly
  as `calculate_turning_metrics()` (standard mode), then delegates to
  `calculate_turning_metrics_at_rpm(..., feed_per_rev_mm=
  target_feed_per_rev_mm)` (research.md #2).

`turning/__init__.py::_reject_if_invalid()`'s finiteness/positivity guard
tuple gains `feed_per_rev_mm` as a seventh guarded field (research.md #6).

## CalculationResult (response, extended — reused across all operations)

Extends the shared `CalculationResult` (`src/mfgparams/models.py`) with one
new optional field, appended after the existing `cutting_force` field
(research.md #4, same positional-construction-compatibility placement
`cutting_force`/`material_removal_rate` themselves established):

| Field | Type | Notes |
|---|---|---|
| `feed_per_rotation` | float \| None | **NEW.** mm/rev under METRIC, in/rev under IMPERIAL. Populated for turning (every mode) on success; `None` for turning on error and `None` for drilling/milling always (per the resolved Clarification — `feed_rate`'s existing meaning and value are unchanged for every operation, this is a purely additive field). |

All other `CalculationResult` fields, including `feed_rate` itself, are
reused with **no change to their meaning, value, or unit** (FR-002).

## Error Codes — one new code

| Code | Trigger |
|---|---|
| `INVALID_TARGET_FEED_RATE` | **NEW.** `target_feed_rate` zero/negative/non-numeric/non-finite when `mode is FEED_RATE_CONSTRAINED` (research.md #5). New `error.invalid_target_feed_rate` catalog entry (`src/mfgparams/locales/en.py`). |

`MODE_CONFLICT`, `INVALID_AVAILABLE_POWER`, and `CALCULATION_OVERFLOW` are
reused verbatim (their existing semantics already cover the new mode's
conflict/advisory-power/overflow cases — research.md #3, #6). Every other
`019-turning-calculations` error code is unaffected.

## `TurningSessionState` (console TUI, internal) — extended

`screens/turning.py`'s `TurningSessionState` gains one new field, mirroring
how it already carries `target_rpm` for `FIXED_RPM`:

| Field | Type | Notes |
|---|---|---|
| `target_feed_rate` | float \| None | **NEW.** Cleared (reset to `None`) whenever the mode changes away from `FEED_RATE_CONSTRAINED` (`_set_mode`'s existing clearing logic, extended), never carried over from a different mode — mirroring `target_rpm`'s existing clearing behavior. Converts on a mid-session unit-system switch via `forms.convert_length()` (research.md #8), mirroring milling's `feed_per_tooth` field. |

## `NumberRow` (console TUI, shared `split_pane.py`) — one new field

| Field | Type | Notes |
|---|---|---|
| `step` | float | **NEW.** Defaults to the existing module-level `NUDGE_STEP` (`1.0`), so every existing row (drilling, milling, turning's own diameter/depth/length/power/RPM rows) is unaffected. Turning's new feed-per-rotation row sets `step=0.1` under METRIC / `step=0.005` under IMPERIAL (research.md #7). `nudge_selected()` reads `row.step` instead of the module-level constant directly. |

## `FieldId` (console TUI, shared `app.py`) — one new member

| Member | Value | Notes |
|---|---|---|
| `TARGET_FEED_RATE` | `"target_feed_rate"` | **NEW.** Identifies the feed-per-rotation row, shown only when turning's mode is `FEED_RATE_CONSTRAINED` (mirrors `TARGET_RPM`'s existing `FIXED_RPM`-only visibility). |

## `power_and_rpm_rows()` (console TUI, shared `split_pane.py`) — extended, backward compatible

Extended with two new, defaulted keyword parameters so drilling's and
milling's existing call sites (which never pass them) are unaffected:

```python
def power_and_rpm_rows(
    *,
    power_constrained: bool,
    fixed_rpm: bool,
    feed_rate_constrained: bool = False,          # NEW, defaults False
    power_row: Callable[[str, bool], NumberRow],
    rpm_row: Callable[[], NumberRow],
    feed_rate_row: Callable[[], NumberRow] | None = None,   # NEW, defaults None
) -> list[Row]:
```

Dispatch order (first match wins, mirroring the existing `if
power_constrained` / `if fixed_rpm` / fallback shape):

1. `power_constrained` → `[power_row(required)]` — unchanged.
2. `fixed_rpm` → `[rpm_row(), power_row(optional)]` — unchanged.
3. `feed_rate_constrained` → **NEW** — `[feed_rate_row(), power_row(optional)]`.
4. Otherwise (standard) → `[power_row(optional)]` — unchanged.

## `format_result()` (console TUI, shared `forms.py`) — extended

`_SPINDLE_SPEED_MODE_LABEL_KEYS` (a plain dict keyed by `CalculationMode`,
looked up unconditionally as `_SPINDLE_SPEED_MODE_LABEL_KEYS[result.mode]`)
gains a fourth entry — required, not optional, since a missing key raises
`KeyError` (research.md #9):

| Mode | Catalog key |
|---|---|
| `FEED_RATE_CONSTRAINED` | **NEW** `tui.result.spindle_speed.mode.feed_rate_constrained` |

`format_result()` also gains a new line, conditional on
`result.feed_per_rotation is not None`, appended immediately after the
existing `tui.result.feed_rate` line — mirroring the existing
`material_removal_rate`/`cutting_force` optional-line convention
(research.md #10).

## Message Catalog — new keys

Core library catalog (`src/mfgparams/locales/en.py`, English-only per
Constitution VIII / spec.md FR-013):

- `error.invalid_target_feed_rate`: `"Feed rate per rotation must be a positive, finite number."`

Console-only catalog (`src/mfgparams/console/locales/en.py`):

- `tui.mode.feed_rate_constrained`: `"feed-rate-constrained"`
- `tui.label.target_feed_rate`: `"Feed rate per rotation"`
- `tui.result.feed_per_rotation`: `"Feed per rotation:  {value} {unit}"`
- `tui.result.spindle_speed.mode.feed_rate_constrained`: `"derived from specified feed rate"`

`forms.UNIT_LABELS` gains one new key under both `UnitSystem` entries:

| Unit system | `feed_per_rotation` |
|---|---|
| METRIC | `"mm/rev"` |
| IMPERIAL | `"in/rev"` |
