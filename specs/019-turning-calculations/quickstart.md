# Quickstart: Turning Calculations Module

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving the feature works end-to-end, for the library API (User
Stories 1, 2, 3) and the console text GUI (User Stories 1, 3). See
[data-model.md](./data-model.md) for entity shapes and [contracts/](./contracts/) for
exact API/error contracts.

## Prerequisites

- Existing `mfgparams` development environment (`pip install -e ".[dev]"` from repo
  root), same as every prior feature.
- No new runtime dependency is introduced by this feature.

## Scenario 1 — Standard-mode turning calculation via the library (User Story 1, 2)

```python
from mfgparams import calculate_turning, UnitSystem

result = calculate_turning(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
)

assert result.error is None
assert result.spindle_speed_rpm is not None
assert result.feed_rate is not None
assert result.machining_time is not None
assert result.torque is not None
assert result.power_required is not None
assert result.cutting_force is not None
```

**Expected outcome**: `result` contains spindle speed, feed rate, machining time, torque,
power, and cutting force, all in metric units, with `error is None`. Values are within 5%
of published reference values for 40 mm mild steel turned with a carbide tool at a 2 mm
depth of cut (SC-002) — verified by the contract test suite against a hand-computed
reference (per Constitution Principle II).

## Scenario 2 — Fixed-RPM mode (User Story 3)

```python
from mfgparams import calculate_turning, CalculationMode, UnitSystem

result = calculate_turning(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
    mode=CalculationMode.FIXED_RPM,
    target_rpm=900,
)

assert result.error is None
assert result.spindle_speed_rpm == 900
```

**Expected outcome**: the returned spindle speed is exactly the supplied `target_rpm`;
feed rate, machining time, torque, power, and cutting force are computed at that RPM
rather than one derived from cutting speed.

## Scenario 3 — Power-constrained mode (User Story 3)

```python
from mfgparams import calculate_turning, CalculationMode, UnitSystem

result = calculate_turning(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=0.5,   # kW, deliberately below the standard-mode requirement
)

assert result.error is None
assert result.power_required <= 0.5 + 1e-6
```

**Expected outcome**: the returned spindle speed is reduced below the standard-mode
nominal value so that required power fits within the 0.5 kW budget, rather than a
feasibility warning being emitted at the (infeasible) nominal speed.

## Scenario 4 — Invalid depth of cut is rejected (Edge Cases, FR-010)

```python
from mfgparams import calculate_turning, UnitSystem

result = calculate_turning(
    diameter=10,
    depth_of_cut=6,   # >= radius (5 mm) — physically impossible
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
)

assert result.error is not None
assert result.error.code == "INVALID_DEPTH_OF_CUT"
assert result.spindle_speed_rpm is None
```

**Expected outcome**: a structured error is returned (never an exception, per the
never-raises contract), and no numeric result is produced.

## Scenario 5 — Turning in the console text GUI (User Story 1)

```bash
mfgparams
```

**Expected outcome**: the Machining tree now shows three leaves — Milling, Drilling, and
Turning. Selecting Turning opens its own floating operation screen (mirroring Drilling's),
with fields for unit system, calculation mode, material type, material, turning tool,
workpiece diameter, depth of cut, length of cut, and (mode-dependent) available power or
target RPM. Once every required field holds a value, the result panel shows spindle
speed, feed rate, machining time, torque, power, and cutting force — matching Scenario 1's
library result for the same inputs (FR-016).

## Scenario 6 — Identical results across console and library (SC-005)

Enter the exact inputs from Scenario 1 into the console's Turning screen and compare the
displayed result panel against Scenario 1's `result` object field-by-field: every value
MUST match (within the same floating-point tolerance the existing drilling/milling
identical-results tests use).
