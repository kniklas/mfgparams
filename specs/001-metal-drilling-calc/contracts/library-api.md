# Contract: Library API

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This is the public contract exposed by the `machine_calc` library
(FR-001, FR-015, FR-016), consumable independent of the CLI.

## Public surface

```python
from machine_calc import calculate, list_materials, list_tools, UnitSystem
```

Internally, `calculate()` is implemented in `machine_calc.operations.drilling` and
re-exported at the top level (`machine_calc/__init__.py`) since drilling is
currently the module's only operation (Constitution Principle VI, amended
2026-07-09). Future operations (e.g., turning, milling) are expected to add
their own `machine_calc.operations.<operation>` module with an analogous
`calculate()` entry point, without changing this drilling contract.

```python
def calculate(
    diameter: float,
    depth: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
) -> CalculationResult: ...

def list_materials() -> list[str]: ...
def list_tools() -> list[str]: ...
```

- `calculate(...)` MUST NOT raise for expected validation failures (invalid
  input, missing/unknown material or tool, unsupported combination, exceeded
  power rating). It MUST always return a `CalculationResult` (data-model.md).
- `calculate(...)` MAY raise only for genuinely unexpected/programmer errors
  (e.g., malformed `config_path` file that cannot be parsed at all) — these
  are not "expected validation failures" under FR-015 and are out of scope
  for the structured-error contract.
- `list_materials()` / `list_tools()` return the currently registered names,
  supporting FR-004/FR-005 and enabling calling programs to build their own
  selection UI (User Story 2).

## Success response contract

```python
CalculationResult(
    spindle_speed_rpm=1350.5,
    feed_rate=54.2,
    machining_time=0.42,
    torque=3.1,
    power_required=0.44,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,   # or a string if available_power exceeded
    error=None,
)
```

## Error response contract

```python
CalculationResult(
    spindle_speed_rpm=None,
    feed_rate=None,
    machining_time=None,
    torque=None,
    power_required=None,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    error=ErrorInfo(code="INVALID_DIAMETER", message="Drill diameter must be greater than 0."),
)
```

### Error codes (FR-009, FR-010, FR-018)

| Code | Trigger |
|---|---|
| `INVALID_DIAMETER` | Diameter is zero, negative, non-numeric, non-finite (`NaN`/`Infinity`), or exceeds the configured maximum |
| `INVALID_DEPTH` | Depth is zero, negative, non-numeric, non-finite (`NaN`/`Infinity`), or exceeds the configured maximum |
| `MISSING_MATERIAL` | No material supplied |
| `MISSING_TOOL` | No drilling tool supplied |
| `UNSUPPORTED_COMBINATION` | Material/tool pairing has no defined reference parameters |

### Feasibility warning (not an error)

When `available_power` is supplied and `power_required` exceeds it, the
result is still a success (`error=None`) with `feasibility_warning` set to a
human-readable message (FR-012). This is distinct from `error` because the
calculation itself succeeded — only the feasibility check produced a
caution.

## Identical-results contract (FR-016)

For any given `(diameter, depth, material, tool, unit_system,
available_power)` tuple, `calculate(...)` MUST return the same
`CalculationResult` values whether invoked directly (User Story 2) or via the
CLI's underlying calls (User Story 1). The CLI MUST NOT contain any
calculation logic of its own — it only collects inputs and formats this
same `CalculationResult` for display.

## Unit labeling contract (FR-013)

`CalculationResult` field names are unit-agnostic by design (e.g., `torque`,
not `torque_nm`) so the schema does not change shape across unit systems; the
`unit_system` field on every result indicates which units apply. To satisfy
FR-013's "clearly labeled" requirement for library consumers (not just the
CLI display), the public docstring for `calculate()` and the generated Sphinx
API reference (Constitution Principle VII) MUST enumerate, for each field,
the exact unit used under `UnitSystem.METRIC` and `UnitSystem.IMPERIAL`
respectively (per Constitution Principle I's documentation requirement).

## Localization contract (FR-019)

`calculate()` accepts an optional `locale` parameter (default `"en"`; an
empty string is treated the same as omitting it) that selects the message
catalog used to populate `ErrorInfo.message` and `feasibility_warning` text.
Falls back to English for any locale or message key not present in the
requested catalog — this MUST NOT raise an error or return a blank/missing
message. If a catalog string requires a placeholder value that is missing at
lookup time, the returned message MUST still be a usable string (FR-019b);
this MUST NOT raise an exception to the caller. This is the same catalog
used by the CLI's `i18n.py`-driven prompts (see contracts/cli-repl.md).
