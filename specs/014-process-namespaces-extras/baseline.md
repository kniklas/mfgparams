# Pre-Move Baseline (T001)

**Captured**: 2026-08-31, on `014-process-namespaces-extras` at commit `2cd50ca`, before any file
moved. Recorded so that FR-003 ("the reorganisation MUST NOT change any calculation input, output,
formula, or bundled reference-data value") and SC-001 are falsifiable after the restructure. T020
re-runs exactly this and diffs against it.

**Environment**: CPython 3.12.7, `pip install -e ".[dev]"`.

## Test suite

```
836 passed, 10 skipped in 10.52s
Required test coverage of 90% reached. Total coverage: 98.59%
```

Full-suite invocation: `python -m pytest -q` from the repository root (the `packaging` marker is
*not* deselected here, so this is the whole suite).

`tox` (py39-py312) and `tox -e packaging` results are recorded under [T002](#t002-multi-version-gate)
below.

## Golden calculations

Fixed inputs, metric, standard mode. The script below imports only the top-level public surface, so
the identical file runs unchanged before and after the restructure - that is the point of it.

```python
import dataclasses

import mfgparams

CASES = [
    ("drilling", mfgparams.calculate, dict(
        diameter=10.0, depth=25.0, material="Mild Steel", tool="HSS")),
    ("end_milling", mfgparams.calculate_end_milling, dict(
        diameter=12.0, axial_depth_of_cut=3.0, radial_depth_of_cut=6.0,
        feed_per_tooth=0.05, number_of_teeth=4, length_of_cut=100.0,
        material="Mild Steel", tool="Carbide")),
    ("face_milling", mfgparams.calculate_face_milling, dict(
        diameter=50.0, axial_depth_of_cut=2.0, width_of_cut=40.0,
        feed_per_tooth=0.15, number_of_teeth=5, length_of_cut=200.0,
        material="Aluminum", tool="Coated Carbide")),
]

for name, fn, kwargs in CASES:
    result = fn(**kwargs)
    print(f"[{name}] {kwargs}")
    for field in dataclasses.fields(result):
        print(f"    {field.name} = {getattr(result, field.name)!r}")
    print()
```

Values are `repr()` of the raw floats, not rounded, so a one-ulp drift is visible.

### drilling

`diameter=10.0, depth=25.0, material="Mild Steel", tool="HSS"`

| Field | Value |
|---|---|
| `spindle_speed_rpm` | `795.7747154594767` |
| `feed_rate` | `159.15494309189535` |
| `machining_time` | `0.1759291886010284` |
| `torque` | `9.5` |
| `power_required` | `0.7916083556926732` |
| `unit_system` | `UnitSystem.METRIC` |
| `feasibility_warning` | `None` |
| `error` | `None` |
| `mode` | `CalculationMode.STANDARD` |
| `material_removal_rate` | `None` |

### end milling

`diameter=12.0, axial_depth_of_cut=3.0, radial_depth_of_cut=6.0, feed_per_tooth=0.05,
number_of_teeth=4, length_of_cut=100.0, material="Mild Steel", tool="Carbide"`

| Field | Value |
|---|---|
| `spindle_speed_rpm` | `1657.8639905405764` |
| `feed_rate` | `331.5727981081153` |
| `machining_time` | `0.30159289474462014` |
| `torque` | `1.0887` |
| `power_required` | `0.1889964949216257` |
| `unit_system` | `UnitSystem.METRIC` |
| `feasibility_warning` | `None` |
| `error` | `None` |
| `mode` | `CalculationMode.STANDARD` |
| `material_removal_rate` | `5.968310365946075` |

### face milling

`diameter=50.0, axial_depth_of_cut=2.0, width_of_cut=40.0, feed_per_tooth=0.15,
number_of_teeth=5, length_of_cut=200.0, material="Aluminum", tool="Coated Carbide"`

| Field | Value |
|---|---|
| `spindle_speed_rpm` | `1145.9155902616465` |
| `feed_rate` | `859.4366926962348` |
| `machining_time` | `0.23271056693257727` |
| `torque` | `6.6850000000000005` |
| `power_required` | `0.8021409131831525` |
| `unit_system` | `UnitSystem.METRIC` |
| `feasibility_warning` | `None` |
| `error` | `None` |
| `mode` | `CalculationMode.STANDARD` |
| `material_removal_rate` | `68.75493541569878` |

## T002: multi-version gate

Both run on the unmodified tree, 2026-08-31:

```
tox            py39: OK | py310: OK | py311: SKIP | py312: OK   (exit 0)
               834 passed, 10 skipped, 2 deselected   (`-m "not packaging"`)
               Total coverage: 98.59%
tox -e packaging   OK   2 passed, 844 deselected
```

**`py311: SKIP` is a local-environment artefact, not a gap.** This machine's pyenv does not expose a
`python3.11` shim, and `tox.ini` sets `skip_missing_interpreters = true`. CI's `test` job runs the
3.11 leg, so 3.11 coverage is unaffected; only the local pre-move confirmation is one interpreter
short. The three interpreters that did run all report the same counts, so there is no
version-specific behaviour for the move to disturb.

The counts differ from the full-suite run above by exactly the two `packaging`-marked tests
(836 = 834 + 2), which `tox` deselects and `tox -e packaging` runs on their own.
