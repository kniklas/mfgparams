# Contract Delta: Console TUI — Machining Menu Auto-Hide

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)
(User Story 3, FR-011/FR-012/FR-013)

Extends `specs/018-tui-splitpane-redesign`'s Machining-tree contract. Applies
identically and symmetrically to all three operations (turning, drilling, milling) —
unlike the rest of this feature, this delta is **not** turning-specific.

## Current behavior (before this feature)

Opening any operation's floating window (`ui.open_operation`) does **not** hide the
Machining tree dropdown (the "Machining menu"). The tree's own visibility is gated
solely on `_ViewState.body_mode == "tree"`, a condition `_activate_tree_row()`
(`app.py`, the single call site for `_open_milling()`/`_open_drilling()`/
`_open_turning()`) never touches — a deliberate decoupling from an earlier revision
(`app.py`'s `on_pane()` docstring: *"`_ViewState.body_mode` can independently be
`"tree"` *while* an operation is open (the float doesn't touch it, revision)"*). The
result: the Machining tree remains rendered (positioned under the bar's "Machining"
entry) at the same time as the operation's own centered floating window.

## New behavior (this feature)

- **On open** (any of the three operations): the Machining tree dropdown is hidden
  immediately — `_activate_tree_row()` sets `view.body_mode = None` right after
  opening the operation. Only the operation's own floating window remains visible.
- **On exit** (Escape from the operation, returning to the top level): the Machining
  tree dropdown reappears, in the same state (selection position) it had before being
  hidden — via the **existing**, unmodified restore logic already present in both of
  `app.py`'s Escape handlers (`_escape_bar`'s defensive fallback and `_escape_body`'s
  primary path): `view.body_mode = "tree" if ui.tree.expanded else None`. Since
  `ui.tree.expanded` is never toggled while an operation is open, it is always `True`
  at this point, so both handlers correctly restore `body_mode = "tree"` with no
  further change. `view.tree_selected` (the highlighted row) is likewise untouched by
  opening/closing an operation, so the restored dropdown shows the same selection it
  had before.
- **Symmetry**: since the fix lives in `_activate_tree_row()` — the single shared call
  site for all three operations — the hide-on-open behavior is identical for turning,
  drilling, and milling without any per-operation code.

## Acceptance mapping

| spec.md requirement | Mechanism |
|---|---|
| FR-011 (hide on select) | `_activate_tree_row()`: `view.body_mode = None` after opening. |
| FR-012 (restore on exit, same state) | Existing `_escape_bar`/`_escape_body` restore logic (unchanged); `view.tree_selected` untouched throughout (unchanged). |
| FR-013 (symmetric across operations) | Single call site (`_activate_tree_row()`) shared by all three `_open_*` functions. |

## Example (headless test shape, mirrors `tests/integration/test_tui_navigation.py`)

```python
# "m": expand Machining, focus tree (row 0 = Milling); "\r": open Milling
snapshots = _drive(["m", "\r"])
# While Milling is open, the Machining tree must be hidden:
assert snapshots[-1][0] is None          # body_mode
assert snapshots[-1][3] is True          # open_operation is not None

# "\x1b": escape Milling, back to the tree
snapshots = _drive(["m", "\r", "\x1b"])
assert snapshots[-1][0] == "tree"        # body_mode restored
assert snapshots[-1][1] is True          # tree.expanded still True
assert snapshots[-1][3] is False         # operation closed
```

## Non-goals

This is a purely presentational fix (spec.md Assumptions): it does not change which
operations are available, how they are opened, or any calculation behavior. It does
not add, remove, or rename any `_ViewState`/`SessionUI` field.
