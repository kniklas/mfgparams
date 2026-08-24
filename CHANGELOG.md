# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `validate_diameter_mm()`/`validate_depth_mm()` no longer let a `NaN`
  drill diameter or hole depth pass validation (issue #56). Both checks
  (`value <= 0` and `value > maximum`) are `False` for `NaN`, so a `NaN`
  silently reached the calculation and produced a `NaN`-poisoned
  `CalculationResult` with `error=None` instead of a structured
  `INVALID_DIAMETER`/`INVALID_DEPTH` error. In the interactive CLI, the
  literal `nan` — which `_prompt_number()` parses successfully via
  `float("nan")` — was accepted at the "Drill diameter"/"Hole depth"
  prompt rather than being re-prompted.
- Both validators now route through the module's existing
  `_is_positive_finite_number()` guard, the same one every milling
  validator already used — and the same validation posture
  `validate_target_rpm()` applies via its own equivalent inline
  type/finiteness checks — so a non-numeric value returns an `ErrorInfo`
  instead of raising `TypeError` from the bound comparison, per the
  never-raises contract (FR-015). As a
  consequence, `+inf`/`-inf` (already rejected before, via two different
  checks) now report the "must be greater than 0" message rather than
  "must not exceed <max> mm", matching milling's wording for the same
  input, and a `bool` is no longer accepted as a 1 mm diameter.
- `_is_positive_finite_number()` no longer raises `OverflowError` for an
  enormous `int` such as `10**1000`. `math.isfinite()` coerces its
  argument to a C double, so it raised instead of answering; `int` is now
  short-circuited as inherently finite and the value is rejected by the
  caller's exact bound comparison. `units.to_metric_length()` catches the
  same overflow from the inch-to-mm multiplication. This also fixes the
  **milling** validators, which shared the helper and raised
  `OverflowError` for such an input before this release.
- Drilling's imperial path no longer raises `TypeError` for a non-numeric
  `diameter`/`depth`. `calculate(..., unit_system=UnitSystem.IMPERIAL)`
  converted lengths with a bare `in_to_mm()` *before* validation, so
  `diameter="abc"` raised from the inch-to-mm multiplication rather than
  returning `INVALID_DIAMETER`. Both operations now share
  `units.to_metric_length()`, which passes non-numeric and `bool` values
  through unconverted so the validators reject them — the guard milling
  already applied privately as `_to_metric()`.

## [0.4.0]

### Added

- **Milling calculation modes** (specs/010-milling-calculation-modes):
  `calculate_end_milling()` and `calculate_face_milling()` now accept the
  same `mode`/`target_rpm` parameters as drilling's `calculate()`,
  supporting **power-constrained** (reduce spindle speed/feed rate to fit
  a supplied available power budget) and **fixed-RPM** (derive feed rate,
  machining time, torque, material removal rate, and required power from
  a user-specified spindle RPM) calculation modes, in addition to the
  existing standard mode.
- The interactive CLI's milling flow now asks for a calculation mode
  (`standard`, `power-constrained`, `fixed-rpm`) immediately after the
  unit-system prompt, mirroring drilling's existing mode-selection
  prompt position; the chosen mode determines whether the available-power
  prompt is optional/advisory or required, and whether a target-RPM
  prompt is shown.
- Both new modes reuse drilling's existing `CalculationMode` enum,
  validators, and error codes (`INFEASIBLE_POWER_BUDGET`,
  `INVALID_TARGET_RPM`, `MODE_CONFLICT`) verbatim. Two new error codes are
  introduced for milling-specific edge cases: `INVALID_AVAILABLE_POWER`
  (a non-numeric, non-finite, or non-positive `available_power` supplied
  as the optional advisory value in **standard** or **fixed-RPM** mode)
  and `CALCULATION_OVERFLOW` (an otherwise-valid extreme input that
  overflows an intermediate calculation). An invalid `available_power` in
  **power-constrained** mode, where it is a required hard budget rather
  than advisory, is reported as `INFEASIBLE_POWER_BUDGET` instead, since
  no spindle speed could ever meet it.

### Unchanged

- Standard (unconstrained) milling calculations that omit `mode`/
  `target_rpm` behave identically to `009-milling-calculations` (no
  regression).

## [0.3.0]

### Added

- **Milling calculations** (specs/009-milling-calculations): new public
  entry points `calculate_end_milling()` and `calculate_face_milling()`,
  with their own bundled tool catalogs exposed via `list_end_mill_tools()`
  and `list_face_mill_tools()`. Both report spindle speed, feed rate,
  machining time, torque, required power and **material removal rate**,
  in metric or imperial units.
- New `MachiningOperation` and `MillingSubOperation` enums, and
  `CalculationResult.material_removal_rate` (cm3/min metric, in3/min
  imperial). Drilling results always leave this field `None`.
- The interactive CLI now asks which machining operation to calculate
  before anything else, and which milling sub-operation when `milling` is
  chosen. Each operation keeps its own remembered defaults across repeat
  calculations.
- New milling configuration bounds — `max_mill_diameter_mm` (200.0),
  `max_depth_of_cut_mm` (50.0, applied to both axial depth and radial/width
  engagement) and `max_length_of_cut_mm` (1000.0) — plus the matching
  validation errors and message-catalog entries.

### Changed

- The package version now has a single source of truth (Constitution IV):
  `pyproject.toml` declares `dynamic = ["version"]` and reads
  `machine_calc.__version__`, replacing the previously duplicated (and
  divergent) declarations.
- Milling reports "milling tool" wording in its missing/unknown-tool errors
  (`error.missing_mill_tool`, `error.unknown_mill_tool`) rather than reusing
  drilling's wording.

### Unchanged

- Drilling behaviour is byte-for-byte identical apart from the new leading
  operation prompt, enforced by a golden-transcript contract test captured
  from the pre-refactor CLI.

## [0.2.0] - 2026-08-11

### Added

- Built-in wood workpiece materials (specs/007-wood-materials-support):
  hardwoods **Oak, Maple**; softwoods **Pine, Spruce, Fir**; engineered
  woods **Plywood, MDF** (one generic entry per type). Reference values are
  derived as the median of multiple authoritative sources (Machinery's
  Handbook, CNC machining guides, ISO/industry standards); see
  `specs/007-wood-materials-support/research.md` §7 for citations.
- `WorkpieceMaterial.is_usable` property and
  `machine_calc.registry.get_material_validation()` to inspect load-time
  validation status of a registered material before using its numeric
  fields.
- New translated error code `UNUSABLE_MATERIAL` returned by `calculate()`
  when a selected material was registered with invalid parameters.

### Changed

- **Behavior change (FR-008, warn-and-continue):** invalid material entries
  in a user-supplied `--materials-config` file (missing, non-numeric,
  non-finite, or non-positive cutting speed / feed / specific cutting
  force) no longer abort CLI startup with a fatal `RegistryConfigError`.
  The entry is registered, a warning is logged identifying the source file
  and issue, and startup/listing continues; calculations that select such
  an entry fail safely with the `UNUSABLE_MATERIAL` error instead of
  computing a wrong number. Malformed TOML and duplicate names within one
  file remain fatal errors.
- Registry snapshots for user-supplied config paths are now cached per
  path for the lifetime of the process (previously re-read on each
  lookup); edit-and-reload of a config file requires restarting the CLI.

## [0.1.0]

- Initial release: metric/imperial drilling calculations, constrained
  calculation modes, configurable materials/tools via TOML, i18n message
  catalog, CI quality/security gates.
