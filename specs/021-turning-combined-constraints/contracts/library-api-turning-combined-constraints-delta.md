# Contract Delta: Turning Library API — Combined-Constraint Modes

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

Extends `specs/020-turning-feed-per-rotation/contracts/library-api-turning-feed-per-rotation-delta.md`
(unchanged except as noted below). Only the delta is documented here.

## Signature — unchanged

```python
def calculate_turning(
    diameter: float,
    depth_of_cut: float,
    length_of_cut: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = DEFAULT_LOCALE,
    mode: CalculationMode = CalculationMode.STANDARD,
    target_rpm: float | None = None,
    materials_config_path: str | None = None,
    target_feed_rate: float | None = None,
) -> CalculationResult: ...
```

No new parameter. Both new modes reuse `target_rpm`, `available_power`, and
`target_feed_rate` — every field already exists (data-model.md).

## `CalculationMode` — two new members

- `CalculationMode.ROTATION_AND_FEED_CONSTRAINED` (`"rotation-and-feed-constrained"`):
  requires both `target_rpm` and `target_feed_rate`. Spindle speed is the supplied
  `target_rpm` directly (never derived from cutting speed). Feed per rotation is the
  supplied `target_feed_rate` directly (never derived from the material/tool's
  reference feed). Machining time, cutting force, torque, and power are computed from
  those two values exactly as `calculate_turning_metrics_at_rpm()` already computes
  them for every other mode.
- `CalculationMode.POWER_AND_FEED_CONSTRAINED` (`"power-and-feed-constrained"`):
  requires both `available_power` (as a **hard constraint**, not advisory — same
  treatment `POWER_CONSTRAINED` already gives it) and `target_feed_rate`. Spindle speed
  is solved to the highest value feasible within `available_power` at the supplied
  `target_feed_rate`, using the same closed-form linear-scaling derivation
  `POWER_CONSTRAINED` already uses (research.md #3) — but never solved *above* the
  cutting-speed-derived reference speed at that feed (the same reference speed
  standard mode uses): a surplus of available power beyond what that reference speed
  requires does not raise the recommended spindle speed further, mirroring
  `POWER_CONSTRAINED`'s own identical ceiling. Machining time and cutting
  force/torque/power follow from that resulting spindle speed and the supplied feed.

## Error codes — zero new codes

| Code | New trigger |
|---|---|
| `INVALID_TARGET_RPM` | (existing) `target_rpm` missing/zero/negative/non-numeric when `mode is ROTATION_AND_FEED_CONSTRAINED`. |
| `INVALID_TARGET_FEED_RATE` | (existing) `target_feed_rate` missing/zero/negative/non-numeric when `mode is ROTATION_AND_FEED_CONSTRAINED` or `mode is POWER_AND_FEED_CONSTRAINED`. |
| `MODE_CONFLICT` | (existing) `available_power` missing under `POWER_AND_FEED_CONSTRAINED`; `target_rpm` supplied under `POWER_AND_FEED_CONSTRAINED`; `target_feed_rate` supplied under any mode outside `TURNING_ONLY_MODES` (reverse-conflict, data-model.md). `target_rpm`'s own reverse-conflict is narrower than `target_feed_rate`'s: only the modes that actually derive/solve spindle speed (`POWER_CONSTRAINED`, `FEED_RATE_CONSTRAINED`, `POWER_AND_FEED_CONSTRAINED`) reject a directly-supplied `target_rpm` — `STANDARD` ignores it entirely (ok in this MODE_CONFLICT context, but not reachable through `FIXED_RPM`/`ROTATION_AND_FEED_CONSTRAINED`, which treat it as their own required/accepted input) (corrected by a Copilot review finding on PR #102: an earlier draft of this row stated the blanket rule uniformly for both fields, which `STANDARD` does not actually enforce for `target_rpm`). |
| `INFEASIBLE_POWER_BUDGET` | (existing) `available_power` non-positive/non-finite under `POWER_AND_FEED_CONSTRAINED`; **or** `POWER_AND_FEED_CONSTRAINED`'s result underflows/overflows to a non-finite or non-positive field (`_reject_if_invalid`'s error code for this mode, mirroring `POWER_CONSTRAINED`'s own identical choice — both modes solve for spindle speed within a power budget, so an invalid result reads as "no feasible operating point" under that same budget, not a generic calculation overflow). In practice, any positive budget yields *some* positive spindle speed via the same linear scaling `POWER_CONSTRAINED` already uses without a floor, so the extreme-input path is reached only via genuinely subnormal geometry, exactly as it is for `POWER_CONSTRAINED` today. |
| `CALCULATION_OVERFLOW` | (existing) `ROTATION_AND_FEED_CONSTRAINED`'s result underflows/overflows to a non-finite or non-positive field (`_reject_if_invalid`'s error code for this mode, mirroring `FIXED_RPM`'s/`FEED_RATE_CONSTRAINED`'s identical choice — none of these three derive/solve for spindle speed within a power budget, so an invalid result is a generic overflow, not an infeasible-budget case). **Not** used by `POWER_AND_FEED_CONSTRAINED`'s equivalent failure — see `INFEASIBLE_POWER_BUDGET` above (Copilot review finding on PR #102: an earlier draft of this table implied `CALCULATION_OVERFLOW` applied uniformly to both new modes, which the implementation never did). |
| `MISSING_MATERIAL` / `MISSING_TOOL` | (existing) Unchanged precedence — still checked before any mode-specific validation, for both new modes. |

## Precedence for combined-invalid requests

If a request supplies inputs belonging to two conflicting modes at once (e.g.
`target_rpm` supplied under `POWER_AND_FEED_CONSTRAINED`, which solves for spindle
speed rather than accepting one directly, or `target_feed_rate` supplied under
`STANDARD` mode), `MODE_CONFLICT` is reported for the *reverse-conflict* case (a
field present under the wrong mode) before any mode's own required-field validity
is checked — this is the existing, established precedence (research.md #4), not
new. (Corrected by a Copilot review finding on PR #102: an earlier draft of this
example used `target_rpm` under `ROTATION_AND_FEED_CONSTRAINED`, but `target_rpm`
is one of *that* mode's own two required inputs, not a foreign field — an invalid
value there is `INVALID_TARGET_RPM`, never `MODE_CONFLICT`.)

Within `ROTATION_AND_FEED_CONSTRAINED`'s own two required fields, if both `target_rpm`
and `target_feed_rate` are simultaneously missing or invalid, `target_rpm`'s validity
is checked first (data-model.md), so `INVALID_TARGET_RPM` is returned rather than
`INVALID_TARGET_FEED_RATE`.

## Example: rotation-and-feed-constrained success

```python
result = calculate_turning(
    diameter=40, depth_of_cut=2, length_of_cut=100,
    material="Mild Steel", tool="Carbide",
    mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
    target_rpm=900, target_feed_rate=0.3,
)
assert result.error is None
assert result.spindle_speed_rpm == 900  # exact, not derived
assert result.feed_per_rotation == 0.3  # exact, not derived
```

## Example: power-and-feed-constrained success

```python
result = calculate_turning(
    diameter=40, depth_of_cut=2, length_of_cut=100,
    material="Mild Steel", tool="Carbide",
    mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
    available_power=0.5, target_feed_rate=0.3,
)
assert result.error is None
assert result.power_required <= 0.5  # (plus floating-point tolerance)
assert result.feed_per_rotation == 0.3  # exact, not derived
```

## Example: mode conflict

```python
result = calculate_turning(
    diameter=40, depth_of_cut=2, length_of_cut=100,
    material="Mild Steel", tool="Carbide",
    mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
    target_feed_rate=0.3, target_rpm=900,  # target_rpm doesn't apply to this mode
)
assert result.error.code == "MODE_CONFLICT"
```

## Drilling/milling: `UNSUPPORTED_MODE` (extended, not new)

`calculate()` (drilling), `calculate_end_milling()`, and `calculate_face_milling()`
reject `ROTATION_AND_FEED_CONSTRAINED` and `POWER_AND_FEED_CONSTRAINED` the same way
they already reject `FEED_RATE_CONSTRAINED` — a structured `UNSUPPORTED_MODE` error,
added in this feature's own implementation (not deferred to a later review round,
research.md #7).

## Identical-results guarantee (unchanged contract)

The console interface and the library continue to produce identical
`CalculationResult` values for identical inputs, including identical
`mode`/`target_rpm`/`available_power`/`target_feed_rate` selections, for both new
modes — no new code path exists between them.
