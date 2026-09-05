# Phase 0 Research: Console-Owned Message Catalogues

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-04

Both of the spec's clarifications were resolved before planning, so no `NEEDS CLARIFICATION`
markers entered this phase. The items below are the design unknowns the plan surfaced.

---

## 1. Two i18n loaders, not a shared abstraction

**Decision**: `mfgparams/console/i18n.py` duplicates `mfgparams/i18n.py`'s loader mechanism
(`_load_catalog`, `translate`, `has_message`, cache) verbatim in structure, pointed at
`mfgparams.console.locales.*` instead of `mfgparams.locales.*`. No shared base module.

**Rationale**: The two catalogues are not the same concern wearing two hats — they have different
compatibility contracts. Core's catalogue (plus `ErrorInfo.message_key`) is part of the public
library API: an external caller can rely on a `message_key` string not changing across a minor
version. Console's catalogue is purely presentational and can be edited freely as the console's UX
changes. Merging them behind one shared loader module would either (a) force console's catalogue
changes to be reviewed against core's stability bar for no reason, or (b) require the "one loader,
two policies" module to encode a distinction that two separate ~50-line modules encode for free by
being separate files. ~50 lines duplicated once is cheaper than the coupling.

**Alternatives considered**:

- *One `mfgparams.i18n` module parameterized by package name*: rejected — every call site would
  need to pass which catalogue to use, turning a currently-argument-free `translate(locale, key)`
  call into `translate(locale, key, catalog_package=...)` everywhere, for a distinction that is
  fixed per call site (core code never wants console's catalogue and vice versa) and is better
  expressed by *which module you imported* than by an extra argument threaded through ~80 call
  sites.
- *Console imports core's `translate` and passes it a different catalogue module path as an
  argument*: same rejection as above, plus it would need `mfgparams.i18n` to accept an
  console-supplied package name, which is exactly the core-importing-nothing-console-specific
  boundary 014's `console-entry-contract.md` "Layering" section exists to keep clean in the other
  direction — no reason to open a new coupling point here.

---

## 2. `ErrorInfo` field names: `message_key`/`kwargs`, tuple-of-pairs, not a dict

**Decision**: `message_key: str` and `kwargs: tuple[tuple[str, object], ...] = ()`, mirroring
`registry_config.MergeResult.notice_key`/`notice_kwargs` in naming, and matching
`RegistryConfigError.message_key` exactly. The type is a tuple of pairs, like
`MergeResult.notice_kwargs`, not a plain `dict`.

**Rationale**: Neither the names nor the shape are new — this codebase already has two existing
"catalogue key plus its render-time arguments" carriers: `RegistryConfigError.message_key`/
`.kwargs` (an exception, so `kwargs` is a plain `dict` there — exceptions are never hashed) and
`MergeResult.notice_key`/`.notice_kwargs` (`notice_kwargs` is a tuple of pairs). `ErrorInfo` gaining
the same *concept* under a *different* name (`message_id`/`params`, considered during drafting)
would have given this codebase three names for one idea. Naming it `message_key`/`kwargs` instead
means a contributor who already knows `RegistryConfigError` recognizes `ErrorInfo` immediately.

The tuple-of-pairs type (not `dict`) is required, not just consistent: `ErrorInfo` is
`@dataclass(frozen=True)` today with only `str` fields, which is hashable by Python's default
frozen-dataclass behavior; a `dict` field would break that (dicts are unhashable), unlike
`RegistryConfigError`, which is an exception and was never relying on hashability. Call sites render
with `translate(locale, error.message_key, **dict(error.kwargs))`, identical in shape to the
existing `materials_load_notice()` call site (`console/cli.py:510-512`).

**Alternatives considered**:

- *`message_id`/`params` (the names used while drafting the spec)*: renamed during planning once
  `RegistryConfigError.message_key` and `MergeResult.notice_key`/`notice_kwargs` were found —
  functionally identical, but introduces a second vocabulary for a concept the codebase already
  names consistently. The spec was updated in place; no design substance changed, only the labels.
- *`kwargs: dict[str, object]`*: more ergonomic to construct (`kwargs={"max_diameter_mm": 50.0}`
  vs. `kwargs=(("max_diameter_mm", 50.0),)`), but breaks `ErrorInfo`'s hashability for no benefit
  anyone has asked for. Rejected for consistency with `MergeResult.notice_kwargs`, not performance.
- *No `kwargs` field; `message_key` alone, with the console re-deriving values by re-running
  validation*: rejected outright — it would require the console to re-execute the validation logic
  it is trying to only *display* the result of, coupling presentation to calculation internals in
  exactly the way Principle VI's layering rules exist to prevent.

---

## 3. Reconciling "no duplication" with FR-005's core-must-be-self-sufficient requirement

**Decision**: Core's English catalogue (`mfgparams/locales/en.py`) keeps the `error.*`/`warning.*`
entries (their English *text*). The console's catalogue does **not** get an English copy of those
same keys — only a non-English console catalogue (when one is eventually added; see spec
Assumptions, none ships in this feature) needs them, because the English path always renders
through `ErrorInfo.message` directly (FR-005) and never touches the console's catalogue at all.

**Rationale**: This looked at first like it re-introduces the duplication FR-001 exists to remove —
error text living in two catalogues. It does not, once the two roles are separated: core's copy is
the *only* copy of the English text (console never holds its own English translation of an error
message; it just displays `error.message` verbatim, per FR-005/SC-002). A future non-English
console catalogue holds *translations*, keyed by the same `message_key`, which is genuinely new
content core could never have supplied (core is English-only by FR-005) — not a second copy of
something core already owns. So "single source of truth for console-rendered strings" (FR-001)
holds for every string that has more than one rendering to choose between; error text's English
rendering has exactly one owner (core), and FR-001 was never meant to relocate the one thing that
must survive the console's absence.

**Consequence for this feature's scope**: because no non-English catalogue ships yet (spec
Assumptions — this is a relocation of infrastructure, not new translations), this feature adds the
*mechanism* (`message_key`/`kwargs` on `ErrorInfo`, the console's re-rendering code path) and proves it
with a test fixture catalogue (mirroring `test_library_api_milling_locale.py`'s existing
`_FIXTURE_LOCALE` pattern), exactly as 014 proved FR-011's missing-dependency guard against an
extra that was itself still empty.

---

## 4. What actually moves out of `mfgparams/locales/en.py`

**Decision**: Every key whose comment-delimited section in `en.py` is not `error.*`/`warning.*`/
`notice.*`/`console.missing_dependency*` moves to `mfgparams/console/locales/en.py`. Concretely,
by the file's own section markers: "Interactive text interface … prompts and labels", "Material-type
(category) selection", and the un-sectioned trailing UI keys (`cli.label.unit_system_suffix`,
milling operation/sub-operation labels, milling input prompts/labels). `material_type.*` moves with
them — it is a UI label for a category, not material data (distinct from `WorkpieceMaterial
.translations`, which Story 3 keeps untouched).

**Rationale**: The file's existing section comments already encode exactly this boundary (they were
written anticipating this slice — see the `console.missing_dependency` entry's own comment citing
"slice 015"). No new categorization scheme is needed; the move is mechanical once FR-002's one
exception is honored.

**Alternatives considered**: None — the boundary was already decided by 014 and confirmed by the
spec's Clarifications; this item records where it lands file-by-file rather than re-litigating it.

**Correction found during implementation (T007)**: the move above is not quite complete as stated.
Three of the moved keys — `cli.label.axial_depth_of_cut`, `cli.label.radial_depth_of_cut`,
`cli.label.width_of_cut` — are also embedded, via `translate()`, inside the core-owned English
`message` that `validate_depth_of_cut_mm`/`validate_engagement_mm` build (as the `{label}`
placeholder in `error.invalid_depth_of_cut.*`/`error.invalid_engagement`). A pure move breaks core's
ability to build its own English error text without the console installed — violating FR-005 — so
these three keys stay in **both** catalogues: core's copy feeds message construction, console's
copy feeds the prompt label. See
[catalogue-ownership-contract.md](./contracts/catalogue-ownership-contract.md) for the corrected,
authoritative table and spec.md's Assumptions for the correction note. This was not something static
analysis of the catalog would have caught before implementation — it required tracing which
`error.*` templates take a `{label}` argument and where that argument's *value* originates.
