# Phase 0 Research: Turning Calculations Module

**Feature**: [spec.md](./spec.md)

No `[NEEDS CLARIFICATION]` markers remained in the Technical Context (the user's feature
description named the exact sibling processes, calculation modes, and layers to mirror),
so this phase focuses on the concrete formulas and reuse decisions needed before design.

## 1. Turning formulas and their relationship to drilling's existing formulas

**Decision**: Reuse drilling's exact formula *shape* — a spindle-speed derivation, a
feed-rate/machining-time pair, and a torque/power pair where power is linear in RPM — with
turning's own physical inputs, per the standard turning formulas published in Sandvik
Coromant's "Machining Formulas" reference and Machinery's Handbook (same class of source
already cited in `specs/001-metal-drilling-calc/research.md` #4 and
`src/mfgparams/processes/machining/drilling/formulas.py`):

- Spindle speed: `n = (vc * 1000) / (pi * D)` — identical form to drilling
  (`calculate_drilling_metrics`), using workpiece diameter `D` (mm) in place of drill
  diameter.
- Feed rate: `vf = n * fn` — identical form to drilling, using the material's reference
  feed-per-revolution `fn` (mm/rev) adjusted by the turning tool's feed factor.
- Machining time: `Tc = lm / vf` — simpler than drilling's `(depth + point-engagement
  allowance) / vf`, because turning has no drill-point geometry; see research item 2.
- Cutting force: `Fc = Kc * ap * fn` (N), using the *same* `specific_cutting_force_kc`
  (Kc, N/mm^2) field `WorkpieceMaterial` already exposes for drilling's torque formula,
  with `ap` = depth of cut (mm) — a new input this feature adds (research item 3).
- Torque: `Mc = Fc * (D / 2) / 1000` (N*m) — the spindle torque implied by the cutting
  force acting at the workpiece radius; algebraically independent of spindle speed, exactly
  like drilling's `Mc = (Kc * D^2 * fn) / 4000`.
- Power: `Pc = (Mc * n) / 9550` (kW) — byte-for-byte the same formula drilling already
  uses, because it only depends on torque and RPM being in the stated units, not on how
  torque was derived.

**Rationale**: Because turning's torque and cutting force are both independent of spindle
speed (they depend only on diameter, depth of cut, feed, and the material/tool's
reference values — never on RPM), turning's power is linear in RPM for a fixed
diameter/depth-of-cut/material/tool selection, exactly like drilling's. This means the
power-constrained mode's existing closed-form algebraic solve
(`n_adjusted = n0 * (Pavail / Pc0)`, `calculate_power_constrained_metrics`) applies to
turning unchanged in spirit — no new iterative/root-finding logic is needed, and no new
numerical-stability risk is introduced (Principle III, Principle V performance target).

**Alternatives considered**:
- *Deriving power directly from `Fc * vc` (a formula also published by Sandvik, `Pc = (vc
  * ap * fn * kc) / 60000`) instead of via torque*: algebraically equivalent (both reduce
  to the same value), but expressing it via `Mc`/`n` — as this decision does — reuses
  drilling's exact two-step formula shape and its already-tested power-constrained solve,
  so it was preferred for consistency and to minimize new, unreviewed algebra.
- *Introducing a new material reference field specific to turning*: rejected — reusing
  `WorkpieceMaterial.specific_cutting_force_kc` as-is satisfies FR-004 (no duplicate
  material list) and Constitution Principle VI (cross-cutting reference data shared across
  operations).

## 2. No point-engagement allowance for machining time

**Decision**: Turning's machining time is `lm / vf` with no additional allowance term.

**Rationale**: Drilling's `POINT_ANGLE_ALLOWANCE_FACTOR` exists specifically to account for
a twist drill's conical point needing to fully engage the material before reaching full
diameter — a geometry unique to drilling. A single-point turning tool has no equivalent
engagement geometry for a straight/OD pass; the tool is already engaged at full depth of
cut from the start of the cut. Published turning machining-time formulas (Sandvik, Machinery's
Handbook) do not include an engagement allowance term for straight turning.

**Alternatives considered**: Adding a small fixed allowance for tool approach/overtravel —
rejected as unsupported by any cited reference and unnecessary for this feature's scope
(straight/OD turning only); can be revisited if a later feature (e.g., facing) needs it.

## 3. Depth of cut is a required new input (spec correction); validation follows the existing per-operation-bound pattern, not a new shared bound or new error codes

**Decision**: Add `depth_of_cut_mm` as a required numeric input, distinct from workpiece
diameter and length of cut (renamed from an initial "cut length" to match milling's
existing `length_of_cut` terminology — see below), validated by three **new**
per-operation functions in `validation.py` — `validate_turning_diameter_mm`,
`validate_turning_depth_of_cut_mm` (which also enforces the diameter-relative "must be
less than the workpiece radius" check), and `validate_turning_length_of_cut_mm` — each
reading its own **new** `Configuration` bound field (`max_turning_diameter_mm`,
`max_turning_depth_of_cut_mm`, `max_turning_length_of_cut_mm`), exactly mirroring the
established `validate_mill_diameter_mm`/`max_mill_diameter_mm` precedent (verified by
reading `src/mfgparams/validation.py` and `config.py` directly: drilling's diameter bound
and milling's diameter bound are already two distinct functions and two distinct config
fields, sharing only the `INVALID_DIAMETER` code — never one shared function/bound).

**Rationale**: Unlike drilling (where the tool always removes the full hole diameter) and
identically to milling (which already takes `axial_depth_of_cut`/`radial_depth_of_cut` as
explicit inputs — `specs/009-milling-calculations`), turning's cutting-force formula
(`Fc = Kc * ap * fn`) requires the radial depth of material removed per pass as a direct
input; it cannot be derived from diameter and length of cut alone. This was missing from
the initial feature description and the first spec draft; discovered during this research
phase and folded back into `spec.md` (FR-003, FR-009, FR-010, User Stories 1-2, Edge Cases,
Key Entities) before proceeding to Phase 1, per Constitution Principle III (inputs must be
validated and physically meaningful) and Principle II (testable requirements).

An initial version of this research item and the resulting `data-model.md` incorrectly
assumed turning could reuse milling's *existing* shared `validate_depth_of_cut_mm`
function and its `max_depth_of_cut_mm` config bound directly, and separately invented a
brand-new `INVALID_CUT_LENGTH` error code for the length input. Both were wrong on closer
reading of `validation.py`/`config.py` during `/speckit-tasks` preparation:
`max_depth_of_cut_mm` defaults to 50 mm (sized for milling cutters), far too permissive
for a single-point turning tool's realistic ≤10 mm depth of cut; and `validation.py`
*already* defines a generic `validate_length_of_cut_mm`/`INVALID_LENGTH_OF_CUT`/
`max_length_of_cut_mm` for milling's `length_of_cut` input, making a new
`INVALID_CUT_LENGTH` code pure duplication (Constitution Principle I: "absence of
duplicated logic"). Corrected to the per-operation-function/per-operation-bound pattern
above, which needs zero new error codes — only new functions and new bound fields.

**Alternatives considered**: Defaulting depth of cut to a fixed fraction of diameter (as
drilling's point-allowance factor does for a different purpose) — rejected because depth
of cut is a real, user-controlled machining parameter with no safe universal default; an
incorrect implicit default would silently produce wrong force/power results, violating
Principle III ("an incorrect result is worse than no result"). Reusing milling's shared
`validate_depth_of_cut_mm`/`max_depth_of_cut_mm` as-is — rejected per the correction above
(wrong default bound for turning). Inventing a new error code for the length input —
rejected once `validate_length_of_cut_mm`/`INVALID_LENGTH_OF_CUT` was found to already
exist and fit exactly.

## 4. Reporting cutting force as a new `CalculationResult` field

**Decision**: Add an optional `cutting_force` field to the shared `CalculationResult`
(Newtons under METRIC, lbf under IMPERIAL), populated for turning and `None` for
drilling/milling — following the exact precedent `material_removal_rate` already set
(populated for milling, `None` for drilling).

**Rationale**: FR-009 requires the module to report cutting force as a first-class
calculated quantity (it is the number a machinist actually compares against a tool
holder's rated force in practice), not merely an internal step folded into `torque`. The
existing `CalculationResult` schema already anticipates per-operation-optional fields for
exactly this situation, so extending it this way needs no changes to drilling's or
milling's existing fields or callers (Constitution Principle VI: extend, don't modify).

**Alternatives considered**: Only reporting `torque` (as drilling/milling do) and treating
cutting force as an internal-only intermediate — rejected because FR-009 and SC-002
(spec.md) both call for cutting force as an independently-verifiable output, and it is the
quantity most turning reference tables publish directly.

## 5. Turning tool reference data source

**Decision**: Seed `turning/data/tools.toml` with the same three tool materials already
bundled for drilling and milling (HSS, Cobalt, Carbide), using published relative
cutting-speed/feed factors for single-point turning tools from the same class of reference
(Sandvik Coromant, Machinery's Handbook), following the identical TOML shape
`specs/005-configurable-materials-tools/contracts/materials-config-schema.md` already
defines for `[[tools]]`.

**Rationale**: Consistent with how drilling's and milling's tool lists were originally
seeded (per their own Assumptions sections); reuses the existing configuration schema and
loader verbatim (no new `table_key` semantics beyond adding `turning_tools` alongside the
existing `tools`/`end_mill_tools`/`face_mill_tools` sections, mirroring the milling tools
schema addendum).

**Alternatives considered**: None — this is a direct, low-risk continuation of an
established pattern with no open design question.

## 6. Console/TUI integration point

**Decision**: Add `TURNING = "turning"` to `MachiningOperation` (`src/mfgparams/models.py`)
and one new dispatch branch in `src/mfgparams/console/tui/machining_menu.py`, following the
exact shape of the existing `DRILLING`/`MILLING` branches (no new sub-operation prompt,
since turning has only one sub-operation in scope — straight/OD turning — unlike milling's
`MillingSubOperation` prompt).

**Rationale**: Matches `models.py`'s own documented extension point
(`MachiningOperation`'s docstring: "Each member routes to its own
`mfgparams.processes.machining.<operation>` package") exactly as designed for this.

**Alternatives considered**: Introducing a `TurningSubOperation` enum now, anticipating
future facing/grooving/parting slices — rejected as premature (Principle VI: extend by
addition when the need arises, not speculative structure ahead of it); the spec's
Assumptions section explicitly defers those variants to later features, each of which can
add its own sub-operation prompt the way milling did, without this feature guessing at
their shape now.
