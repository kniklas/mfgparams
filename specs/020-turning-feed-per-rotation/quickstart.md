# Quickstart: Turning Feed Rate Per Rotation & Constrained Mode

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving this feature works end-to-end, once implemented.
Assumes the same setup as `specs/019-turning-calculations/quickstart.md`
(editable install, `pytest` available); not repeated here.

## Prerequisites

```bash
pip install -e ".[console,dev]"
```

## Scenario 1 — Every turning mode reports feed-per-rotation (User Story 1)

```bash
python -c "
import math
from mfgparams import calculate_turning, UnitSystem

result = calculate_turning(
    diameter=50.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', unit_system=UnitSystem.METRIC,
)
print(result.feed_rate, result.feed_per_rotation)
assert result.error is None
assert result.feed_per_rotation is not None
assert math.isclose(result.feed_per_rotation * result.spindle_speed_rpm, result.feed_rate, rel_tol=1e-9)
"
```

**Expected**: `feed_per_rotation` is populated (mm/rev), `feed_rate` is
unchanged from what `019-turning-calculations` already produced for these
inputs (mm/min) — confirms FR-001/FR-002/SC-001/SC-005.

Repeat with `mode=CalculationMode.FIXED_RPM, target_rpm=900` and
`mode=CalculationMode.POWER_CONSTRAINED, available_power=1.0` — both should
also return a populated `feed_per_rotation`, consistent with standard mode's.

## Scenario 2 — Feed-rate-constrained mode (User Story 2)

```bash
python -c "
from mfgparams import calculate_turning, CalculationMode, UnitSystem

result = calculate_turning(
    diameter=50.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', unit_system=UnitSystem.METRIC,
    mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=0.3,
)
print(result.feed_per_rotation, result.spindle_speed_rpm, result.cutting_force)
assert result.error is None
assert result.feed_per_rotation == 0.3
assert result.mode is CalculationMode.FEED_RATE_CONSTRAINED
"
```

**Expected**: `feed_per_rotation` equals the supplied `0.3` exactly;
`spindle_speed_rpm` matches the standard-mode value for the same
diameter/material/tool (Scenario 1's result); `cutting_force`/`torque`/
`power_required` differ from Scenario 1's (they depend on feed per
revolution) — confirms FR-004/FR-005/SC-002/SC-003.

**Error cases** (confirms FR-006/FR-007):

```bash
python -c "
from mfgparams import calculate_turning, CalculationMode, UnitSystem

# Missing target_feed_rate
r = calculate_turning(diameter=50.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', mode=CalculationMode.FEED_RATE_CONSTRAINED)
assert r.error.code == 'INVALID_TARGET_FEED_RATE'

# Zero/negative
r = calculate_turning(diameter=50.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', mode=CalculationMode.FEED_RATE_CONSTRAINED,
    target_feed_rate=-0.1)
assert r.error.code == 'INVALID_TARGET_FEED_RATE'

# Conflicting with target_rpm
r = calculate_turning(diameter=50.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', mode=CalculationMode.FEED_RATE_CONSTRAINED,
    target_feed_rate=0.3, target_rpm=900)
assert r.error.code == 'MODE_CONFLICT'
"
```

## Scenario 3 — TUI arrow-key nudge (User Story 3)

Manual/integration-test scenario (mirrors
`019-turning-calculations/quickstart.md`'s TUI section):

1. Launch the console (`mfgparams` or the project's documented entry point),
   open Machining → Turning.
2. Select material, tool, diameter, depth of cut, length of cut.
3. Set Mode to **feed-rate-constrained** — a new "Feed rate per rotation"
   field appears (required), and the Target spindle speed field (if it was
   showing) disappears.
4. Select the Feed rate per rotation field. Press Right arrow once: value
   goes from unset/`0` to `0.1` (METRIC) — not `1.0`, confirming the
   field-specific nudge step (FR-011). Press Right three more times: `0.4`.
   Press Left once: `0.3`.
5. Switch Unit system to Imperial: the field's value converts (mm → in) via
   the same conversion diameter/depth already use, not silently relabeled
   (FR-012). Press Right once: value increases by `0.005` (in), not `0.1`.
6. Complete the remaining required fields; the result panel shows a new
   "Feed per rotation" line, immediately after "Feed rate", matching the
   entered value.

**Expected**: Steps 4-5 are the concrete, testable form of SC-004; step 6
confirms the result panel change from the CLI/TUI contract delta.

## Regression check (SC-005)

```bash
pytest tests/contract/test_library_api_turning.py tests/contract/test_library_api_turning_fixed_rpm.py tests/contract/test_library_api_turning_power_constrained.py -q
```

**Expected**: All pre-existing turning tests continue to pass unmodified in
their assertions on `feed_rate`, `spindle_speed_rpm`, `machining_time`,
`torque`, `power_required`, and `cutting_force` — only new assertions on
`feed_per_rotation` are additive to these suites (or added as new sibling
test files), never replacing an existing assertion's expected value.
