# Contract Delta: Materials Configuration File Schema — `material_number`/`short_notation`

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)
**Base contract**: [../../005-configurable-materials-tools/contracts/materials-config-schema.md](../../005-configurable-materials-tools/contracts/materials-config-schema.md)

This is an additive delta to the base `[[materials]]` schema (005's contract). It does not
replace that document — it adds two new optional keys to the `[[materials]]` entry table
defined there. The `[[tools]]` schema is untouched by this feature.

## New `[[materials]]` entry fields

| Key | Required | Type | Notes |
|---|---|---|---|
| `material_number` | No | string | EN material number notation, e.g. `"1.7225+N"`. Free-form — no format is enforced beyond the validation rule below. Absent by default. |
| `short_notation` | No | string | Shortened/DIN-style designation, e.g. `"42CrMo4+N"`. Same rules as `material_number`. |

## Validation rules (additive to the base contract's rules 1–7)

8. `material_number` and `short_notation`, if present, MUST each be a non-empty single-line
   string containing no C0/C1 control character and no Unicode line or paragraph separator —
   identical to the base contract's rule 7 for `material_type`. A value violating this is
   **not** fatal: a validation issue is recorded and the field falls back to absent (`None`),
   mirroring the warn-and-continue policy already used for invalid `material_type`/numeric
   values.
9. Unlike the numeric fields (base contract rule 2), neither key is required — a metal
   material with no known EN number or shortened designation for either is valid and remains
   fully selectable by common name alone (spec.md Edge Cases).
10. Both keys are **sticky** across a merge (base contract rule 7's mechanism, extended):
    when a user entry overrides a bundled entry without restating `material_number`/
    `short_notation`, the bundled value for that key is carried over rather than dropped
    (research.md Decision 5).

## Example

An entry populating `material_number`/`short_notation` SHOULD be named after the specific
grade those fields describe, unless (like the bundled defaults — see `materials.toml`'s own
top-of-file comment) the value is an explicitly documented *representative* default for a
more generic name.

```toml
[[materials]]
name = "S235JR Structural Steel"
material_type = "metal"
reference_cutting_speed = 25.0
reference_feed_per_rev = 0.20
specific_cutting_force = 1900.0
unit_system = "metric"
material_number = "1.0038"
short_notation = "S235JR"

# A user override that only changes the reference cutting speed still keeps the bundled
# entry's material_number/short_notation, because both are sticky fields (rule 10) — the
# user file below need not repeat them.
[[materials]]
name = "S235JR Structural Steel"
reference_cutting_speed = 28.0
reference_feed_per_rev = 0.20
specific_cutting_force = 1900.0
```

## Consumers

- `src/mfgparams/registry_config.py`: **unchanged** — `material_number`/`short_notation`
  already flow through `_parse_entries`'s generic `fields_dict` capture (any TOML key not
  `name`/`unit_system`/`translations`) with no code change required.
- `src/mfgparams/registry.py`: `_to_material` reads and validates both new keys (rule 8);
  `_STICKY_FIELDS` gains both (rule 10).
