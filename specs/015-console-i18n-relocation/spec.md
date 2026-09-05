# Feature Specification: Console-Owned Message Catalogues

**Feature Branch**: `015-console-i18n-relocation`

**Created**: 2026-09-04

**Status**: Draft

**Input**: User description: "Relocate UI-facing message catalogues (prompts, labels, error text) into mfgparams.console as the single source of truth for console-rendered strings, per issue #63 slice 2. Data translations that are user-supplied config (e.g. WorkpieceMaterial.translations in registry_config.py) stay in core — this slice does not move them. Core currently returns ErrorInfo with an already-locale-translated message (validation.py threads locale= throughout); this slice must decide and implement how error reporting works once English-only core no longer owns translation of UI strings, and update tests/contract/test_library_api_milling_locale.py to match. The console.missing_dependency* catalogue entries must remain in the core catalogue per specs/014-process-namespaces-extras/contracts/console-entry-contract.md (a message announcing the console is unavailable cannot be looked up from inside the console)."

## Context

This feature is **slice 2 of 4** of [issue #63](https://github.com/kniklas/mfgparams/issues/63), following
[014 (process namespaces and extras)](../014-process-namespaces-extras/spec.md), which moved the console's
*code* behind an optional extra but deliberately left message catalogues in core. This slice moves the
catalogues themselves.

Deliberately **not** in this slice:

| Slice | Scope | Why separate |
|---|---|---|
| 014 | Process/operation namespaces, console as an installable extra | Landed (PR #83); this slice builds on its layout and inherits its console-entry contract |
| 016 | Path-based CI job selection | Independent of catalogue ownership |
| 017 | Placeholder namespaces for not-yet-implemented processes | Independent of catalogue ownership |

Inherited constraint from 014's console-entry contract: the `console.missing_dependency*` catalogue
entries MUST stay in the core catalogue, because a message announcing the console is unavailable cannot be
looked up from inside the unavailable console. This feature MUST NOT move those entries.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find every console string in one place (Priority: P1)

As a maintainer or contributor changing a prompt, label, or piece of console output, I want every
console-rendered string sourced from a catalogue owned by the console package, so I don't have to guess
whether a given string lives in core or console before I can find and change it.

**Why this priority**: This is the substance of the slice and the reason it exists — issue #63's request
for a single source of UI strings.

**Independent Test**: Search the console package for every string it displays to a user and confirm each
resolves through a console-owned catalogue lookup, not a literal or a core-owned lookup — except the
inherited `console.missing_dependency*` entries, which are the one documented exception.

**Acceptance Scenarios**:

1. **Given** the console displays a prompt, label, or status message, **When** its catalogue entry is
   located, **Then** it lives in a catalogue module owned by `mfgparams.console`.
2. **Given** a contributor adds a new console-only string, **When** they follow the project's
   documentation, **Then** it directs them to add the entry to the console's catalogue, not core's.
3. **Given** the `console.missing_dependency*` entries, **When** their location is checked, **Then** they
   remain in the core catalogue, unaffected by this feature.

---

### User Story 2 - Get a readable error without the console installed (Priority: P1)

As someone using `mfgparams` as a library, without the `console` extra installed, I want a calculation
error to still come back as something I can show a user or log meaningfully, so that removing the console
from my dependency tree doesn't degrade the core API's usefulness.

**Why this priority**: Equal to Story 1. The core API's error-reporting contract (`CalculationResult.error`)
is public surface that non-console consumers rely on today; this slice must not strand it. This is also the
central open design question the slice exists to resolve (see Clarifications).

**Independent Test**: In an environment without the `console` extra installed, trigger a validation error
through the library API and confirm the result carries information sufficient to identify and describe the
error, in English, with no import of anything console-owned.

**Acceptance Scenarios**:

1. **Given** the `console` extra is not installed, **When** a library call returns a validation error,
   **Then** `CalculationResult.error` is fully usable — resolution of *what it contains* is recorded under
   Clarifications below.
2. **Given** the console *is* installed and a non-English locale is requested, **When** the console
   displays an error to the user, **Then** the displayed text is translated, sourced from the console's own
   catalogue.
3. **Given** `tests/contract/test_library_api_milling_locale.py` as it exists today, **When** this feature
   ships, **Then** the test is updated to assert the new contract rather than deleted or left asserting
   stale behaviour.

---

### User Story 3 - Keep data translations where the data lives (Priority: P2)

As a maintainer, I want material display-name translations to stay attached to the material data they
describe, so that a user-supplied materials config remains a single self-contained file and this slice does
not have to teach the console how to look up arbitrary user data.

**Why this priority**: Scope-limiting. Without this story, "single source of UI strings" could be
misread as "single source of *all* translated text," which is not achievable and was already ruled out
(`WorkpieceMaterial.translations` is user-supplied config data, not a catalogue entry).

**Independent Test**: Confirm `WorkpieceMaterial.translations` in `registry_config.py` and its schema are
untouched by this feature, and that material display names still resolve correctly after the feature ships.

**Acceptance Scenarios**:

1. **Given** a materials config with `WorkpieceMaterial.translations`, **When** this feature ships,
   **Then** the schema and its resolution behaviour are unchanged.
2. **Given** the console displays a material's translated display name, **When** the lookup happens,
   **Then** it still reads from the material's own config data, not from a console catalogue.

---

### Edge Cases

- **`console.missing_dependency*` entries**: MUST remain in core (inherited constraint; not re-litigated
  by this feature).
- **A locale requested that the console doesn't bundle a catalogue for**: falls back to English, per the
  existing `i18n.translate` fallback behaviour (FR-019e in 014's predecessor contracts) — this feature
  changes *where* catalogues live, not the fallback rule itself.
- **A library caller who never installs the console extra but wants translated (non-English) error text**:
  out of scope for this feature to satisfy — see Clarifications. The library API's obligation is a usable
  English result, not localization without the console.
- **`WorkpieceMaterial.translations`**: explicitly out of scope for relocation (Story 3).
- **A `code` that covers more than one message template** (e.g. `INVALID_DIAMETER` for both the
  "zero" and "exceeds max" cases): the console MUST re-render using `message_key` (FR-005b), never by
  branching on `code`, so this is unambiguous by construction rather than by convention.

## Requirements *(mandatory)*

### Functional Requirements

#### Catalogue ownership

- **FR-001**: Every console-rendered UI string (prompts, labels, status/progress text) MUST be sourced
  from a catalogue module owned by `mfgparams.console`, not from core.
- **FR-002**: The `console.missing_dependency*` catalogue entries MUST remain in the core catalogue,
  unaffected by this feature, per the inherited constraint in 014's console-entry contract.
- **FR-003**: `WorkpieceMaterial.translations` and its schema in `registry_config.py` MUST NOT be moved
  or altered by this feature.
- **FR-004**: The previous location of any relocated catalogue entry MUST NOT remain as an alias, shim,
  or dual lookup path — consistent with 014's no-alias precedent (FR-004 of that slice).

#### Error reporting contract

- **FR-005**: Core MUST retain a minimal English-only error-text catalogue and continue populating
  `ErrorInfo.message` from it, so `CalculationResult.error` stays fully usable — readable English
  text, no import of anything console-owned — for a library caller who does not have the `console`
  extra installed. This is an explicit, deliberate exception to FR-001: error text is the one UI-string
  category whose *English* rendering stays a core responsibility, because it is part of the public
  library API's contract and must not depend on an optional extra.
- **FR-005a**: When the `console` extra is installed and a non-English locale is active, the console
  MUST render translated error text by re-rendering from `ErrorInfo.message_key` and `ErrorInfo.kwargs`
  (FR-005b) through the console's own catalogue, rather than by translating core's English `message`
  string. Non-English error text is therefore a console-catalogue concern; only the English fallback
  is core's.
- **FR-005b**: `ErrorInfo` MUST expose two additional fields beyond today's `code`/`message`:
  `message_key` (the stable, fine-grained catalog key already used internally, e.g.
  `"error.invalid_diameter.max"`, naming it consistently with the existing
  `RegistryConfigError.message_key` and `MergeResult.notice_key`) and `kwargs` (the interpolation
  values already passed to `translate()`, e.g. `{"max_diameter_mm": 50.0}`). These exist so the console can reproduce the exact
  message template and values in another locale — `code` alone cannot: a single code such as
  `INVALID_DIAMETER` already covers more than one distinct message template (a "value is zero" case
  and a "value exceeds max" case with a parameter), so it cannot serve as the re-rendering key.
- **FR-006**: Error **codes** (`ErrorInfo.code`) MUST remain stable identifiers with their current,
  coarser granularity, unaffected by this feature — `message_key` (FR-005b) is the new, finer-grained
  identifier the console uses; `code` keeps its existing meaning and MUST NOT be split or repurposed
  to carry that precision instead.
- **FR-007**: `tests/contract/test_library_api_milling_locale.py` MUST be updated to assert the FR-005/
  FR-005a contract: core's `ErrorInfo.message` is English-only regardless of `MFGPARAMS_LOCALE` or an
  explicit `locale=` argument, and non-English translation is verified through the console's rendering
  path instead of through the library API's `locale` parameter. Whether the library API's `locale=`
  parameter itself is retained (as a now-inert compatibility argument), deprecated, or removed is a
  plan-level decision (see Assumptions) — this requirement only fixes what the *returned message text*
  must be.

#### Mirroring

- **FR-008**: Documentation describing where to add or change a user-facing string MUST be updated to
  point at the console's catalogue for console strings, and at core for the entries FR-002 preserves.

### Key Entities

- **Console catalogue**: A message-key-to-text mapping owned by `mfgparams.console`, one per locale it
  bundles, holding UI strings (prompts, labels, non-error status text) and — pending FR-005's resolution —
  possibly error text as well.
- **Core catalogue**: The existing `mfgparams.locales.*` catalogue, retained for the entries FR-002
  requires plus whatever FR-005 assigns to it.
- **ErrorInfo**: Returned in `CalculationResult.error`. Today: `code` + `message`. After this feature:
  `code` (unchanged meaning, coarse), `message` (English-only, per FR-005), `message_key` (new — the
  fine-grained catalog key, per FR-005b), and `kwargs` (new — the interpolation values for that key,
  per FR-005b).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every string the console displays resolves through a console-owned catalogue lookup, except
  the documented `console.missing_dependency*` exception — verified by an automated check, not manual
  review (mirroring 014's precedent of enforcing structural rules with tests, not convention).
- **SC-002**: A library caller without the `console` extra installed receives a usable error result for
  every validation failure the core API can produce, with zero import of anything console-owned.
- **SC-003**: `tests/contract/test_library_api_milling_locale.py` passes against the new contract, and no
  other existing test suite regresses.
- **SC-004**: Zero functional references to a relocated catalogue's previous location remain, enforced
  automatically.
- **SC-005**: `WorkpieceMaterial.translations` resolution is verified unchanged by the existing materials
  config contract tests, unmodified in substance by this feature.
- **SC-006**: For every distinct message template reachable through the core API — including cases
  where more than one template shares a `code` — the console renders correct, distinct translated text
  for each, verified by a test that exercises at least one such shared-`code` pair (e.g.
  `INVALID_DIAMETER`'s zero and max cases).
- **SC-007**: A contributor changing or adding a user-facing string can determine, from documentation
  alone — no code search, no guessing — which catalogue (console's or core's) owns it (FR-008).

## Assumptions

- **This feature is a relocation of existing catalogue infrastructure, not the addition of new
  languages.** The repository currently bundles only an English (`en`) catalogue; this feature does not
  add non-English catalogues as part of its scope.
- **No published release exists yet** (per [[mfgparams-restructure-before-pypi]] / 014's own assumption,
  reverified as of 014's landing): this feature MUST NOT trigger its own version release. Changes
  accumulate under `## [Unreleased]` for the single 2.0.0 issue #63 will cut once slice 017 lands.
- **~~The console's dependency-missing message (FR-002) is the only catalogue entry with a
  structural reason to stay in core.~~ Corrected during implementation (T007):** a second, narrow
  exception exists. `validate_depth_of_cut_mm`/`validate_engagement_mm` build their core-owned
  English `message` by embedding a `{label}` resolved from a `cli.label.*` key
  (`axial_depth_of_cut`/`radial_depth_of_cut`/`width_of_cut`) via `translate()`. Core must be able
  to do this without the console installed (FR-005), so these three keys exist in **both**
  catalogues — core's copy feeds error-message construction, console's copy feeds the prompt label
  display. This was not visible until implementation exercised the actual `translate()` call sites;
  it does not generalize to any other entry.
- **The library API's `locale=` parameter (on `calculate_end_milling`, `calculate_face_milling`, etc.)
  is left for `/speckit-plan` to resolve** now that core's `ErrorInfo.message` is always English
  (FR-005). Once core no longer varies its output by locale, an accepted-but-inert `locale=` argument
  is a plan-level API design choice (keep for compatibility vs. deprecate vs. remove), not a
  spec-level requirement — FR-007 only fixes the returned text, not the signature.

## Out of Scope

- Adding non-English catalogues (this feature relocates existing infrastructure only).
- Moving or altering `WorkpieceMaterial.translations` or the materials config schema (Story 3).
- Path-based CI job selection (slice 016).
- Creating placeholder namespaces for unimplemented processes (slice 017).
- Publishing to a package index (issue #40).

## Dependencies

- Depends on 014 (process namespaces and extras), landed as PR #83 — this feature's console package and
  console-entry contract are inherited, not re-derived.
- 014's console-entry contract (`specs/014-process-namespaces-extras/contracts/console-entry-contract.md`,
  "Message catalogue constraint" section) binds FR-002 directly.
- Constitution Principle VIII (no inlined user-facing strings) governs both FR-001 and whatever FR-005
  resolves to.

## Clarifications

### Session 2026-09-04

- Q: FR-005 — what does `CalculationResult.error` carry once console owns UI-string catalogues and core
  is meant to stop being the one true source of translated text? → **A: core keeps a minimal
  English-only error-text catalogue and keeps populating `ErrorInfo.message` from it; the console
  layers translated rendering on top for non-English locales by re-rendering from `message_key`
  (+ kwargs) through its own catalogue.** [Corrected post-review: this bullet originally said
  `code`, written before the second clarification below established that `code` is too coarse to
  serve as the re-rendering key at all — a Copilot review on the implementing PR caught the
  resulting self-contradiction.] Chosen over "core returns key+kwargs only" because that would make a
  library caller without the console extra lose readable error text entirely, breaking today's
  guarantee for no benefit proportional to the cost. Chosen over "core depends on console for its
  catalogue" because that reopens 014's FR-008 (core must not import console) for no compensating
  benefit. Recorded in FR-005/FR-005a; the library API's `locale=` parameter fate is deferred to
  `/speckit-plan` (see Assumptions).
- Q: `ErrorInfo.code` alone can't identify which message template to re-render — `INVALID_DIAMETER`
  already covers a "zero" case and a distinct "exceeds max" case carrying a `max_diameter_mm` value,
  and there is no `kwargs` field today. How should the console determine the template and its
  interpolation values? → **A: `ErrorInfo` gains two new fields — `message_key` (the existing
  fine-grained catalog key, e.g. `"error.invalid_diameter.max"`, matching the existing
  `RegistryConfigError.message_key`/`MergeResult.notice_key` naming) and `kwargs` (the interpolation
  values already passed to `translate()`).** `code` keeps its current, coarser meaning and is
  unaffected (FR-006). Chosen over making `code` itself fully granular because that would break
  FR-006 and any caller branching on today's codes; chosen over leaving ambiguous-`code` errors
  English-only under the console because that silently degrades translation coverage for an already-
  common case. Recorded in FR-005a/FR-005b and the ErrorInfo entity.
