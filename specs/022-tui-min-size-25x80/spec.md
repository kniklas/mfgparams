# Feature Specification: TUI Minimum Terminal Size 25x80

**Feature Branch**: `022-tui-min-size-25x80`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Change minimum TUI display to 25x80 to be aligned to old terminals"

## Clarifications

### Session 2026-09-18

- Q: The spec's User Story 1 calls Milling "the taller of the two operation screens," but the current code has three operations under the Machining tree (Drilling, Milling, and Turning — added since the 018 redesign the spec's row-math cites), plus separate Configuration/About/Help screens outside the Machining tree entirely. Which screens must the manual 80x25 fit-verification (FR-005/FR-006) actually cover? → A: Every screen reachable from the menu — all three Machining operations (Drilling, Milling, Turning) plus Configuration, About, and Help.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch the text GUI on a classic 25x80 terminal (Priority: P1)

A user running mfgparams on old or constrained hardware (per Principle V's legacy-hardware
target) opens the text GUI in a terminal sized to the classic 80-column, 25-line standard
(e.g. a VT100-class terminal, a legacy serial console, or a terminal emulator deliberately
kept at that size). Today the application refuses to start because its height floor (30
lines) is taller than their terminal; after this change, the application launches and is
usable.

**Why this priority**: This is the entire purpose of the change — without it, the feature
delivers nothing. The application's own resource-constrained-compatibility principle is
undermined if the text GUI locks out the terminal size most associated with legacy hardware.

**Independent Test**: Launch the text GUI (`mfgparams` console entry point, text-GUI mode)
in a terminal reporting exactly 80 columns x 25 lines and confirm the application starts,
renders its menu bar, Machining tree, and every screen reachable from the main menu
(Drilling, Milling, Turning, Configuration, About, Help) without being rejected as
"unsupported."

**Acceptance Scenarios**:

1. **Given** a terminal reporting 80 columns x 25 lines, **When** the user launches the text
   GUI, **Then** the application starts (no "terminal too small" rejection) and the initial
   screen (menu bar + Machining tree) is visible and usable.
2. **Given** a terminal reporting 80 columns x 25 lines, **When** the user opens each screen
   reachable from the main menu (the Drilling, Milling, and Turning operation screens, plus
   Configuration, About, and Help), **Then** every screen's content and controls remain
   visible and keyboard-operable, with no crash, clipping, or unrecoverable error, per the
   manual-verification requirement in Assumptions.

---

### User Story 2 - Still reject terminals smaller than 25x80 (Priority: P2)

A user's terminal is narrower or shorter than 80x25 (e.g. resized very small, or a
non-standard legacy device below the classic floor). The application MUST continue to
detect this and refuse to start the text GUI with a clear message, exactly as it does
today for undersized terminals — this feature only changes *where* the floor sits, not
the fact that a floor exists.

**Why this priority**: Without this, lowering the floor could be mistaken for removing it
entirely, silently degrading into the unlocalized, un-styled fallback output that FR-006 of
the original text-GUI feature (017-console-text-gui) forbids.

**Independent Test**: Launch the text GUI in a terminal reporting 79 columns x 25 lines, and
separately in one reporting 80 columns x 24 lines; confirm both are rejected with the
existing "terminal too small" message before any prompt-toolkit UI is constructed.

**Acceptance Scenarios**:

1. **Given** a terminal reporting 79 columns x 25 lines, **When** the user launches the text
   GUI, **Then** the application reports the terminal as unsupported and does not start.
2. **Given** a terminal reporting 80 columns x 24 lines, **When** the user launches the text
   GUI, **Then** the application reports the terminal as unsupported and does not start.

---

### Edge Cases

- What happens when the terminal is exactly at the new floor (80x25) but the currently
  selected operation screen's content, at that exact size, would need more rows than are
  available? See the manual-verification requirement in Assumptions — this is precisely
  what that verification exists to catch before release.
- What happens to a session that starts in a terminal at or above the new floor and is then
  resized smaller than 80x25 while the text GUI is already running? This is unchanged by
  this feature — whatever the application already does today on a shrink-below-floor resize
  (if anything) continues unchanged; only the launch-time floor value moves.
- What happens on a terminal that reports 0x0 or a failed/unavailable size query (e.g. not a
  real TTY)? Unchanged by this feature — already handled as "unsupported" via the existing
  TTY check, independent of the column/line thresholds.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST treat a terminal reporting at least 80 columns and at least 25
  lines as large enough to run the text GUI, where today it requires at least 30 lines.
- **FR-002**: The system MUST continue to treat a terminal reporting fewer than 80 columns,
  or fewer than 25 lines, as too small to run the text GUI, and MUST refuse to start it in
  that case (unchanged behavior, only the line threshold's value changes).
- **FR-003**: The system MUST perform this size check before constructing any text-GUI
  screen or widget, exactly as it does today, so an undersized terminal never reaches a
  half-built or silently degraded UI.
- **FR-004**: The unsupported-terminal message shown to the user MUST continue to state the
  actual minimum required size, reflecting the new 80x25 floor rather than the old 80x30
  value.
- **FR-005**: Every screen reachable from the main menu — the Machining tree's three
  operation screens (Drilling, Milling, Turning) as well as Configuration, About, and Help —
  MUST remain usable — visible and keyboard-operable without crashing — on a terminal at
  exactly the new floor (80 columns x 25 lines).
- **FR-006**: If manual verification (see Assumptions) finds that any of those screens'
  content does not fully fit within 80x25 without clipping or overlap, that screen's
  rendering MUST be compacted until it fits, rather than accepting the clipped/overlapping
  result or leaving that screen's effective floor higher than 25 lines.

### Key Entities

*(Not applicable — this feature changes a configuration threshold and a display-capability
check; it introduces no new data entities.)*

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user on a terminal sized to the classic 80x25 standard can launch the text
  GUI and reach every screen on the main menu — Drilling, Milling, Turning, Configuration,
  About, and Help — without being rejected as unsupported.
- **SC-002**: A terminal narrower than 80 columns or shorter than 25 lines is still rejected
  with a clear message, 100% of the time, before any part of the text GUI renders.
- **SC-003**: No existing text-GUI behavior changes for terminals that were already at or
  above 80x30 (the old floor) — this change only widens the set of accepted terminals
  downward, it does not alter anything for terminals already above the new floor.

## Assumptions

- **MIN_COLUMNS stays at 80.** The user's "25x80" phrasing matches the application's
  existing column floor exactly (80), so only the line floor changes, from 30 to 25 — the
  classic 80x25 text-terminal standard this feature is aligning to.
- **Per Principle XIII (Manual Verification for Interactive & Reference-Fidelity
  Features), this is an interactive TUI change and its correctness at the new floor cannot
  be confirmed by automated tests alone** (this project's TUI test strategy asserts against
  state/rendered text, not layout fit/clipping). Before this feature is considered done, a
  developer or reviewer MUST manually run the text GUI on a real terminal set to exactly
  80x25 and confirm every screen reachable from the main menu — Drilling, Milling, Turning,
  Configuration, About, and Help — has its content and controls remain visible and
  reachable, with no clipped or overlapping content. This is tracked as a required, separate
  manual-verification task at planning time, not assumed from a passing automated test
  suite.
- **If manual verification finds a screen's content does not actually fit at 80x25** (the
  row-budget math from the 018-tui-splitpane-redesign feature estimated the Milling screen —
  the more complex of the two operations that existed at that time — at 24-25 rows *before*
  adding this feature's own margin, and before Turning existed as a third operation with its
  own, not-yet-measured row count; a tight or failing fit at exactly 25 lines is a real
  possibility for any of the three operation screens, not a purely hypothetical edge case):
  fitting within 80x25 is a hard requirement of this feature, not an aspiration, for every
  screen in FR-005's scope. If a screen's content does not fit, its rendering MUST be
  compacted (e.g. tighter spacing, shorter labels/summaries) until it does, before this
  feature's manual-verification task is considered complete — the feature is not done merely
  because `MIN_LINES` was edited to 25.
