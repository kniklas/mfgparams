# Data Model: TUI Minimum Terminal Size 25x80

No new entities. This feature changes two module-level constants
(`terminal_capability.MIN_COLUMNS`, unchanged at 80; `terminal_capability.MIN_LINES`, 30 → 25)
consumed by the existing `TerminalCapability` dataclass and `check()` function
(`src/mfgparams/console/tui/terminal_capability.py`), and, only where manual verification
(research.md #3/#4) finds a shortfall, adjusts existing screen-rendering density in
`src/mfgparams/console/tui/screens/{drilling,milling,turning}.py`. No field, attribute,
relationship, or state transition is added, removed, or changed on any existing entity
(`TerminalCapability`, `SessionUI`, `MachiningTree`, `OperationScreen`, or any
`*SessionState`) — see `spec.md`'s Key Entities section ("Not applicable").

**Post-implementation correction (Copilot review, PR #103)**: the paragraph above, written
during planning, scoped all possible layout adjustments to the three operation-screen
modules — it did not anticipate that a fix could land anywhere else, because its own
risk analysis (research.md #3/#4) only considered vertical row-fit, not horizontal
dropdown-width fit. Manual verification (tasks.md T008) found a one-column width underflow
in the Help dropdown's positioning, unrelated to any screen's content and pre-existing
(latent since at least 018-tui-splitpane-redesign, not introduced by this feature's
`MIN_LINES` change) — fixed by narrowing a named width constant
(`_HELP_DROPDOWN_WIDTH`) in `src/mfgparams/console/tui/app.py`, the shared menu-bar/
dropdown wiring module, not a `screens/*.py` module. No entity, field, or data shape
changed by this fix either — it is still purely a constant-value change, just a different
one than this document originally scoped for.
