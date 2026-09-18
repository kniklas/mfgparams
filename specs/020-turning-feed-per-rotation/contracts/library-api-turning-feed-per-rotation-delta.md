# Contract Delta: Turning Library API — Feed Rate Per Rotation & Constrained Mode

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

Extends `specs/019-turning-calculations/contracts/library-api-turning.md`
(unchanged except as noted below). Only the delta is documented here.

## Signature change

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
    target_feed_rate: float | None = None,   # NEW
) -> CalculationResult: ...
```

- `target_feed_rate`: **NEW.** Required when `mode is
  CalculationMode.FEED_RATE_CONSTRAINED`: the caller-supplied feed rate per
  workpiece rotation to calculate from, in the units of `unit_system` (mm/rev
  METRIC, in/rev IMPERIAL) — instead of deriving it from the material/tool's
  reference feed value. Supplying it together with any other mode
  (`CalculationMode.STANDARD`, `CalculationMode.POWER_CONSTRAINED`, or
  `CalculationMode.FIXED_RPM`) is a `MODE_CONFLICT` — checked locally in
  turning's own `_validate_mode_inputs()`, not the shared
  `validate_mode_arguments()` (data-model.md). Supplying a `target_rpm`
  together with `mode is CalculationMode.FEED_RATE_CONSTRAINED` is also a
  `MODE_CONFLICT` (checked in the shared `validate_mode_arguments()`,
  mirroring `POWER_CONSTRAINED`'s identical rejection). **Appended after
  `materials_config_path`, not immediately after `target_rpm`** — a
  Copilot review finding on this PR caught an earlier draft that inserted
  it ahead of `materials_config_path`, which would have silently broken
  any caller passing that pre-existing parameter positionally (its own
  index must stay unchanged for backward compatibility).
- Every other parameter's contract is unchanged, including
  `materials_config_path`'s own positional index. Existing callers that
  never pass `target_feed_rate` (the new parameter's default is `None`)
  see no behavior change — this is an additive, backward-compatible
  signature extension (MINOR version bump, Constitution Principle IV),
  exactly as `target_rpm` itself was when
  `002-constrained-calculation-modes` introduced it.

## Result field addition

```python
CalculationResult(
    ...,
    cutting_force=826.7,
    feed_per_rotation=0.2036,   # NEW field — mm/rev (METRIC) or in/rev (IMPERIAL)
)
```

- `feed_per_rotation` is populated on every successful turning result
  (standard, fixed-RPM, power-constrained, and feed-rate-constrained modes)
  and is `None` on any error result. It is `None` for every drilling and
  milling result, always (per the resolved Clarification — `feed_rate`'s
  existing per-time meaning and value are unchanged for every operation;
  this is a new, additive, turning-specific field, not a redefinition).

## Success response contract (feed-rate-constrained mode) — NEW

```python
CalculationResult(
    spindle_speed_rpm=1018.6,      # derived exactly as standard mode (from cutting speed + diameter)
    feed_rate=100.0,               # = spindle_speed_rpm * target_feed_rate, still mm/min, unchanged meaning
    feed_per_rotation=0.0982,      # caller-supplied target_feed_rate, echoed back (mm/rev)
    machining_time=1.99,           # recomputed from the supplied feed rate
    torque=6.0,                    # recomputed from the supplied feed rate (depends on it, unlike drilling/milling's torque)
    power_required=0.64,           # recomputed from the supplied feed rate
    cutting_force=398.7,           # recomputed from the supplied feed rate
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,       # or set, per FR-008, if power_required > available_power
    mode=CalculationMode.FEED_RATE_CONSTRAINED,
    error=None,
)
```

Unlike `FIXED_RPM` mode's `torque`/`cutting_force` (unchanged from the
nominal, since they don't depend on spindle speed — `019-turning-calculations`
research.md #1), feed-rate-constrained mode's `cutting_force`/`torque`/
`power_required` **do** change from the nominal value, because turning's
cutting force is `Fc = Kc * ap * fn` — it depends directly on the feed per
revolution (`fn`), which is exactly what this mode lets the caller override.

## Error response contract — NEW

```python
# Feed-rate-constrained mode, target_feed_rate <= 0, non-numeric, or non-finite
CalculationResult(
    ..., error=ErrorInfo(code="INVALID_TARGET_FEED_RATE", message="Feed rate per rotation must be a positive, finite number."),
)

# Feed-rate-constrained mode without a supplied target_feed_rate
CalculationResult(
    ..., error=ErrorInfo(code="INVALID_TARGET_FEED_RATE", message="Feed rate per rotation must be a positive, finite number."),
)

# target_feed_rate supplied together with target_rpm, or with mode is POWER_CONSTRAINED/FIXED_RPM
CalculationResult(
    ..., error=ErrorInfo(code="MODE_CONFLICT", message="..."),
)
```

### Error codes summary — one new code

| Code | Trigger |
|---|---|
| `INVALID_TARGET_FEED_RATE` | **NEW.** `target_feed_rate` zero/negative/non-numeric/non-finite, or missing, when `mode is FEED_RATE_CONSTRAINED` (data-model.md). |

`MODE_CONFLICT`, `INVALID_AVAILABLE_POWER`, and `CALCULATION_OVERFLOW` are
reused verbatim for this mode's own conflict/advisory-power/overflow cases.
Every other `019-turning-calculations` error code and its trigger is
unchanged.

## Identical-results guarantee (FR-016, unchanged contract)

The console interface and the library continue to produce identical
`CalculationResult` values for identical inputs, including identical
`mode`/`target_feed_rate` selections — the console's new feed-per-rotation
field is purely an input-gathering row that calls the same
`calculate_turning()` a library caller would use.

## Scope note (FR-014)

`calculate()` (drilling), `calculate_end_milling()`, and
`calculate_face_milling()` do **not** gain a `target_feed_rate` parameter,
and their calculation behavior for every mode they do support is
unaffected by this feature. `CalculationMode.FEED_RATE_CONSTRAINED` exists
on the shared enum (data-model.md), but only `calculate_turning()`'s
dispatch acts on it — the other three functions each gain one small,
explicit guard: since the enum member is still constructible and passable
to their own public signatures regardless of the console's own restricted
mode list, each rejects it with a structured `UNSUPPORTED_MODE` error
(research.md #3) rather than silently falling through to a standard-mode
result mislabeled with that mode — a Copilot review finding on this PR
established this call shape is reachable, not hypothetical.
