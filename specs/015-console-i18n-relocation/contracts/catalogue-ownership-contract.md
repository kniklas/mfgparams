# Contract: which catalogue owns which key

**Feature**: [../spec.md](../spec.md) | **Requirements**: FR-001, FR-002, FR-004, SC-001

## The rule

A message key lives in exactly one catalogue, determined by this table, not by convention:

| Key pattern | Owner | Why |
|---|---|---|
| `cli.*` | `mfgparams.console.locales.*` | Console-rendered prompt/label/status text (FR-001). |
| `material_type.*` | `mfgparams.console.locales.*` | Console-rendered category label — a UI string, not material data (distinct from `WorkpieceMaterial.translations`; see Story 3). |
| `error.*`, `warning.*`, `notice.*` | `mfgparams.locales.*` | Core-owned per FR-005: must render (in English) with no import of anything console-owned, for a library caller without the `console` extra. Includes `error.materials_config.*`/`notice.materials_config.*` (`RegistryConfigError`/`MergeResult`), which already carry this same reasoning today. |
| `console.missing_dependency*` | `mfgparams.locales.*` | Inherited constraint from [014's console-entry contract](../../014-process-namespaces-extras/contracts/console-entry-contract.md) — a message announcing the console is unavailable cannot live where it can't be looked up (FR-002). This is a `console.*`-prefixed key that stays in core, precisely because of what it says. |
| `cli.label.axial_depth_of_cut`, `cli.label.radial_depth_of_cut`, `cli.label.width_of_cut` | **Both** | Found during implementation (T007), not assumed up front — spec.md's Assumptions section is corrected accordingly. `validate_depth_of_cut_mm`/`validate_engagement_mm` embed one of these, resolved via `translate()`, as `{label}` inside their core-owned English `message` (FR-005). Core needs its own English copy to do that without the console installed; console keeps its copy for the matching prompt label. Genuinely dual-use, not an oversight — but exactly the kind of thing FR-004's "no key in both catalogues" default should have flagged as a risk in `/speckit-clarify` rather than being discovered in code. |

Outside the two documented exceptions above, no key legitimately exists in both catalogues. A key
relocated by this feature MUST be removed from its previous location in the same change (FR-004) —
no alias, no dual lookup, for any key other than these two exceptions.

## Enforcement

Convention alone regresses silently (this is exactly what 014's `console-entry-contract.md` warns
about for its own guard). This feature is enforced by:

- `tests/static/test_console_catalogue_ownership.py` (new): for every string literal `console/cli.py`
  passes to `translate()`, assert the key exists in `mfgparams.console.locales.en.MESSAGES` — except
  `console.missing_dependency*` (present in `mfgparams.locales.en.MESSAGES` instead, absent from the
  console's) and the three `cli.label.*` depth/engagement keys (present in **both**, by design —
  see the table above).
- The existing `tests/static/test_no_hardcoded_strings.py` (Principle VIII) continues to apply
  unchanged — a literal string still cannot be inlined at any call site, in either package; this
  feature only changes *which* catalogue the non-literal lookup targets.
- A reciprocal check that no `error.*`/`warning.*`/`notice.*` key that core needs for FR-005 is
  missing from `mfgparams.locales.en.MESSAGES` (i.e., the move in research.md #4 didn't
  over-relocate something core still needs), and that the two `RegistryConfigError`/
  `materials_load_notice` call sites in `console/cli.py` render through core's `translate`
  (aliased `_translate_core` there), not the console's — they pass a *dynamic* key
  (`exc.message_key`/`notice_key`), so the string-literal scan above cannot see them; this check
  must inspect those two call sites by name instead.

## Non-goals

- This contract does not require a non-English catalogue to exist on either side (spec Assumptions
  — this feature relocates infrastructure, it does not add translations).
- This contract does not change `i18n.get_locale`/`get_raw_locale`'s resolution rules
  (`MFGPARAMS_LOCALE`, no OS auto-detection) on either side — both loaders keep that behavior
  identically (research.md #1).
