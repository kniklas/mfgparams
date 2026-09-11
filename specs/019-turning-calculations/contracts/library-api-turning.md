# Contract: Turning Library API

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

The public contract exposed by `mfgparams` for the new `turning` process (FR-001, FR-003
through FR-014), consumable independent of the console interface, following the same
"never raises for expected validation failures" contract already established by
`specs/001-metal-drilling-calc/contracts/library-api.md` and extended by
`specs/002-constrained-calculation-modes/contracts/library-api-delta.md` (FR-016 of this
feature).

## Public surface

```python
from mfgparams import calculate_turning, list_turning_tools, UnitSystem, CalculationMode
```

`calculate_turning()` is implemented in `mfgparams.processes.machining.turning` and
re-exported at the top level (`mfgparams/__init__.py`) alongside the existing
`calculate` (drilling), `calculate_end_milling`, and `calculate_face_milling` (all
unchanged — FR-001, FR-002). `list_materials()` / `list_material_types()` (shared,
unchanged) continue to enumerate workpiece materials for turning as well.

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
) -> CalculationResult: ...

def list_turning_tools(config_path: str | None = None) -> list[str]: ...
```

- `calculate_turning(...)` MUST NOT raise for expected validation failures (invalid or
  missing input, missing/unknown material or tool, unsupported material/tool combination,
  depth of cut not less than the workpiece radius, mode-argument conflicts, infeasible
  power budget, exceeded power rating). It MUST always return a `CalculationResult`
  (data-model.md), mirroring drilling's and milling's `calculate*()` contracts (FR-016).
- All parameters are in the units of `unit_system` (mm for `diameter`/`depth_of_cut`/
  `length_of_cut`, RPM for `target_rpm`, kW/HP for `available_power` per METRIC/IMPERIAL);
  identical convention to drilling and milling.
- `mode`, `target_rpm`, `available_power`, `locale`, and `materials_config_path` behave
  identically to their drilling/milling counterparts (FR-012, FR-013, FR-014, FR-015).
- Callers that never pass `mode`/`target_rpm` get `STANDARD` mode behavior — there is no
  drilling-style "pre-modes" version of turning to stay backward compatible with, since
  this feature ships all three modes from its first release (plan.md Scale/Scope).

## Success response contract (standard mode)

```python
CalculationResult(
    spindle_speed_rpm=1018.6,
    feed_rate=203.7,
    machining_time=0.98,
    torque=12.4,
    power_required=1.32,
    cutting_force=826.7,          # NEW field (data-model.md) — None for drilling/milling
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.STANDARD,
    error=None,
)
```

## Success response contract (fixed-RPM mode)

```python
CalculationResult(
    spindle_speed_rpm=900.0,       # caller-supplied target_rpm, echoed back
    feed_rate=180.0,
    machining_time=1.11,
    torque=12.4,                   # unchanged — independent of spindle speed (research.md #1)
    power_required=1.17,
    cutting_force=826.7,           # unchanged — independent of spindle speed
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,       # or set, per FR-014, if power_required > available_power
    mode=CalculationMode.FIXED_RPM,
    error=None,
)
```

## Success response contract (power-constrained mode)

```python
CalculationResult(
    spindle_speed_rpm=650.2,       # reduced from the nominal standard-mode value
    feed_rate=130.0,
    machining_time=1.54,
    torque=12.4,                    # unchanged
    power_required=0.85,            # equals the supplied available_power (within float tolerance)
    cutting_force=826.7,            # unchanged
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.POWER_CONSTRAINED,
    error=None,
)
```

If the supplied `available_power` is already sufficient at the nominal standard-mode
spindle speed, the result is identical to the `STANDARD`-mode result for the same inputs
except `mode`, mirroring `specs/002-constrained-calculation-modes` FR-003.

## Error response contracts

```python
# Depth of cut >= workpiece radius (spec.md Edge Cases; data-model.md)
CalculationResult(
    spindle_speed_rpm=None, feed_rate=None, machining_time=None,
    torque=None, power_required=None, cutting_force=None,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.STANDARD,
    error=ErrorInfo(code="INVALID_DEPTH_OF_CUT", message="Depth of cut must be less than the workpiece radius."),
)

# Length of cut zero/negative/non-numeric/exceeds maximum (reuses milling's code)
CalculationResult(
    ..., error=ErrorInfo(code="INVALID_LENGTH_OF_CUT", message="Length of cut must be greater than 0."),
)

# Fixed-RPM mode, target_rpm <= 0 or non-numeric (reused from drilling)
CalculationResult(
    ..., error=ErrorInfo(code="INVALID_TARGET_RPM", message="Target spindle speed must be greater than 0."),
)

# Power-constrained mode, no positive RPM fits the budget (reused from drilling)
CalculationResult(
    ..., error=ErrorInfo(code="INFEASIBLE_POWER_BUDGET", message="No spindle speed keeps required power within the available power budget."),
)

# Conflicting/incomplete mode arguments (reused from drilling)
CalculationResult(
    ..., error=ErrorInfo(code="MODE_CONFLICT", message="Power-constrained and fixed-RPM modes cannot be combined in one request."),
)
```

### Error codes summary (data-model.md) — zero new codes

Every failure turning can produce reuses an existing code — new *functions* and new
*config bounds* (`validate_turning_diameter_mm`/`max_turning_diameter_mm`,
`validate_turning_depth_of_cut_mm`/`max_turning_depth_of_cut_mm`,
`validate_turning_length_of_cut_mm`/`max_turning_length_of_cut_mm`) back them, mirroring
drilling's/milling's own per-operation-bound precedent, but no new error vocabulary:

| Code | Trigger |
|---|---|
| `INVALID_DIAMETER` | Diameter zero/negative/non-numeric/exceeds `max_turning_diameter_mm` |
| `INVALID_DEPTH_OF_CUT` | Depth of cut zero/negative/non-numeric/exceeds `max_turning_depth_of_cut_mm`, or not strictly less than the workpiece radius (three checks, one code — `ErrorInfo.code`'s documented "coarser than message_key" contract) |
| `INVALID_LENGTH_OF_CUT` | Length of cut zero/negative/non-numeric/exceeds `max_turning_length_of_cut_mm` (reuses the code milling's own `length_of_cut` input already defined) |

`MISSING_MATERIAL`, `MISSING_TOOL`, `UNSUPPORTED_COMBINATION`, `INVALID_TARGET_RPM`,
`MODE_CONFLICT`, and `INFEASIBLE_POWER_BUDGET` are reused verbatim from drilling, unchanged.

## Identical-results guarantee (FR-016)

The console interface and the library MUST produce identical `CalculationResult` values
for identical inputs (including identical `mode`/`target_rpm`/`available_power`
selections) — the console's turning prompts are purely an input-gathering step that
ultimately calls the same `calculate_turning()` function a library caller would use.
