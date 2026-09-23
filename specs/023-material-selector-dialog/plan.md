# Implementation Plan: Multi-Notation Metal Material Selector Dialog

**Branch**: `023-material-selector-dialog` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-material-selector-dialog/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Replace the metal Material field's current Left/Right-cycling `RadioRow` interaction with a
dedicated, centered floating dialog (matching the existing operation-window `Float`/`Frame`/
`Shadow` pattern already used in `app.py`) offering three side-by-side, independently
searchable columns — common name (locale-translated, per Clarification 1), EN material
number, and shortened designation — sharing one row highlight, opened by Enter on the metal
Material row and closed by Enter (confirm) or Escape (cancel, no change). The two new
identifying columns require two new optional fields on `WorkpieceMaterial` and the materials
TOML schema; because `RawRegistryEntry.fields` already passes through arbitrary TOML keys
generically (`registry_config.py::_parse_entries`), no config-parsing code changes — only
`registry.py`'s `_to_material` converter and `_STICKY_FIELDS` need updating. This is an
interactive TUI feature (Constitution Principle XIII): its correctness (does the dialog
render, position, and respond to keys correctly on a real terminal) cannot be confirmed by
this project's state/text-only TUI test strategy, so a developer/reviewer-performed manual
walkthrough is a required, separate `tasks.md` item.

## Technical Context

**Language/Version**: Python >=3.9 (existing project requirement, `pyproject.toml`)

**Primary Dependencies**: `prompt-toolkit>=3.0,<4.0` (existing `console` extra); no new
dependency — reuses `Float`/`FloatContainer`/`ConditionalContainer`/`Frame`/`Shadow`/`Box`
already imported in `app.py`.

**Storage**: N/A for runtime state (in-memory); the bundled/user materials TOML file
(`src/mfgparams/data/materials.toml`, or a `--materials-config PATH` override) gains two new
optional per-entry keys, `material_number` and `short_notation`.

**Testing**: `pytest` — new unit tests for the picker's filter/navigation logic (pure
functions, no TUI harness needed) and the `registry.py`/`registry_config.py` schema change;
existing `DummyOutput`-based TUI integration tests extended for the new Float's open/close/
focus-transfer wiring; plus a required manual walkthrough per Principle XIII (rendering,
color, and layout correctness are outside what this project's TUI tests can assert).

**Target Platform**: Any terminal `mfgparams` already targets (Principle V), specifically
including the 80x25 floor from 022-tui-min-size-25x80 — the dialog's width/height budget
must fit within that floor alongside the already-open operation window it layers above.

**Project Type**: Single project (existing `src/mfgparams` console/TUI application) — no new
project or module boundary; one new module inside the existing `console/tui/` package.

**Performance Goals**: N/A as a throughput target — `registry.py::_build_registry_cached` is
already `functools.cache`d, so re-deriving the filtered candidate list on every keystroke costs
one cheap in-memory filter over an already-loaded snapshot (no TOML re-parsing), matching
`app.py::_current_pane_rows`'s existing per-render-recompute approach for the same reason.
Scale stays small enough (see Scale/Scope) that no additional memoization is needed.

**Constraints**: Keyboard-only (no pointer/mouse interaction, consistent with the rest of the
console TUI); must not regress any existing pane/dropdown/exit-confirm key binding (`app.py`'s
`_escape_body` in particular is a shared catch-all that must be scoped to exclude this new
dialog's own focus state, mirroring how it already excludes `view.confirming_exit`).

**Scale/Scope**: The bundled default registry currently ships 6 metal materials
(`src/mfgparams/data/materials.toml`); a user-supplied `--materials-config` file can add an
unbounded number more (Constitution VI/Principle V still bounds this to what a legacy-hardware
terminal session can reasonably hold in memory, same as today's unfiltered material list). The
design must read correctly at both today's small bundled count and a much larger user-supplied
one — three new optional fields on `WorkpieceMaterial`, one new state dataclass, one new
rendering/interaction module, no new public library API.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| I. Code Quality | Yes | New picker logic (filter/navigate/edit-query) lives in one new module with a single responsibility, not folded into `split_pane.py`'s existing row engine or `app.py`'s already-large key-binding block. PASS. |
| II. Testing Standards | Yes | Filter/navigation/highlight logic is pure and unit-testable without a TUI harness (nominal, boundary — empty query, no matches, material missing a notation — and known-value cases). Registry conversion of the two new optional fields gets unit tests mirroring `material_type`'s existing warn-and-continue tests. PASS, pending task creation. |
| III. Calculation Robustness | No | No numeric calculation logic touched; `material_number`/`short_notation` are opaque display/search strings, not computed values. N/A. |
| IV. Packaging & Versioning | No | No public library API change — `WorkpieceMaterial` gains two new dataclass fields with defaults (`None`), which is additive and backward-compatible for any existing caller/config file. N/A. |
| V. Resource-Constrained Compatibility | Yes | Reuses the already-cached registry snapshot (see Performance Goals); the dialog is one more small `Float`, not a new heavy dependency or unbounded-growth data structure. PASS. |
| VI. Extensibility | Yes | The new picker lives behind its own module boundary (mirroring `machining_menu.py`'s precedent for the Machining tree dropdown) rather than being wedged into `split_pane.py`'s shared row engine, so a future operation reuses it the same way drilling/turning/milling already share `split_pane.py`. PASS. |
| VII. Documentation & Publishing | No | No new public-facing docs surface beyond the existing generated Sphinx docs picking up the two new `WorkpieceMaterial` fields' docstrings automatically. N/A. |
| VIII. Internationalization | Yes | All new labels/messages (column headers, empty-state text) go through the existing `translate()`/message-catalog mechanism (FR-013); the common-name column reuses `WorkpieceMaterial.display_name(locale)` — already the project's existing i18n mechanism for material names (Clarification 1) — introducing no new translation surface of its own. PASS. |
| IX. Automated Quality/Security Gates | Yes | Existing CI gates (lint, type-check, complexity, security, tests) apply unchanged; scope is well below any complexity/MI threshold. PASS. |
| X. Licensing | No | N/A. |
| XI. Multi-Agent Consistency | No | No skill/agent-instruction file touched. N/A. |
| XII. Long-Lived Feature Branches | No | Single PR-sized change (one new module, two dataclass fields, one schema doc, key-binding wiring); no long-lived integration branch needed. N/A. |
| XIII. Manual Verification (NON-NEGOTIABLE) | Yes | This is exactly the case this principle targets: a new interactive floating dialog whose correctness (position/size within the 80x25 floor, column alignment, highlight visibility, focus transfer in and out) cannot be observed by this project's state/text-only TUI test strategy. `tasks.md` (Phase 2) MUST carry a distinct, named manual-verification task — walking `quickstart.md`'s scenarios on a real terminal for drilling, turning, and milling — separate from and in addition to the automated test tasks, completed (with any layout fixes it surfaces) before the feature is considered done. GATE SATISFIED BY DESIGN — enforced at the tasks phase, not skippable here. |

No violations requiring justification. Complexity Tracking table below is not needed.

**Post-Phase-1 re-check**: Design work (research.md, data-model.md, contracts/, quickstart.md)
surfaced one additional, precedent-driven decision not yet reflected above: `material_number`/
`short_notation` must be added to `registry.py::_STICKY_FIELDS` alongside `material_type`
(research.md Decision 5) — without this, a pre-existing user materials-config override of a
bundled metal material would silently drop the newly-added notations, the exact regression
class `material_type` was made sticky to prevent (verified by reading
`registry_config.py::merge_entries`'s wholesale-replace-then-sticky-carryover logic directly,
not assumed). This is a `registry.py` edit, not a new principle concern — Constitution Check
gate re-confirmed PASS with no new violations.

## Project Structure

### Documentation (this feature)

```text
specs/023-material-selector-dialog/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mfgparams/
├── registry.py                          # WorkpieceMaterial: +material_number, +short_notation
│                                          # (both `str | None = None`); _to_material: extract +
│                                          # validate (warn-and-continue, mirroring material_type);
│                                          # _STICKY_FIELDS: add both new keys (research.md Decision 5)
├── registry_config.py                    # NO CHANGE — RawRegistryEntry.fields already passes
│                                          # unknown TOML keys through generically (verified by
│                                          # reading _parse_entries directly)
├── data/materials.toml                   # Bundled data-entry task: populate material_number/
│                                          # short_notation for as many of the 6 bundled metal
│                                          # materials as have a known EN/DIN designation (out of
│                                          # scope for interaction-behavior tasks per spec.md
│                                          # Assumptions, but needed for quickstart.md to have real
│                                          # data to search)
└── console/
    ├── locales/en.py                     # NEW tui.material_picker.* keys (FR-013)
    └── tui/
        ├── material_picker.py            # NEW module: MaterialPickerState, open_state(),
        │                                  # candidates() (FR-004/FR-010 filter), move_highlight(),
        │                                  # cycle_column(), render() — mirrors machining_menu.py's
        │                                  # precedent as an own-module dropdown/dialog, not folded
        │                                  # into split_pane.py. Query-text editing itself (FR-003)
        │                                  # is NOT a function here — it's done inline in app.py's
        │                                  # own key-binding handlers (`_material_picker_char`/
        │                                  # `_material_picker_backspace`, via a
        │                                  # `_MATERIAL_PICKER_QUERY_ATTR` lookup), the same way
        │                                  # every other pane field's char/backspace editing already
        │                                  # works in that file (tasks.md T046 correction — an
        │                                  # earlier draft of this row named two module functions,
        │                                  # `edit_active_query()`/`backspace_active_query()`, that
        │                                  # were never actually added here)
        ├── app.py                        # _ViewState: +material_picker field; build_app(): new
        │                                  # material_picker_control + centered Float (Box/Shadow/
        │                                  # Frame, matching operation_window's pattern); new
        │                                  # Conditions (trigger, focused) and key bindings (up/down/
        │                                  # left-right+tab/backspace/char/enter/escape); _escape_body's
        │                                  # filter extended to exclude this new focus state. The
        │                                  # existing pane_radio_focused Condition is left unmodified —
        │                                  # Left/Right/Space keep cycling the metal Material row too,
        │                                  # additive not exclusive with Enter (research.md Decision 3,
        │                                  # Session 2026-09-23 amendment)
        └── screens/
            ├── split_pane.py               # render_bottom_bar: swaps the generic pane hint for
            │                              # tui.material_picker.pane_hint (FR-014) when the metal
            │                              # Material row is selected (research.md Decision 9,
            │                              # Session 2026-09-23 amendment)
            ├── drilling.py                # NO CHANGE — Material row's `options`/`on_select`
            │                              # (already built from list_materials/get_material) are
            │                              # reused unchanged as the picker's own candidate source
            ├── turning.py                 # NO CHANGE, same reason
            └── milling.py                 # NO CHANGE, same reason

tests/
├── unit/console/tui/test_material_picker.py       # NEW — pure filter/navigation/query-edit logic
├── unit/shared/test_registry_material_notations.py # NEW — material_number/short_notation parse,
│                                              # validation, and sticky-field merge behavior
│                                              # (mirrors the existing test_registry_material_types.py)
└── integration/test_tui_material_picker.py    # NEW — Float open/close, focus transfer, Enter/
                                              # Escape outcomes via the existing DummyOutput harness
```

**Structure Decision**: Single project (existing layout, Option 1). One new module
(`console/tui/material_picker.py`) added inside the existing TUI package, following the
`machining_menu.py` precedent for a self-contained dropdown/dialog; `registry.py` gains two
additive dataclass fields and a converter/sticky-field update; `app.py` gains wiring only
(new `Float`, `Condition`s, key bindings) — no existing screen module (`drilling.py`/
`turning.py`/`milling.py`) needs to change, since their `rows_for` already builds the exact
`(name -> display_label)` option set the picker's candidate list reuses.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — this table is intentionally empty.
