# Contract: Material Selector Dialog — UI Interaction

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This is the keyboard-interaction contract for the floating dialog (FR-001–FR-011), applying
identically across drilling, turning, and milling (FR-012). It is scoped to a metal Material
row only (`session_state.material_type == "metal"`); other material types are unaffected.

## Preconditions to open

- An operation window is open (`ui.open_operation is not None`).
- The left pane's currently-selected row is the Material field.
- That operation's `session_state.material_type == "metal"`.
- No other floating dialog (Exit confirm, a bar dropdown) currently holds focus.

Enter opening this dialog is **additive**, not exclusive: the metal Material row also still
cycles one material at a time with Left/Right/Space, exactly like any other radio field on the
pane — Enter gives it a second, independent way to change the material, it does not remove the
first (Session 2026-09-23 spec amendment). While the row is selected and the dialog is not
open, the pane's bottom hint line names this extra Enter behavior where there is room for one
(FR-014) — see `render_bottom_bar` in `split_pane.py`.

## Key contract while the dialog is open

| Key | Effect | Requirement |
|---|---|---|
| Up | Move row highlight to the previous candidate in the current filtered list | FR-005 |
| Down | Move row highlight to the next candidate in the current filtered list | FR-005 |
| Left, Shift+Tab | Move active search-column focus one column left (wraps common → short) | FR-006, research.md #7 |
| Right, Tab | Move active search-column focus one column right (wraps short → common) | FR-006, research.md #7 |
| Any printable character | Append to the active column's search text; candidate list and highlight re-filter | FR-003, FR-004 |
| Backspace | Remove the last character from the active column's search text; re-filter | FR-003, FR-004 |
| Enter, candidate highlighted | Set the operation's material to the highlighted candidate; close the dialog; return focus to the pane | FR-007 |
| Enter, no candidate highlighted (empty list) | No-op; dialog stays open | FR-008 |
| Escape | Close the dialog; do not change the operation's material; return focus to the pane | FR-009 |

## Opening/closing side effects

- **Open**: candidate list resets to the full metal-material list for the current operation;
  all three search fields reset to empty; the row for the material already selected (if any,
  and still present in the full list) starts highlighted — otherwise no row is highlighted
  (FR-011, Clarification 2).
- **Close (confirm or cancel)**: dialog state is discarded entirely; reopening always starts
  fresh per the Open rule above — no memory of the last search carries over (spec.md Edge
  Cases).

## Display contract

- Three columns, side by side, one row per candidate material: common name (locale-translated
  per `display_name(display_locale)`, Clarification 1), EN material number, shortened
  designation.
- A material missing a value for the material-number or shortened-designation column renders
  that cell blank (FR-010) and is excluded from the candidate list the moment a non-empty
  search is entered in that column (FR-010).
- All column headers and any empty-state message are sourced from the translatable message
  catalog (FR-013) under the `tui.material_picker.*` key namespace.

## Non-goals (explicitly out of contract)

- Mouse/pointer interaction (spec.md Assumptions: keyboard-only).
- Any behavior for non-metal material types — the existing `RadioRow` Left/Right/Space cycle
  is untouched there, and no dialog is ever offered.
- Replacing the metal Material row's own Left/Right/Space cycle — see the additive note under
  Preconditions above.
- Persisting search text or highlight across a dialog close/reopen cycle.
