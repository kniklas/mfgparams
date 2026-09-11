# Contract: Turning Tools Configuration Schema (addendum)

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

Addendum to `specs/005-configurable-materials-tools/contracts/materials-config-schema.md`
and `specs/009-milling-calculations/contracts/milling-tools-config-schema.md`. This
feature adds one further top-level array-of-tables, `[[turning_tools]]`, to the **same**
optional user configuration file (`materials_config_path`). No second configuration file
and no new loader is introduced (FR-005).

## Added section

```toml
# Turning tools (new in 019)
[[turning_tools]]
name = "Carbide"
cutting_speed_factor = 2.4
feed_factor = 1.05
unit_system = "metric"

  [turning_tools.translations]
  pl = "Weglik spiekany"
```

### Field rules

| Field | Required | Rules |
|---|---|---|
| `name` | yes | non-empty string; unique within `turning_tools` by **exact** (case-sensitive) match — verified against `registry_config.py`'s actual `_check_duplicates`/`merge_entries`, which compare names exactly, not case-insensitively, for every registry (materials, drilling tools, milling tools alike; matches `specs/008-material-categorization/contracts/material-selection.md`'s explicit "not case-insensitive" for materials). Matching an existing bundled name performs an override/merge, exactly as for `[[tools]]`. (Correction, Copilot review finding on PR #100: an earlier draft of this row claimed "case-insensitive," copied from `specs/009-milling-calculations/contracts/milling-tools-config-schema.md`'s own identical, equally inaccurate claim — neither turning's nor milling's registry code has ever implemented case-insensitive matching; only this document's wording was wrong, not the shipped behavior, so this fix corrects the doc rather than adding new case-folding logic to shared registry code that three other operations already rely on behaving exactly-matched.) |
| `cutting_speed_factor` | yes for a new entry, optional when overriding | number `> 0` |
| `feed_factor` | yes for a new entry, optional when overriding | number `> 0` — unlike the milling addendum's tool sections, turning tools DO carry a `feed_factor` (turning's feed-per-revolution formula reuses drilling's shape, research.md #1), matching `[[tools]]`'s field set rather than `[[end_mill_tools]]`/`[[face_mill_tools]]`'s |
| `unit_system` | no | `"metric"` \| `"imperial"`; defaults to `"metric"` |
| `translations` | no | table of locale code -> translated display name |

## Section isolation (normative)

Each registry loads **only** its own `table_key` and MUST ignore every other top-level
section, extending the existing isolation table
(`specs/009-milling-calculations/contracts/milling-tools-config-schema.md`):

| Registry | `table_key` |
|---|---|
| Materials | `materials` |
| Drilling tools | `tools` |
| End-mill tools | `end_mill_tools` |
| Face-mill tools | `face_mill_tools` |
| Turning tools | `turning_tools` |

Consequences that MUST hold (and are covered by a regression test, mirroring the existing
milling isolation tests):

1. A config file containing only `[[turning_tools]]` leaves the drilling, end-mill, and
   face-mill tool registries byte-for-byte identical to their bundled defaults, and the
   material registry unaffected.
2. A config file containing `[[tools]]`, `[[end_mill_tools]]`, `[[face_mill_tools]]`, and
   `[[turning_tools]]` together applies each section only to its own registry — no
   cross-contamination between operations' tool lists.

## Bundled defaults (`turning/data/tools.toml`)

Seeded with the same three tool materials already bundled for drilling and milling (HSS,
Cobalt, Carbide), following the identical shape to
`src/mfgparams/processes/machining/drilling/data/tools.toml` (research.md #5):

```toml
[[turning_tools]]
name = "HSS"
cutting_speed_factor = 1.0
feed_factor = 1.0
unit_system = "metric"

[[turning_tools]]
name = "Cobalt"
cutting_speed_factor = 1.2
feed_factor = 1.0
unit_system = "metric"

[[turning_tools]]
name = "Carbide"
cutting_speed_factor = 2.4
feed_factor = 1.05
unit_system = "metric"
```

Note: the *bundled* file's own top-level key is `turning_tools`, matching the external
override file's key exactly — verified against milling's actual precedent
(`milling/end_milling/data/tools.toml` is itself keyed `[[end_mill_tools]]`, not
`[[tools]]`; `load_and_merge()`/`parse_toml_entries()` parse the bundled resource and any
user override with the *same* `table_key`, per `registry_config.py`). Only drilling's own
bundled file happens to be keyed `tools`, because drilling's table key genuinely is
`tools`; that is not a "bundled files are always `tools`" rule, and this document's
earlier draft was wrong to describe it that way.
