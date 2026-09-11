# Phase 1 Data Model: Turning Calculations Module

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This document defines the entities backing the turning calculation engine, derived from
the spec's Key Entities section and this feature's requirements. It reuses
`WorkpieceMaterial`, `UnitSystem`, `CalculationMode`, and `ErrorInfo` unchanged from
`specs/001-metal-drilling-calc/data-model.md` and
`specs/002-constrained-calculation-modes/data-model.md`; only the entities new or changed
by this feature are defined here.

## WorkpieceMaterial (reused, unchanged)

See `specs/001-metal-drilling-calc/data-model.md`. Turning uses
`reference_cutting_speed_m_min`, `reference_feed_per_rev_mm`, and
`specific_cutting_force_kc` exactly as drilling does (research.md #1) — no new field, no
turning-specific material list (FR-004).

## TurningTool

Reference data for a selectable single-point turning tool type (FR-005), e.g., high-speed
steel, cobalt, carbide — structurally identical to `DrillingTool`.

| Field | Type | Notes |
|---|---|---|
| `name` | str | Unique identifier/display name (e.g., "Carbide") |
| `cutting_speed_factor` | float | Multiplier applied to the material's reference cutting speed |
| `feed_factor` | float | Multiplier applied to the material's reference feed per revolution |

Validation: `name` unique within the turning tool registry; factors MUST be positive.

## MaterialToolCompatibility (registry relationship, reused pattern)

Same rule as drilling's (FR-011 of this feature): a (`WorkpieceMaterial`, `TurningTool`)
pairing with no defined reference parameters is rejected with
`error_code=UNSUPPORTED_COMBINATION`, performing no calculation. As with drilling's initial
release, every material x tool combination seeded in `turning/data/tools.toml` is defined;
the rejection path exists for forward-compatibility as the registries grow.

## CalculationMode (enum, reused — extended usage, not extended definition)

`STANDARD`, `FIXED_RPM`, `POWER_CONSTRAINED` (`src/mfgparams/models.py`, unchanged
definition). Turning is simply a new caller of the existing enum (FR-012); no new mode is
introduced.

## TurningOperation (request)

Represents a single calculation request (FR-003).

| Field | Type | Notes |
|---|---|---|
| `diameter` | float | Workpiece diameter, in the units of the selected `unit_system` |
| `depth_of_cut` | float | Radial depth of cut per pass (`ap`), in the units of the selected `unit_system` — new input this feature introduces (research.md #3) |
| `length_of_cut` | float | Length of the turning pass (`lm`), in the units of the selected `unit_system` — named to match milling's existing `length_of_cut` input, not a turning-only "cut length" term (see Validation below) |
| `material` | str (→ WorkpieceMaterial name) | Required (FR-011) |
| `tool` | str (→ TurningTool name) | Required (FR-011) |
| `unit_system` | UnitSystem | Required (FR-017) |
| `mode` | CalculationMode | Defaults to `STANDARD` (FR-012) |
| `target_rpm` | float \| None | Required when `mode == FIXED_RPM`; rejected otherwise |
| `available_power` | float \| None | Optional in `STANDARD`/`FIXED_RPM` (FR-014); required in `POWER_CONSTRAINED` (FR-013) |

Validation (FR-010) — following the established **per-operation validator function +
per-operation `Configuration` bound field** pattern exactly (verified against
`src/mfgparams/validation.py`/`config.py`: drilling's `validate_diameter_mm`/
`max_diameter_mm` and milling's `validate_mill_diameter_mm`/`max_mill_diameter_mm` are
two distinct functions and two distinct config fields sharing only the `INVALID_DIAMETER`
code — not one shared function/bound.  Turning follows the same shape rather than
attempting to share milling's `max_depth_of_cut_mm` (default 50 mm — too permissive for a
single-point turning tool's realistic depth of cut) or inventing a new error code where
an existing one already fits):

- **New** `validate_turning_diameter_mm(diameter_mm, config, locale)` in `validation.py`,
  mirroring `validate_mill_diameter_mm`'s shape exactly: reuses the `INVALID_DIAMETER`
  code, checks a **new** `config.max_turning_diameter_mm` field (default 500 mm / 20 in),
  with its own `error.invalid_turning_diameter.zero`/`.max` catalog messages. Non-finite
  (`NaN`/`Infinity`) and non-numeric values are rejected before any bound comparison,
  mirroring drilling's issue #56 fix.
- **New** `validate_turning_depth_of_cut_mm(depth_of_cut_mm, diameter_mm, config, locale)`
  in `validation.py`: reuses the `INVALID_DEPTH_OF_CUT` code throughout (one code, three
  message templates, per `ErrorInfo.code`'s own documented "coarser than message_key"
  contract), checking, in order: positive/finite (`error.invalid_turning_depth_of_cut.zero`),
  ≤ a **new** `config.max_turning_depth_of_cut_mm` field (default 10 mm / ≈0.4 in;
  `error.invalid_turning_depth_of_cut.max`), and strictly `< diameter_mm / 2` — the
  workpiece radius (`error.invalid_turning_depth_of_cut.exceeds_radius`; spec.md Edge
  Cases; research.md #3).
- **New** `validate_turning_length_of_cut_mm(length_of_cut_mm, config, locale)` in
  `validation.py`, mirroring `validate_mill_diameter_mm`'s shape again: reuses the
  existing `INVALID_LENGTH_OF_CUT` code (already defined for milling's `length_of_cut`
  input — genuinely nothing new here except the function and bound), checking a **new**
  `config.max_turning_length_of_cut_mm` field (default 1000 mm / 40 in — the same
  *number* milling already defaults to, kept as a distinct field for the same reason
  diameter's bound is distinct per operation even where two operations' numbers happen to
  coincide).
- `material` and `tool` MUST both be present and MUST resolve to a defined registry
  combination (see MaterialToolCompatibility).
- `mode`-specific rules reuse drilling's existing `validate_mode_arguments`/
  `validate_target_rpm` shape (`specs/002-constrained-calculation-modes/data-model.md`):
  `target_rpm` required and positive iff `mode == FIXED_RPM`; `available_power` required
  and positive iff `mode == POWER_CONSTRAINED`.

## TurningMetrics (internal calculation output, canonical metric)

Mirrors `DrillingMetrics` (`src/mfgparams/processes/machining/drilling/formulas.py`) with
turning's own fields; internal to `turning/formulas.py`, converted to the public
`CalculationResult` at the orchestration layer.

| Field | Type | Notes |
|---|---|---|
| `spindle_speed_rpm` | float | RPM |
| `feed_rate_mm_min` | float | mm/min |
| `machining_time_min` | float | Minutes (fractional) |
| `cutting_force_n` | float | Newtons — `Fc = Kc * ap * fn` (research.md #1) |
| `torque_nm` | float | N*m — `Mc = Fc * (D / 2) / 1000` |
| `power_kw` | float | kW — `Pc = (Mc * n) / 9550` |

## CalculationResult (response, extended — reused across all operations)

Extends the existing shared `CalculationResult` (`src/mfgparams/models.py`) with one new
optional field, following the precedent `material_removal_rate` already set (populated for
milling, `None` for drilling):

| Field | Type | Notes |
|---|---|---|
| `cutting_force` | float \| None | **NEW.** Newtons under METRIC, lbf under IMPERIAL. Populated for turning; `None` for drilling and milling (research.md #4). |

All other `CalculationResult` fields (`spindle_speed_rpm`, `feed_rate`, `machining_time`,
`torque`, `power_required`, `unit_system`, `error`) are reused unchanged: turning populates
`torque` and `power_required` exactly as drilling/milling do, in addition to the new
`cutting_force` field.

## ErrorInfo (reused, unchanged) — no new error codes

Zero genuinely new `error_code` values are introduced by this feature. Every validation
failure turning can produce reuses an existing code — `INVALID_DIAMETER`,
`INVALID_DEPTH_OF_CUT` (including its new exceeds-workpiece-radius message, per
`ErrorInfo.code`'s own documented "one code, multiple message templates" contract —
`src/mfgparams/models.py`), `INVALID_LENGTH_OF_CUT`, `MISSING_MATERIAL`, `MISSING_TOOL`,
`UNSUPPORTED_COMBINATION`, `INVALID_TARGET_RPM`, `MODE_CONFLICT`, and
`INFEASIBLE_POWER_BUDGET` — all reused verbatim from drilling's/milling's existing
`ErrorInfo` codes (`src/mfgparams/validation.py`). What is new is three *functions* and
three *config bounds* (see Configuration below), not new error vocabulary.

## Configuration (reused, extended)

Three new `Configuration` fields (`src/mfgparams/config.py`), following the exact
per-operation-bound precedent `max_mill_diameter_mm` already set alongside drilling's
`max_diameter_mm`:

| Field | Default | Notes |
|---|---|---|
| `max_turning_diameter_mm` | 500.0 (≈20 in) | Read by `validate_turning_diameter_mm` |
| `max_turning_depth_of_cut_mm` | 10.0 (≈0.4 in) | Read by `validate_turning_depth_of_cut_mm` |
| `max_turning_length_of_cut_mm` | 1000.0 (≈40 in) | Read by `validate_turning_length_of_cut_mm` |

All three are overridable via the existing external configuration file mechanism
(`specs/001-metal-drilling-calc` FR-018), parsed the same way `max_mill_diameter_mm` etc.
already are (`Configuration.from_file`/equivalent in `config.py`). Turning's bundled tool
reference data (`turning/data/tools.toml`) follows the materials/tools config file
addendum pattern (`specs/009-milling-calculations/contracts/milling-tools-config-schema.md`)
for a new `[[turning_tools]]` section, isolated from `tools`/`end_mill_tools`/
`face_mill_tools` the same way those are isolated from each other — each operation's own
`tools.py` module passes its own `table_key` string directly to the existing generic
`registry_config.build_registry(...)`/`load_registry_entries(...)` helpers; there is no
separate central place where a new `table_key` must be "registered" (verified against
`src/mfgparams/registry_config.py` and `drilling/tools.py`/`milling/end_milling/tools.py`).
