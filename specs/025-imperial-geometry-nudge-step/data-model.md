# Data Model: Imperial Arrow-Key Nudge Step for Geometry Fields

No new entities. This feature changes the `step=` constructor argument on
nine existing `split_pane.NumberRow`s built by
`src/mfgparams/console/tui/screens/milling.py` (4 rows),
`src/mfgparams/console/tui/screens/drilling.py` (2 rows), and
`src/mfgparams/console/tui/screens/turning.py` (3 rows) — the `step` field
itself already exists on `NumberRow` (`020-turning-feed-per-rotation`).
Two of the three screens' shared `_number_row()` helper functions
(drilling's, turning's) gain a new optional `step` parameter, mirroring
the one milling's already has (`024-feed-per-tooth-nudge-step`); this is a
function-signature change, not a data-model change. No field, attribute,
relationship, or state transition is added, removed, or changed on any
existing entity (`NumberRow`, `MillingSessionState`, `DrillingSessionState`,
`TurningSessionState`, `OperationScreen`, or any other session/state
dataclass) — see `spec.md`'s omitted Key Entities section (not applicable,
per the template's own instruction to remove sections that don't apply).
