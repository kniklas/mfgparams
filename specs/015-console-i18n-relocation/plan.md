# Implementation Plan: Console-Owned Message Catalogues

**Branch**: `015-console-i18n-relocation` | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-console-i18n-relocation/spec.md`

## Summary

Move UI-string catalogues (prompts, labels, status text) out of `mfgparams.locales.*` and into a
catalogue owned by `mfgparams.console`, so the console is the single place to find and change what
it displays — continuing #63 from [014](../014-process-namespaces-extras/plan.md), which separated
the console's *code* but deliberately left its strings in core.

Error text is the one category that cannot simply move, because `CalculationResult.error` is public
library-API surface that must stay usable with the `console` extra absent. The clarified design
(spec Clarifications) keeps a minimal English-only error catalogue in core and gives `ErrorInfo` two
new fields — `message_key` and `kwargs` — so the console can re-render translated error text from the
same identifier core already computes internally, without core ever holding non-English text. This
mirrors a pattern the codebase already has: `registry.materials_load_notice()` returns
`(notice_key, notice_kwargs)` rather than pre-rendered text, and `console/cli.py:510-512` renders it
at the call site. `ErrorInfo` has simply never followed that pattern until now.

**Decision this plan owes spec.md** (spec.md's Assumptions explicitly defers it here): the public
`locale=` parameter on `calculate()`/`calculate_end_milling()`/`calculate_face_milling()` is
**retained, unchanged in signature**, but no longer affects `ErrorInfo.message` (always English per
the design above) — kept rather than deprecated or removed, since removing it would stack a second
breaking signature change on top of `ErrorInfo`'s own shape change for no compensating benefit.
Implemented in tasks.md T013.

## Technical Context

**Language/Version**: Python 3.9–3.12 (unchanged from 014; `requires-python = ">=3.9"`)

**Primary Dependencies**: None added. `mfgparams.i18n`'s loader (`importlib.import_module` +
`str.format()`) is reused as-is; the console gets its own instance of the same mechanism pointed at
a different package, not a new library.

**Storage**: N/A — catalogues are Python modules (`MESSAGES: dict[str, str]`), as today.

**Testing**: pytest + pytest-cov, unchanged from 014. `tests/contract/test_library_api_milling_locale.py`
is rewritten per FR-007; `tests/static/` gains an enforcement test for FR-001/SC-001 (no console string
resolved from a core-owned lookup, except the inherited `console.missing_dependency*` exception).

**Target Platform**: Unchanged — library plus interactive console, OS-independent.

**Project Type**: Single project, `src/` layout, library + CLI (unchanged from 014).

**Constraints**: No behaviour change to English-locale output (SC-002, SC-003); coverage stays ≥90%;
every Principle IX gate must pass; no release cut by this feature (spec Assumptions, mirroring 014's
FR-018).

**Scale/Scope**: One new catalogue module (`mfgparams/console/locales/en.py`) and one new loader
(`mfgparams/console/i18n.py`, structurally identical to `mfgparams/i18n.py`); ~60 `cli.*`/
`material_type.*` entries move from `mfgparams/locales/en.py` into it; `console/cli.py`'s `translate`
import point moves from `mfgparams.i18n` to `mfgparams.console.i18n`; `ErrorInfo` gains two fields,
touching every one of `validation.py`'s ~25 `ErrorInfo(...)` call sites plus every operation's
`calculate()` that constructs one directly.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Verdict |
|---|---|---|
| I. Code Quality | The two i18n loaders (core, console) are structurally identical; research.md #1 records why duplication is chosen over a shared abstraction. | PASS |
| II. Testing | `ErrorInfo`'s new fields touch every validation call site; each existing test asserting `.message` needs no change (FR-005 keeps it English), but new tests cover `.message_key`/`.kwargs` and the console's re-rendering path (SC-006). Coverage threshold unchanged. | PASS |
| III. Calculation Robustness | No calculation logic touched — this feature is confined to error/message plumbing. | PASS |
| IV. Packaging & Versioning | No new dependency; no packaging metadata change (catalogues are already-included Python modules, not package-data files). Breaking change to `ErrorInfo`'s shape accumulates toward the same 2.0.0 as 014 (spec Assumptions). | PASS |
| V. Resource-Constrained Compatibility | Two small dict-based catalogues instead of one; negligible memory/import cost, no new dependency. | PASS |
| VI. Extensibility by Design | A future non-English catalogue is added as one new module per side (core or console), consistent with the existing pattern — no code change. | PASS |
| VII. Documentation & Publishing | FR-008 requires updated contributor documentation on where to add a string; Sphinx build unaffected (no public API doc beyond `ErrorInfo`'s docstring, which gains the two new fields). | PASS |
| VIII. Internationalization | This feature *is* Principle VIII's catalogue/key-independence rule applied one level deeper: `message_key` is exactly the "stable identifier independent of wording" the principle already requires internally, now exposed so the console can use it too. | PASS |
| IX. Automated Gates | No gate added, removed, or reconfigured. | PASS |
| X. Licensing & Author Rights | Unaffected. | PASS |
| XI. Multi-Agent Consistency | No agent-integration file changes anticipated; `/speckit-converge` re-checks per 014's precedent (skill docs describing the catalogue split, if any, get the same scrutiny 014's FR-017 required). | PASS |
| XII. Long-Lived Feature Branches | Not triggered: scope is one new catalogue module, one new loader, and an additive `ErrorInfo` change — smaller than 014, which itself didn't trigger this principle. Single PR to `main`. | N/A |

**Post-Phase 1 re-check**: PASS. See [research.md](./research.md) #3 for the one place this plan
revisits Principle VIII's "no duplication" instinct against FR-005's requirement that core stay
self-sufficient — the two are reconciled, not in tension, once `message_key` is understood as
metadata rather than translated text.

## Project Structure

### Documentation (this feature)

```text
specs/015-console-i18n-relocation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── error-info-contract.md
│   └── catalogue-ownership-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/mfgparams/
├── i18n.py                          # unchanged mechanism; now core-only scope
├── locales/
│   └── en.py                        # error.*, warning.*, notice.*, console.missing_dependency*
│                                     #   — cli.*/material_type.* entries move out (FR-001), except
│                                     #   three cli.label.* keys core's own error text embeds via
│                                     #   translate(); those stay in BOTH catalogues (found during
│                                     #   T007, FR-004's second documented exception — see spec.md
│                                     #   Assumptions, research.md #4, contracts/catalogue-ownership
│                                     #   -contract.md)
├── models.py                        # ErrorInfo gains message_key, kwargs (FR-005b)
├── validation.py                    # every ErrorInfo(...) call site passes message_key + kwargs
├── registry.py, registry_config.py  # unchanged (materials_load_notice already key+kwargs-shaped;
│                                     #   WorkpieceMaterial.translations untouched, FR-003)
└── console/
    ├── i18n.py                      # NEW — same loader mechanism, scoped to console/locales/*
    ├── locales/
    │   └── en.py                    # NEW — cli.*, material_type.* entries (moved from core)
    └── cli.py                       # translate import moves to mfgparams.console.i18n;
                                      #   error display re-renders via message_key+kwargs when
                                      #   the active locale has a console-catalogue entry (FR-005a)

tests/
├── contract/
│   └── test_library_api_milling_locale.py   # rewritten per FR-007
├── static/
│   └── test_console_catalogue_ownership.py  # NEW (FR-001/SC-001) — every mfgparams.console
│                                             #   string resolves via mfgparams.console.i18n,
│                                             #   not mfgparams.i18n, except the inherited
│                                             #   console.missing_dependency* exception
└── unit/
    └── test_error_info_rerendering.py       # NEW (SC-006) — a code shared by two templates
                                              #   (INVALID_DIAMETER zero/max) re-renders distinctly
```

**Structure Decision**: Single project, unchanged from 014. The console gets its own `i18n.py` +
`locales/` pair, mirroring core's exactly — a deliberate, reviewed duplication (research.md #1)
rather than a shared abstraction, because the two catalogues have different content and different
lifecycles (core's is a public-API compatibility surface; console's is presentation and can change
freely).

## Complexity Tracking

*No Constitution Check violations require justification — see Constitution Check verdicts above.*
