# Phase 1 Data Model: Console-Owned Message Catalogues

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

This feature changes one existing entity (`ErrorInfo`) and introduces one new one (the console
catalogue). No persisted storage, database, or migration is involved — every entity here is an
in-memory Python object or a static module.

## ErrorInfo (changed)

Returned as `CalculationResult.error`. Defined in `src/mfgparams/models.py`.

| Field | Type | Status | Notes |
|---|---|---|---|
| `code` | `str` | Unchanged | Coarse, stable, machine-readable identifier (e.g. `"INVALID_DIAMETER"`). May cover more than one `message_key` (FR-006). Existing callers branching on `code` are unaffected. |
| `message` | `str` | Unchanged meaning, changed content | English-language text (FR-005). Previously varied by the caller's `locale`; now always English, regardless of `MFGPARAMS_LOCALE` or an explicit `locale=` argument (FR-007). |
| `message_key` | `str` | **New** (FR-005b) | The fine-grained catalog key already computed internally (e.g. `"error.invalid_diameter.max"`). Named to match the existing `RegistryConfigError.message_key` (research.md #2). One-to-one with a message template; unlike `code`, never shared between two distinct templates. |
| `kwargs` | `tuple[tuple[str, object], ...]` | **New** (FR-005b), default `()` | The interpolation values already passed to `translate()` internally (e.g. `(("max_diameter_mm", 50.0),)`). Tuple-of-pairs, not `dict`, to preserve `ErrorInfo`'s existing hashability (`@dataclass(frozen=True)`) and to match `MergeResult.notice_kwargs`'s shape exactly (research.md #2). |

**Validation rule**: `message_key` MUST be non-empty and MUST be a real key in
`mfgparams.locales.<locale>` for at least the English catalog (i.e., `i18n.has_message(DEFAULT_LOCALE,
message_key)` is `True`) for every `ErrorInfo` the core constructs — this is what makes FR-005a's
re-rendering possible at all. Enforced by test, not by a runtime assertion in `ErrorInfo.__init__`
(matching how Principle VIII's existing catalog-key rules are enforced elsewhere in this codebase —
by `tests/static/test_no_hardcoded_strings.py`-style checks, not runtime guards).

**Construction sites**: every `ErrorInfo(...)` call in `validation.py` (~25 sites) gains
`message_key=` and, where the message has placeholders, `kwargs=`. The `code` and `message`
arguments and their values are unchanged — this is purely additive at each call site.

## Console catalogue (new)

A locale-keyed collection of `mfgparams.console.locales.<locale>` modules, structurally identical to
today's `mfgparams.locales.<locale>` modules.

| Attribute | Type | Notes |
|---|---|---|
| `MESSAGES` | `dict[str, str]` | Module-level dict, same shape as `mfgparams.locales.en.MESSAGES`. Keys are `cli.*`/`material_type.*` (moved from core, research.md #4) in the English module; a future non-English module would additionally carry `error.*`/`warning.*` keys for FR-005a re-rendering (none ships in this feature — spec Assumptions). **Exception**: three `cli.label.*` keys (`axial_depth_of_cut`/`radial_depth_of_cut`/`width_of_cut`) also live in `mfgparams.locales.en.MESSAGES` (core's, unchanged/pre-existing catalogue — not itself a new-or-changed entity, so it has no section of its own here) — found during implementation (T007), not assumed up front; see `contracts/catalogue-ownership-contract.md` for the full reasoning. |

**Loader**: `mfgparams/console/i18n.py`, structurally identical to `mfgparams/i18n.py`
(`_load_catalog`, `translate`, `has_message`, `clear_catalog_cache`, `get_locale`/`get_raw_locale`
re-exported or re-implemented — see research.md #1 for why this is a deliberate duplicate, not a
shared module). Its `_load_catalog` imports `mfgparams.console.locales.<locale>` rather than
`mfgparams.locales.<locale>`; everything else about the lookup-and-fallback contract is identical,
including English fallback for a missing key or locale.

## Relationships

```
CalculationResult.error : ErrorInfo
ErrorInfo.message        — rendered once, in core, from ErrorInfo.message_key + kwargs (English only)
ErrorInfo.message_key    — looked up a second time, by the console, in ITS OWN catalogue,
                            when the active locale is non-English (FR-005a)
                          — looked up NOWHERE when the active locale is English; the console
                            displays ErrorInfo.message verbatim in that case (no double-render)
```

No entity here has a lifecycle or state transitions — `ErrorInfo` is an immutable, one-shot result
value, and both catalogues are loaded once and cached for the process lifetime (existing
`_catalog_cache` behavior, replicated per research.md #1).

## Out of scope for this data model

- `WorkpieceMaterial.translations` and its schema (`registry_config.py`) — untouched, per spec
  Story 3 / FR-003. Not a message-catalogue entity; it is user-supplied config data attached to a
  registry object, and stays that way.
- `RegistryConfigError` and `MergeResult` — cited above as the existing precedent for
  `message_key`/`kwargs` naming and shape, but neither is modified by this feature. Their
  `error.materials_config.*`/`notice.materials_config.*` catalogue keys stay in core, by the same
  "library caller without console must still get usable text" reasoning as `ErrorInfo` (FR-005) —
  they are already key+kwargs-shaped, so no `ErrorInfo`-style change is needed for them.
