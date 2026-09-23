# Data Model: Multi-Notation Metal Material Selector Dialog

## Extended entity: `WorkpieceMaterial` (`src/mfgparams/registry.py`)

Two new fields, both optional and additive (no existing caller/config file needs to change):

| Field | Type | Default | Notes |
|---|---|---|---|
| `material_number` | `str \| None` | `None` | EN material number notation, e.g. `"1.7225+N"` (FR-002, FR-010). Opaque display/search string — no format enforced (research.md #6). |
| `short_notation` | `str \| None` | `None` | Shortened/DIN-style designation, e.g. `"42CrMo4+N"` (FR-002, FR-010). Same validation tier as `material_number`. |

`display_name(locale)` (existing method) remains the source of the picker's common-name column
per Clarification 1 — no new method needed; the picker calls it exactly as `forms.display_label`
already does elsewhere.

### TOML key → dataclass field mapping (new)

| TOML key | Dataclass field | Required | Validation |
|---|---|---|---|
| `material_number` | `material_number` | No | If present: must be a string with no `_FORBIDDEN_NAME_CATEGORIES` character (control/line-separator). Invalid → validation issue recorded (warn-and-continue), field becomes `None`. |
| `short_notation` | `short_notation` | No | Same rule as `material_number`. |

Both keys flow through `registry_config.py::_parse_entries`'s existing generic
`fields_dict` (any TOML key not `name`/`unit_system`/`translations`) with **no parser code
change** — only `registry.py::_to_material` needs to read
`entry.fields.get("material_number")` / `entry.fields.get("short_notation")`, validate, and
pass them into the `WorkpieceMaterial(...)` constructor call.

### Merge/override behavior

`material_number` and `short_notation` join `registry.py::_STICKY_FIELDS` (currently just
`("material_type",)`) — see research.md Decision 5. A user override entry that omits either
key carries over the bundled entry's value for that key rather than dropping it.

## New entity: `MaterialPickerState` (`src/mfgparams/console/tui/material_picker.py`)

Transient dialog state; lives on `app.py`'s `_ViewState.material_picker` (research.md
Decision 1), `None` when the dialog is closed.

| Field | Type | Notes |
|---|---|---|
| `query_common` | `str` | Search text for the common-name column. Empty = no filter on this column. |
| `query_number` | `str` | Search text for the material-number column. |
| `query_short` | `str` | Search text for the shortened-designation column. |
| `active_column` | `Literal["common", "number", "short"]` | Which query field receives typed characters/backspace (FR-006). |
| `highlighted_name` | `str \| None` | The canonical `WorkpieceMaterial.name` of the currently highlighted row, or `None` when the candidate list is empty. Always a member of the *current* filtered candidate list, or `None`. |

Construction (`open_state(current_material_name, materials)`, FR-011, Clarification 2): all
three queries start empty, `active_column` starts `"common"`, and `highlighted_name` starts as
`current_material_name` if it is present in `materials` (the unfiltered full metal list),
otherwise `None`.

### Derived, not stored: the candidate list

`candidates(state, materials, display_locale) -> list[WorkpieceMaterial]` is a pure function,
recomputed on every render (research.md #8) — not cached on `MaterialPickerState` itself, to
avoid a second source of truth that could drift from the query fields. Filter rule (FR-004):
a material is included only if, for every one of the three queries that is non-empty, the
corresponding column value both (a) is present (not `None`/blank) and (b) contains that query
as a case-insensitive substring. The common-name column value used for both display and
matching is `material.display_name(display_locale)` (Clarification 1).

### State transitions

| Operation | Trigger | Effect |
|---|---|---|
| Open | Enter on the metal Material row (research.md #3) | `view.material_picker = open_state(...)`; focus moves to `material_picker_control`. |
| Move highlight | Up/Down | `highlighted_name` moves to the previous/next entry in the *current* filtered candidate list (wrapping is out of scope — spec.md Edge Cases: an empty list leaves nothing to move to). |
| Switch column | Left/Right or Tab/Shift+Tab | `active_column` cycles among the three, wrapping (research.md #7). |
| Edit query | Printable character / Backspace | Appends to / removes from whichever `query_*` field matches `active_column`; `highlighted_name` is re-derived against the newly-filtered candidate list (falls to the first candidate, or `None` if empty) each time a query changes, since the previously-highlighted material may no longer be a candidate. |
| Confirm | Enter, `highlighted_name is not None` | The corresponding operation's `session_state.material` is set to `highlighted_name`; `view.material_picker = None`; focus returns to `left_control` (FR-007). |
| Confirm, no highlight | Enter, `highlighted_name is None` | No-op — dialog stays open (FR-008). |
| Cancel | Escape (any time) | `view.material_picker = None`; focus returns to `left_control`; `session_state.material` is untouched (FR-009). |

No state persists between one dialog session and the next beyond what `open_state` derives
fresh from the just-closed operation's own `session_state.material` (FR-011).

## Unaffected

- `DrillingTool` / `MillingTool` / `TurningTool` — no notation fields; out of scope (this
  feature is materials-only, per the description's "select metal" framing).
- `OperationScreen`, `split_pane.RadioRow`/`NumberRow`, and every `rows_for` in
  `drilling.py`/`turning.py`/`milling.py` — unchanged (research.md #3).
