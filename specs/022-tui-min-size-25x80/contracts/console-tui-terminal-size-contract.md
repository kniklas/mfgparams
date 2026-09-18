# Contract: Console TUI Minimum Terminal Size

**Feature**: `022-tui-min-size-25x80` | **Date**: 2026-09-18

Mirrors this repo's existing contract style (e.g.
`specs/018-tui-splitpane-redesign/contracts/console-tui-splitpane-contract.md`, which this
contract supersedes for the size-floor row of its Entry points table only — every other row
of that contract, and the rest of its content, is unaffected and remains authoritative). A
durable, test-enforced statement of the interface this feature exposes, not narrative
documentation.

## 1. Entry points

| Invocation | Behavior after this feature |
|---|---|
| No TTY / terminal too small | Exits with a clear, localized, catalog-sourced message and a non-zero, documented exit status — **before** any prompt-toolkit `Application` is constructed (unchanged gating mechanism). The size floor itself changes: **<25×80**, lowered from 018's <30×80 (this feature's `research.md`) — restoring the classic 80-column/25-line terminal standard 018 raised away from. `MIN_COLUMNS` (80) is unchanged; only `MIN_LINES` moves (30 → 25). |

Enforced by `tests/unit/console/tui/test_terminal_capability.py` (unit-level: `check()`'s
boundary behavior) and `tests/integration/test_tui_terminal_too_small.py` (integration-level:
`cli.py::main()`'s exit status and message content), both updated by this feature to assert
the new 80×25 boundary in place of the old 80×30 one.

## 2. Screen usability at the new floor (FR-005/FR-006)

| Screen | Overflow behavior at 80×25 |
|---|---|
| Drilling, Milling, Turning (operation screens) | No scroll fallback — content MUST fit within the terminal without clipping/overlap (research.md #3). If manual verification finds a shortfall, that screen's rendering MUST be compacted until it fits (FR-006). |
| Configuration, About, Help, Machining tree | Already scrollable (`app.py`'s `scrollable_dropdown_windows` mechanism, pre-existing, unchanged by this feature) — content taller than 25 lines remains fully reachable via the existing Up/Down scroll bindings; this satisfies FR-005's "usable" bar without requiring compaction. |

This table is **not** mechanically enforced by an automated test (this project's TUI test
strategy asserts state/rendered text, not layout fit or scroll reachability at a specific
terminal size — Principle XIII). It is enforced by the manual-verification task in
`tasks.md`, walked against `quickstart.md`.

## 3. What this contract does NOT change

- `MIN_COLUMNS` (80) — unchanged from both 017 and 018.
- The gating mechanism itself (check before construct, no degraded/partial TUI) — unchanged
  from 017/018.
- The menu bar entry set, Machining tree structure, split-pane layout, and keyboard contract
  described by `specs/018-tui-splitpane-redesign/contracts/console-tui-splitpane-contract.md`
  — unchanged by this feature except where §2 above notes a screen's rendering had to be
  compacted to fit the new floor (an implementation-level density change, not a structural
  one).
