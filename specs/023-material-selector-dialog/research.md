# Research: Multi-Notation Metal Material Selector Dialog

No `NEEDS CLARIFICATION` markers remain in the Technical Context — the two business-level
ambiguities were already resolved in `spec.md`'s Clarifications session. The decisions below
are plan-level (how to build it inside this specific codebase), each grounded in reading the
actual current source rather than assumed.

## 1. Where the picker's own state lives

**Decision**: Add `material_picker: MaterialPickerState | None = None` to `app.py`'s
`_ViewState` — not to `OperationScreen`.

**Rationale**: `_ViewState`'s own docstring documents it as "pure UI-presentation state,
deliberately *not* part of `SessionUI`"; the existing Exit-confirmation dialog
(`confirming_exit: bool`, `confirm_selected: Literal["yes","no"]`) is the closest precedent —
a small, flat, singleton-style dialog-open state, not nested inside the object it's triggered
from. Critically, `OperationScreen` is the exact input to `app.py::_current_pane_rows`'s own
memoization cache key (`(id(op), id(op.session_state), op.selected_field, op.field_buffer,
tuple(vars(op.session_state).items()), ui.locale)`), whose docstring already documents two
past bugs from that cache key missing a source of change. Adding a new `OperationScreen` field
would require also adding it to that fingerprint tuple — an easy-to-miss step exactly the kind
of trap that cache's own comments warn about. Living on `_ViewState` (which
`_current_pane_rows` never reads) sidesteps that risk entirely rather than requiring a new,
easy-to-forget cache-key edit.

**Alternatives considered**: Nesting on `OperationScreen` (rejected: cache-key risk above,
and the picker's own lifetime — reset every open, discarded every close — matches
`_ViewState`'s dialog-state precedent more closely than `OperationScreen`'s "session state that
survives a body change" role, per `_ViewState`'s docstring, FR-012).

## 2. Where the picker's logic/rendering lives

**Decision**: New module `src/mfgparams/console/tui/material_picker.py`.

**Rationale**: `machining_menu.py` already establishes the precedent of a self-contained
dropdown/dialog (state dataclass + pure logic functions + a `render_*` function) living in its
own module rather than inside `split_pane.py`'s shared row engine or `app.py`'s already-large
`build_app`. `split_pane.py`'s own docstring scopes it to "the left/right split-pane engine ...
Left/Right/Space cycle it and commit immediately" — the picker's interaction model (multi-
column search, shared row highlight across columns, Enter/Escape as confirm/cancel) is a
different shape entirely and does not belong inside that engine. Constitution Principle VI
(Extensibility) favors a new, clearly-bounded module over widening `split_pane.py`'s existing
contract.

**Alternatives considered**: Extending `split_pane.py` with a new `Row` variant (rejected: the
picker isn't a pane row at all — it's a modal float layered *above* the pane, like the
Machining tree/Exit-confirm dialogs, not one more line inside it).

## 3. How the metal Material row triggers the dialog without breaking the existing `RadioRow` contract

**Decision**: No new `Row` subtype. `drilling.py`/`turning.py`/`milling.py`'s `rows_for` keep
building the Material field as a `RadioRow` exactly as today (unchanged code). In `app.py`, add
a new `pane_material_picker_trigger` Condition (`_pane_is_focused() and` current row is the
Material `RadioRow` `and` `ui.open_operation.session_state.material_type == "metal"`) bound to
`enter` — opening the dialog. This is additive, not exclusive: `pane_radio_focused` is left
unmodified (it still matches every `RadioRow` including the metal Material row), so
Left/Right/Space keep cycling that row one material at a time exactly as before, and `enter`
simply gives it a second, independent behavior on top (Session 2026-09-23 spec amendment,
overriding an earlier version of this decision that had narrowed `pane_radio_focused` to
exclude the row and disable its cycling — reverted after direct user feedback that both paths
must stay available). Non-metal material types (e.g. wood) are unaffected either way — no
`pane_material_picker_trigger` match is possible for them, so they only ever cycle.

**Rationale**: Reuses the exact `(name -> display_label)` option set `rows_for` already
builds for the Material row as the picker's candidate source (no duplicated material-listing
logic), while the trigger/interaction split lives entirely in `app.py`'s existing
Condition/key-binding layer, which already dispatches by row type and focus state this way for
every other row/dialog.

**Alternatives considered**: A new `MaterialPickerRow` dataclass mirroring `RadioRow`
(rejected: `rows_for` already produces everything the picker needs from the existing
`RadioRow`; a parallel type would only exist to be pattern-matched in `app.py`, adding an
abstraction with no behavior of its own).

## 4. Closing/cancelling without breaking the existing generic Escape handler

**Decision**: Extend `_escape_body`'s filter from
`not on_bar() and not view.confirming_exit` to
`not on_bar() and not view.confirming_exit and view.material_picker is None`, and add a
dedicated `material_picker_focused`-gated Escape binding (registered the same way
`_exit_confirm_cancel` is), which simply clears `view.material_picker` and returns focus to
`left_control` — no material-selection change, matching FR-009.

**Rationale**: Read `_escape_body`'s actual body directly: it branches on `on_pane()` and
otherwise falls back to "closing a bar entry's dropdown", which is the *wrong* behavior for
this dialog (it would jump focus all the way to the bar, past the still-open operation
window). The Exit-confirmation dialog already solves the identical problem — its own comment
at the Escape binding explicitly says it "gets its own dedicated Escape binding ... distinct
from every other floating window since it has no `body_mode`/`on_pane()` state of its own to
fall back on" — and works today specifically because `_escape_body`'s filter excludes it.
Mirroring that exact, working pattern (rather than inventing a new one) is both lower-risk and
consistent with the codebase's own established approach to this exact class of problem.

**Alternatives considered**: Relying on `_escape_body`'s existing `on_pane()` branch alone
(rejected: verified by reading the code that this branch's "land back at the operation pane"
behavior is only reachable when focus is still on `left_control`; the picker moves focus to
its own `material_picker_control`, so `on_pane()` would already be `False` when Escape is
pressed inside the dialog, hitting the wrong branch).

## 5. Sticky-field handling for the two new registry keys

**Decision**: Add `material_number` and `short_notation` to `registry.py::_STICKY_FIELDS`
alongside the existing `"material_type"`.

**Rationale**: Read `registry_config.py::merge_entries` directly: a user override entry
replaces the bundled entry's `fields` dict *wholesale*, except for keys listed in
`sticky_fields`, which are carried over from the bundled entry when the user entry omits them.
`material_type` was made sticky for exactly this scenario (its own docstring/comment: "so that
a config file written before that key existed keeps its materials in their original
categories instead of silently falling back to `'uncategorized'`"). The two new notation
fields are the same shape of problem: a pre-existing user config that already overrides, say,
"Mild Steel"'s `reference_cutting_speed` predates `material_number`/`short_notation` by
definition and would otherwise silently lose the bundled notations for that material the
moment this feature ships.

**Alternatives considered**: Leaving them non-sticky (rejected: reproduces a regression class
this codebase has already been burned by once, per `material_type`'s own precedent/rationale).

## 6. Validation policy for the two new fields

**Decision**: Both fields are optional strings. If present, non-string, or containing a
forbidden Unicode category (reusing `_FORBIDDEN_NAME_CATEGORIES`'s existing
control-character/line-separator check — these values are rendered as picker cell text and
searched character-by-character, the same injection/corruption risk `name`/`material_type`
already guard against), record a validation issue (warn-and-continue, mirroring
`material_type`'s existing policy) and treat the field as absent (`None`) rather than raising
`RegistryConfigError`. Never required.

**Rationale**: Consistent with this module's existing two-tier policy: the three *numeric*
reference fields are hard-required (`RegistryConfigError` on missing/invalid, since a
calculation cannot proceed without them — Constitution Principle III), while classification/
display metadata (`material_type`) is soft-validated (warn, fall back, keep the material
usable). `material_number`/`short_notation` are display/search metadata, not calculation
inputs — the same tier as `material_type`, not the numeric tier.

**Alternatives considered**: Enforcing a literal EN-number/DIN-shortname format (e.g. regex
`^\d\.\d{4}(\+\w+)?$`) (rejected: spec.md's own Assumptions leave exact population as a
separate data-entry concern, not an interaction-behavior requirement; a format check would
also reject legitimate real-world variance in how these standards are written and gains
nothing the substring search itself needs).

## 7. Column-switch key binding

**Decision**: Inside the dialog, Left/Right arrow keys AND Tab/Shift+Tab both cycle which of
the three search columns is active (wrapping); Up/Down always move the shared row highlight,
never column focus.

**Rationale**: Resolves spec.md's Assumptions item ("the exact key is a presentation detail
left to implementation/design review"). Left/Right carry no conflicting meaning inside this
modal (the outer pane's Left/Right-nudge/cycle bindings are gated on `pane_focused`, which is
`False` once focus moves to `material_picker_control` — verified against the same
Condition/focus pattern documented in Decision 3/4), so reusing them for column-switching adds
no new key vocabulary for the user to learn. Tab/Shift+Tab are offered as a second path since
they're the more conventional cross-field navigation key in most textual UIs and cost nothing
to also bind.

**Alternatives considered**: Tab-only (rejected: less discoverable than arrow keys in a
terminal app whose every other dialog is arrow-key-driven); a fourth "which column" indicator
requiring a dedicated activation key (rejected: unnecessary complexity for a 3-item cycle).

## 8. Candidate list performance

**Decision**: Recompute the filtered candidate list from scratch on every keystroke/render;
no dedicated memoization for the picker itself.

**Rationale**: `registry.py::_build_registry_cached` is already `functools.cache`d — repeated
`list_materials`/`get_material` calls cost one dict/list lookup against an in-memory snapshot,
not a re-parse of the TOML file. `app.py::_current_pane_rows` already recomputes its own,
larger row list on every render for the identical reason (documented in its own docstring: the
registry lookups underneath are cheap; only the *row-building/translate() calls* were worth
caching, and only because they ran up to 5x per keystroke). The picker's candidate list is a
single filter pass over a handful (bundled: 6) to at most a few hundred (large user config)
materials — well under any threshold that made the existing cache worthwhile.

**Alternatives considered**: A cache keyed on the three query strings (rejected as premature —
no measured performance problem to justify the added state/invalidation surface; can be added
later if a future large-registry user report shows otherwise).

## 9. Where the "Enter opens detailed search" hint lives (FR-014, Session 2026-09-23 amendment)

**Decision**: `split_pane.py::render_bottom_bar` — the shared per-operation status/hint row
already at the bottom of every operation window — swaps its generic `tui.pane.hint` line for a
`tui.material_picker.pane_hint` line specifically when the currently-selected field is the
metal Material row (`screen.selected_field is FieldId.MATERIAL and
screen.session_state.material_type == "metal"`), reverting to the generic hint otherwise.

**Rationale**: This row already exists on every operation screen precisely to hold a one-line
keyboard hint (or, when set, `OperationScreen.status`); reusing it needs no new UI element and
naturally disappears once the user moves to a different field, matching FR-014's "wherever the
surrounding UI already has a place for such a hint, not a MUST that forces one" framing. The
swapped-in text (`"↑↓ move   ←→/Space change   ↵ detailed search   Esc back"`) stays within the
generic hint's existing length/style (terse, symbol-led) so it fits the same one-line budget
without wrapping on an 80-column terminal.

**Alternatives considered**: Appending to the Material row's own label text in `render_left_pane`
(rejected: that row is shared code across every operation and every material type, and a label
change would show even for non-metal materials or run at a width the row wasn't budgeted for);
a `status`-style transient message (rejected: `status` is reserved for FR-006b's unparseable-
number error and would be indistinguishable from one, plus it would disappear rather than
persist while the field stays selected).
