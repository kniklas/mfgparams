# Quickstart: Turning Combined-Constraint Modes & Machining Menu Auto-Hide

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving this feature works end-to-end, once implemented.
Assumes the same setup as `specs/019-turning-calculations/quickstart.md`
(editable install, `pytest` available); not repeated here.

## Prerequisites

```bash
pip install -e ".[console,dev]"
```

## Scenario 1 — Rotation-and-feed-constrained mode (User Story 1)

```bash
python -c "
import math
from mfgparams import calculate_turning, CalculationMode, UnitSystem

standard = calculate_turning(
    diameter=40.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', unit_system=UnitSystem.METRIC,
)
result = calculate_turning(
    diameter=40.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', unit_system=UnitSystem.METRIC,
    mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
    target_rpm=900, target_feed_rate=0.3,
)
print(result.spindle_speed_rpm, result.feed_per_rotation, result.machining_time)
assert result.error is None
assert result.spindle_speed_rpm == 900
assert result.feed_per_rotation == 0.3
# Neither value matches standard mode's derived values -- confirms neither is derived.
assert not math.isclose(result.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
assert not math.isclose(result.feed_per_rotation, standard.feed_per_rotation, rel_tol=1e-9)
"
```

**Expected**: `spindle_speed_rpm` equals the supplied `900` exactly;
`feed_per_rotation` equals the supplied `0.3` exactly; both differ from
standard mode's derived values for the same inputs — confirms FR-001/SC-001/SC-003.

## Scenario 2 — Rotation-and-feed-constrained mode requires both values (User Story 1 edge case)

```bash
python -c "
from mfgparams import calculate_turning, CalculationMode

# Only target_rpm supplied, target_feed_rate missing.
result = calculate_turning(
    diameter=40.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide',
    mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED, target_rpm=900,
)
print(result.error.code)
assert result.error is not None
assert result.error.code == 'INVALID_TARGET_FEED_RATE'
assert result.spindle_speed_rpm is None
"
```

**Expected**: a structured `INVALID_TARGET_FEED_RATE` error, no calculation
performed — confirms FR-002.

## Scenario 3 — Power-and-feed-constrained mode (User Story 2)

```bash
python -c "
from mfgparams import calculate_turning, CalculationMode, UnitSystem

result = calculate_turning(
    diameter=40.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide', unit_system=UnitSystem.METRIC,
    mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
    available_power=0.5, target_feed_rate=0.3,
)
print(result.spindle_speed_rpm, result.power_required, result.feed_per_rotation)
assert result.error is None
assert result.feed_per_rotation == 0.3
assert result.power_required <= 0.5 or abs(result.power_required - 0.5) < 1e-6
"
```

**Expected**: `feed_per_rotation` equals the supplied `0.3` exactly;
`power_required` is at or within the supplied `0.5` kW budget; `spindle_speed_rpm`
is solved to the highest value feasible at that feed and budget, but never above
the cutting-speed-derived reference speed standard mode uses at that feed (a
surplus budget alone never raises the result past that reference speed) —
confirms FR-003/SC-002.

## Scenario 4 — Power-and-feed-constrained mode: infeasible budget (User Story 2 edge case)

```bash
python -c "
from mfgparams import calculate_turning, CalculationMode

result = calculate_turning(
    diameter=40.0, depth_of_cut=2.0, length_of_cut=100.0,
    material='Mild Steel', tool='Carbide',
    mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
    available_power=0, target_feed_rate=0.3,
)
print(result.error.code)
assert result.error is not None
assert result.error.code == 'INFEASIBLE_POWER_BUDGET'
"
```

**Expected**: a structured `INFEASIBLE_POWER_BUDGET` error — confirms FR-005.

## Scenario 5 — Both new modes are rejected for drilling and milling (FR-010)

```bash
python -c "
from mfgparams import calculate, calculate_end_milling, CalculationMode

for fn, kwargs in [
    (calculate, dict(diameter=10, depth=25, material='Mild Steel', tool='Carbide')),
    (calculate_end_milling, dict(
        diameter=10, axial_depth_of_cut=2, radial_depth_of_cut=5,
        feed_per_tooth=0.05, number_of_teeth=4, length_of_cut=100,
        material='Mild Steel', tool='Carbide',
    )),
]:
    for mode in (CalculationMode.ROTATION_AND_FEED_CONSTRAINED, CalculationMode.POWER_AND_FEED_CONSTRAINED):
        result = fn(**kwargs, mode=mode)
        assert result.error is not None, (fn, mode)
        assert result.error.code == 'UNSUPPORTED_MODE', (fn, mode, result.error.code)
print('ok')
"
```

**Expected**: both new modes are rejected with `UNSUPPORTED_MODE` for both
drilling and milling — confirms FR-010, extended from the same guard `020`
established for `FEED_RATE_CONSTRAINED`.

## Scenario 6 — Console TUI: Machining menu hides during an operation, all three operations (User Story 3)

```bash
python -c "
from _tui_test_support import run_headless
import mfgparams.console.tui.app as app_mod
from mfgparams.console.i18n import get_locale
from mfgparams.i18n import get_raw_locale

locale = get_locale()
display_locale = get_raw_locale()
holder = {}

def target():
    app, ui, view = app_mod.build_app(None, locale, display_locale)
    holder['ui'] = ui
    holder['view'] = view
    app.run()

snapshots = []
def on_batch():
    ui, view = holder.get('ui'), holder.get('view')
    if ui is None:
        return
    snapshots.append((view.body_mode, ui.tree.expanded, ui.open_operation is not None))

# m: expand Machining, focus tree (row 0 = Milling); Enter: open Milling;
# then close Milling, close the tree, and exit -- run_headless drives the
# real Application and needs it to actually terminate (matching every
# real test's key-batch shape, e.g. test_tui_navigation.py's own).
run_headless(target, ['m', '\r', '\x1b', '\x1b', '\x1b'], on_batch=on_batch)
after_opening = snapshots[2]
assert after_opening == (None, True, True), after_opening  # menu hidden while open
"
```

(Run from the `tests/integration/` directory, or with it on `sys.path`, since
`_tui_test_support` lives there — mirrors how `test_tui_navigation.py` imports it.)

**Expected**: once Milling's floating window is open, `body_mode` is `None`
(the Machining tree is hidden) while `tree.expanded` stays `True` and
`open_operation` is not `None` — confirms FR-011. Repeating with `'j'`
(Drilling) or `'j', 'j'` navigation to Turning's row (row 0 is Milling;
`'k'` at row 0 closes the Machining menu outright via `_tree_up` rather
than navigating within it, so it cannot be used to reach Turning from the
top), followed by `'\r'`, produces the identical result — confirms
FR-013's symmetry. Escaping (`'\x1b'`) afterward restores
`body_mode == "tree"` — confirms FR-012 (see
`contracts/tui-machining-menu-auto-hide-delta.md`'s own example for the full
open→escape sequence).

## Full validation

```bash
pytest tests/unit/processes/machining/turning/test_formulas_power_and_feed_constrained.py \
       tests/contract/test_library_api_turning_rotation_and_feed_constrained.py \
       tests/contract/test_library_api_turning_rotation_and_feed_constrained_errors.py \
       tests/contract/test_library_api_turning_power_and_feed_constrained.py \
       tests/contract/test_library_api_turning_power_and_feed_constrained_errors.py \
       tests/contract/test_mode_conflict.py \
       tests/contract/test_milling_mode_conflict.py \
       tests/integration/test_tui_turning.py \
       tests/integration/test_tui_navigation.py \
       -v
```

All scenarios above should pass, alongside the full existing suite
(`pytest`) staying green — this feature changes no existing mode's behavior
(spec.md Assumptions).
