# Pre-Change Baseline (T001)

Captured 2026-09-04, before any change in this feature, on `pip install -e ".[console,dev]"`.

## Test suite

```
1029 passed, 10 skipped in 12.45s
Required test coverage of 90% reached. Total coverage: 99.30%
```

## `src/mfgparams/locales/en.py` `MESSAGES` — full key inventory (93 keys)

**60 keys to move** to `src/mfgparams/console/locales/en.py` (every `cli.*`/`material_type.*` key):

```
cli.prompt.unit_system, cli.prompt.unit_system.invalid, cli.unit_system.metric,
cli.unit_system.imperial, cli.prompt.choice, cli.prompt.choice.invalid, cli.prompt.number,
cli.prompt.number.invalid, cli.prompt.suffix.with_default, cli.prompt.suffix.no_default,
cli.prompt.power.suffix, cli.prompt.power.default_clause, cli.prompt.power.invalid,
cli.label.diameter, cli.label.depth, cli.label.power, cli.label.material, cli.label.tool,
cli.label.material_type, material_type.metal, material_type.wood, material_type.uncategorized,
cli.prompt.run_again, cli.result.error, cli.result.spindle_speed,
cli.result.spindle_speed.mode_suffix, cli.result.spindle_speed.mode.standard,
cli.result.spindle_speed.mode.power_constrained, cli.result.spindle_speed.mode.fixed_rpm,
cli.result.feed_rate, cli.result.machining_time, cli.result.torque, cli.result.power_required,
cli.result.warning, cli.label.mode, cli.mode.standard, cli.mode.power_constrained,
cli.mode.fixed_rpm, cli.label.power_required, cli.prompt.power_required.invalid,
cli.label.target_rpm, cli.prompt.target_rpm.invalid, cli.label.unit_system_suffix,
cli.label.operation, cli.operation.drilling, cli.operation.milling,
cli.label.milling_sub_operation, cli.milling_sub_operation.end_milling,
cli.milling_sub_operation.face_milling, cli.label.mill_diameter, cli.label.end_mill_tool,
cli.label.face_mill_tool, cli.label.axial_depth_of_cut, cli.label.radial_depth_of_cut,
cli.label.width_of_cut, cli.label.feed_per_tooth, cli.label.number_of_teeth,
cli.label.length_of_cut, cli.prompt.number_of_teeth.unit, cli.result.material_removal_rate
```

**33 keys stay in core** (`error.*`, `warning.*`, `notice.*`, `console.missing_dependency*`):

```
console.missing_dependency, console.missing_dependency.unnamed, error.invalid_diameter.zero,
error.invalid_diameter.max, error.invalid_depth.zero, error.invalid_depth.max,
error.missing_material, error.missing_tool, error.unknown_material, error.unknown_tool,
error.unusable_material, error.invalid_target_rpm, error.mode_conflict,
error.infeasible_power_budget, error.invalid_available_power, error.calculation_overflow,
warning.feasibility, notice.materials_config.not_found, error.materials_config.malformed,
error.materials_config.duplicate_entry, error.materials_config.invalid_entry,
error.invalid_mill_diameter.zero, error.invalid_mill_diameter.max,
error.invalid_depth_of_cut.zero, error.invalid_depth_of_cut.max, error.invalid_engagement,
error.invalid_feed_per_tooth, error.invalid_tooth_count, error.invalid_tooth_count.fractional,
error.invalid_length_of_cut.zero, error.invalid_length_of_cut.max, error.missing_mill_tool,
error.unknown_mill_tool
```

60 + 33 = 93, matching the pre-change total. This is the move's checklist for T006 and the
enforcement basis for T008/T009.
