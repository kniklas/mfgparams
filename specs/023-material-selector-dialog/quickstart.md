# Quickstart: Multi-Notation Metal Material Selector Dialog

This is the Constitution Principle XIII manual-verification guide: a `tasks.md` task MUST walk
every scenario below on a real terminal before this feature is considered done. Automated
tests (unit tests for the filter/navigation logic, integration tests for the Float's open/
close/focus wiring) cannot confirm layout, color, or highlight visibility — only a human
looking at a real terminal can.

## Prerequisites

- A real terminal at least 80 columns x 25 lines (the 022-tui-min-size-25x80 floor) — not a
  piped/non-TTY session.
- `mfgparams` installed with the `console` extra (`pip install -e ".[console]"` from the repo
  root, or however this repo's contributor docs currently recommend).
- A small test materials-config file with *additional* sample notation data, so Scenarios 2–4
  below have more than one grade to search — the bundled `data/materials.toml` already
  populates `material_number`/`short_notation` on one entry, `S235JR Structural Steel` (its own
  name states the specific grade the numbers describe, unlike the other, generic-family bundled
  metals — plan.md's Project Structure). Entries below follow the same named-after-its-grade
  pattern, per contracts/materials-config-schema-delta.md's example. Save this as
  `/tmp/mfgparams-quickstart-materials.toml` (or your OS equivalent):

  ```toml
  [[materials]]
  name = "Chromoly Steel"
  material_type = "metal"
  reference_cutting_speed = 20.0
  reference_feed_per_rev = 0.18
  specific_cutting_force = 2100.0
  unit_system = "metric"
  material_number = "1.7225"
  short_notation = "42CrMo4+N"

  [[materials]]
  name = "Unlabeled Alloy"
  material_type = "metal"
  reference_cutting_speed = 30.0
  reference_feed_per_rev = 0.22
  specific_cutting_force = 1800.0
  unit_system = "metric"
  # Deliberately no material_number/short_notation — exercises FR-010's blank-cell case.
  ```

## Setup

```bash
mfgparams --materials-config /tmp/mfgparams-quickstart-materials.toml
```

## Scenario 1 — Open the dialog, search by common name, select, close (User Story 1)

1. From the menu bar, open **Machining → Drilling**.
2. Navigate (Down) to the **Material type** row; confirm it shows `metal` (cycle with
   Left/Right/Space if it doesn't default there).
3. Navigate (Down) to the **Material** row.
4. Look at the hint line beneath the two panes (below the horizontal divider).
   - **Expect**: it reads `↑↓ move   ←→/Space change   ↵ detailed search   Esc back` (FR-014,
     `tui.material_picker.pane_hint`), rendered on one line, not clipped and not overlapping
     the divider above it or the panes themselves — this exact rendering is only checkable on a
     real terminal (Constitution Principle XIII), not by the automated tests, which only assert
     the underlying text value.
5. Press **Right** (or **l**) twice, then **Left** (or **h**) once — do **not** press Enter yet.
   - **Expect**: the Material row's shown value cycles one bundled metal material at a time on
     each press — unset → **Mild Steel** (1st Right) → **Stainless Steel** (2nd Right) → back to
     **Mild Steel** (the Left, cycling backward by one from Stainless Steel) — exactly like every
     other radio field on the pane — **no dialog opens**, confirming Enter's detailed-search
     window is additive, not a replacement for this ordinary cycling (Session 2026-09-23 spec
     amendment).
6. Press **Enter**.
   - **Expect**: a centered floating dialog appears, showing three columns (common name /
     material number / shortened designation) side by side, listing every metal material —
     the 7 bundled defaults (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium,
     S235JR Structural Steel) plus this fixture's 2 additions (Chromoly Steel, Unlabeled Alloy)
     — since step 5 already cycled the Material row to "Mild Steel" (a value present in the
     unfiltered list), **expect that row highlighted** — not the empty-highlight case
     data-model.md's Open transition describes for a field that was never set.
7. Type `steel` (common-name column, the default active column).
   - **Expect**: the list narrows to "Mild Steel", "Stainless Steel", "S235JR Structural Steel",
     and "Chromoly Steel" (all four contain "steel"); every other material, including
     "Unlabeled Alloy", drops out.
8. Press **Down** once.
   - **Expect**: the highlight moves from "Mild Steel" (the first filtered row — typing a query
     always re-highlights the first match, per data-model.md's Edit query transition, regardless
     of what step 6 left highlighted) to "Stainless Steel", the second filtered row.
9. Press **Enter**.
   - **Expect**: the dialog closes; the Material row now shows "Stainless Steel"; focus is back
     on the left pane; the hint line from step 4 is showing again (the Material row is still
     selected, the dialog is just closed).

## Scenario 2 — Search by EN material number (User Story 2)

1. Re-open the Material picker (Enter on the Material row).
   - **Expect**: the row for whatever you selected in Scenario 1 starts highlighted, all three
     search fields are empty, and the full 9-material list (7 bundled + this fixture's 2) is
     shown (Clarification 2, FR-011).
2. Move column focus to the material-number column (Right or Tab, once).
3. Type `1.72`.
   - **Expect**: only "Chromoly Steel" (`1.7225`) remains.
4. Press **Enter**.
   - **Expect**: "Chromoly Steel" becomes the selected material.

## Scenario 3 — Search by shortened designation, blank cells, no-match state (User Story 3, Edge Cases)

1. Re-open the picker (which starts back on the common-name column, per FR-011). Move column
   focus to the shortened-designation column: **Right**/**Tab** twice, or **Left**/**Shift+Tab**
   once — the column order wraps, so going left from common name reaches shortened designation
   directly in a single press.
2. Type `42CrMo4`.
   - **Expect**: only "Chromoly Steel" remains.
3. Clear that column's text (Backspace to empty), then type `zzz` into it.
   - **Expect**: the list becomes empty (no candidates); no row is highlighted.
4. Press **Enter** while the list is empty.
   - **Expect**: nothing happens — the dialog stays open (FR-008).
5. Clear the search text (Backspace to empty again) and move to the common-name column; type
   `unlabeled`.
   - **Expect**: "Unlabeled Alloy" appears with its material-number and shortened-designation
     cells visibly **blank**, not showing a placeholder or an error (FR-010).
6. Press **Escape**.
   - **Expect**: the dialog closes; the material selected at the end of Scenario 2
     ("Chromoly Steel") is unchanged — the blank-cell material was never confirmed (FR-009).

## Scenario 4 — Consistency across operations (FR-012, SC-004)

Repeat all of Scenario 1's steps (open Machining → **Milling**, then separately **Turning**
instead of Drilling), confirming the dialog — and the step 4/5 hint-line and Left/Right-cycling
checks — look and behave identically in each: same three columns, same key bindings, same
open/close behavior, same hint text, same direct-cycling fallback.

## Scenario 5 — Fits the 80x25 floor (Constitution Principle XIII / 022-tui-min-size-25x80)

With the terminal at exactly 80 columns x 25 lines, repeat Scenario 1. Confirm the dialog does
not clip, overlap the menu bar, or overflow the terminal's right/bottom edge, and that its
Shadow/Frame border renders fully inside the visible area — the exact class of bug
022-tui-min-size-25x80's own manual verification (not automated tests) caught for an unrelated
dropdown (see that feature's plan.md Post-implementation correction).

## Sign-off

All five scenarios MUST pass on a real terminal before the corresponding `tasks.md`
manual-verification task is marked complete. Record any layout fix required by Scenario 5 in
the same task, per Constitution Principle XIII.
