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
