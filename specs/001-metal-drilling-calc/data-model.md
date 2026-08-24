# Phase 1 Data Model: Metal Drilling Calculations Module

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This document defines the entities backing the calculation engine, derived
from the spec's Key Entities section and clarified requirements.

## WorkpieceMaterial

Reference data for a selectable workpiece material (FR-004).

| Field | Type | Notes |
|---|---|---|
| `name` | str | Unique identifier/display name (e.g., "Mild Steel") |
| `reference_cutting_speed_m_min` | float | Standard `vc` reference in m/min (canonical metric storage; converted for imperial display per FR-017) |
| `reference_feed_per_rev_mm` | float | Standard `fn` reference in mm/rev (canonical metric storage) |
| `specific_cutting_force_kc` | float | `Kc` in N/mm², used in torque/power calculations (research.md #4) |

Validation: `name` MUST be unique within the registry; all numeric fields MUST
be positive (Principle III — no silently wrong reference data).

## DrillingTool

Reference data for a selectable drill bit type (FR-005), e.g., high-speed
steel, cobalt, carbide.

| Field | Type | Notes |
|---|---|---|
| `name` | str | Unique identifier/display name (e.g., "Carbide") |
| `cutting_speed_factor` | float | Multiplier applied to the material's reference cutting speed |
| `feed_factor` | float | Multiplier applied to the material's reference feed per revolution |

Validation: `name` unique; factors MUST be positive.

## MaterialToolCompatibility (registry relationship)

Not a standalone entity but a registry-level rule (FR-010): a
(`WorkpieceMaterial`, `DrillingTool`) pairing is either defined (both factors
combine to produce a valid calculation) or undefined. Undefined pairings MUST
be rejected with a structured error (`error_code=UNSUPPORTED_COMBINATION`) —
see Configuration/error handling below. The initial release treats every
material × tool combination in the registries as defined (per spec
Assumptions); the rejection path exists for forward-compatibility as the
registries grow (Principle VI).

## UnitSystem (enum)

- `METRIC` — mm, mm/rev, RPM, kW, N·m
- `IMPERIAL` — inches, in/rev, RPM, HP, in-lb

Selected per request/session (FR-017); does not change calculation results,
only input parsing and output formatting/labels (canonical calculation is
always performed in metric internally per research.md #4, then converted for
display/output when `IMPERIAL` is selected).

## DrillingOperation (request)

Represents a single calculation request (FR-003).

| Field | Type | Notes |
|---|---|---|
| `diameter` | float | In the units of the selected `unit_system` |
| `depth` | float | In the units of the selected `unit_system` |
| `material` | str (→ WorkpieceMaterial name) | Required (FR-010) |
| `tool` | str (→ DrillingTool name) | Required (FR-010) |
| `unit_system` | UnitSystem | Required (FR-017) |
| `available_power` | float \| None | Optional (FR-012), same units as `unit_system`'s power unit |

Validation (FR-009, FR-018):
- `diameter` MUST be a finite number > 0 and ≤ configured max diameter
  (default 100 mm / 4 in). `NaN`, `Infinity` and non-numeric values are
  rejected as `INVALID_DIAMETER` before the bound is compared — every
  comparison against `NaN` is false, so a bound check alone would let it
  through (issue #56).
- `depth` MUST be a finite number > 0 and ≤ configured max depth
  (default 500 mm / 20 in), under the same non-finite/non-numeric rule.
- `material` and `tool` MUST both be present and MUST resolve to a defined
  registry combination (see MaterialToolCompatibility).

## CalculationResult (response)

Structured output returned identically by the CLI and library (FR-016),
always returned — never raised as an exception — per FR-015.

| Field | Type | Notes |
|---|---|---|
| `spindle_speed_rpm` | float \| None | RPM; `None` if calculation could not proceed |
| `feed_rate` | float \| None | Units per `unit_system` (mm/min or in/min) |
| `machining_time` | float \| None | Minutes (fractional), fixed regardless of `unit_system` per spec clarification |
| `torque` | float \| None | N·m or in-lb per `unit_system` |
| `power_required` | float \| None | kW or HP per `unit_system` |
| `unit_system` | UnitSystem | Echoes the request's unit system |
| `feasibility_warning` | str \| None | Set when `available_power` was supplied and is exceeded by `power_required` (FR-012) |
| `error` | ErrorInfo \| None | Set when validation fails or an unsupported combination is requested (FR-015); when set, the numeric fields above MUST be `None` |

**Unit-labeling resolution (FR-013, /speckit.analyze finding B1)**: Field names
(`torque`, `power_required`, etc.) intentionally stay unit-agnostic (not
suffixed like `torque_nm`) so the schema is stable across unit systems —
callers read the accompanying `unit_system` field to know which units apply.
"Clearly labeled" for the library API is satisfied by: (1) the `unit_system`
field always being present, and (2) `machine_calc`'s public docstrings and
generated Sphinx API reference explicitly documenting the exact unit for
every `CalculationResult` field under each `UnitSystem` value (Constitution
Principle I requires inputs/outputs/units to be documented). The CLI (FR-002)
additionally renders human-readable unit suffixes (e.g., "3.1 N·m") at
display time — see contracts/cli-repl.md.

## ErrorInfo

| Field | Type | Notes |
|---|---|---|
| `code` | str | Machine-readable identifier, e.g. `INVALID_DIAMETER`, `MISSING_MATERIAL`, `MISSING_TOOL`, `UNSUPPORTED_COMBINATION`, `OUT_OF_RANGE_DEPTH` |
| `message` | str | Human-readable explanation for display in the CLI |

## Configuration

Optional external settings overriding default validation bounds (FR-018).

| Field | Type | Notes |
|---|---|---|
| `max_diameter_mm` | float | Overrides default 100 mm (canonical metric storage) |
| `max_depth_mm` | float | Overrides default 500 mm (canonical metric storage) |

Loaded from an external TOML file (research.md #3, #5); when the file or a
given key is absent, the module MUST fall back to its built-in defaults
(FR-018).

## Relationships

```
Configuration ──(overrides bounds for)──▶ DrillingOperation validation
WorkpieceMaterial ──(combined with)──▶ DrillingTool ──▶ MaterialToolCompatibility
DrillingOperation ──(validated against registries + Configuration)──▶ CalculationResult
```

## State / Lifecycle

These entities are stateless value objects computed per request; there is no
persistence or state transition beyond a single calculation's lifecycle
(request in → validate → calculate → result out), consistent with the spec's
"single-user, single-session" assumption.

## Message Catalog

Represents the set of translatable user-facing strings (REPL prompts, labels,
error/warning text) keyed by a stable message ID, one catalog per supported
locale.

- `locale`: str — e.g. `"en"`; identifies which catalog is active.
- `messages`: dict[str, str] — message ID → localized string for this locale; strings MAY contain `str.format()`-style named placeholders (e.g. `{material}`) for dynamic values, populated by the caller at lookup time.
- English (`en`) is always present and used as the fallback for any locale or
  message key missing from a non-English catalog.
- Consumed by both the CLI (`cli.py`) and the library (`calculate(locale=...)`)
  for `ErrorInfo.message` and feasibility-warning text (FR-019).
- The CLI resolves its active locale exactly once at process startup (from
  `MACHINE_CALC_LOCALE`) and treats it as immutable for the remainder of that
  process's REPL loop (FR-019c). The library re-evaluates `locale` on every
  `calculate()` call, since it has no persistent session concept.
- If a placeholder value required by a catalog string is missing at lookup
  time, the lookup MUST return a usable string rather than raise (FR-019b);
  any such formatting failure is reported only via an English-language log
  entry, never surfaced as a user-facing exception.
