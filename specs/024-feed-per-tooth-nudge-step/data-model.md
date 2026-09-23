# Data Model: Milling Feed-Per-Tooth Nudge Step

No new entities. This feature changes one constructor argument
(`step=`) on the existing `feed_per_tooth` `split_pane.NumberRow` built
by `src/mfgparams/console/tui/screens/milling.py`'s row factory — the
`step` field itself already exists on `NumberRow`
(`020-turning-feed-per-rotation`). No field, attribute, relationship, or
state transition is added, removed, or changed on any existing entity
(`NumberRow`, `MillingSessionState`, `OperationScreen`, or any other
session/state dataclass) — see `spec.md`'s omitted Key Entities section
(not applicable, per the template's own instruction to remove sections
that don't apply).
