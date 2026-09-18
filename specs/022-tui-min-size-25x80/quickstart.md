# Quickstart: Validating TUI Minimum Terminal Size 25x80

This is the Principle XIII manual-verification walkthrough `tasks.md`'s required
manual-verification task points to. It cannot be run by an agent — it requires a real
terminal and a human (developer or reviewer) observing the rendered output (Constitution
Principle XIII: this project's automated TUI tests assert state/rendered text, not layout
fit or clipping).

## Prerequisites

- A working checkout with this feature's code change applied (`MIN_LINES = 25` in
  `src/mfgparams/console/tui/terminal_capability.py`) and the `console` extra installed
  (`pip install -e ".[console]"`).
- A real terminal emulator you can resize to an exact character size (most emulators show
  the current size while resizing, e.g. in the title bar or a HUD overlay).

## Part 1 — Confirm the new floor is accepted (User Story 1 / SC-001)

1. Resize your terminal window to **exactly 80 columns x 25 lines**. If your emulator
   doesn't show size while dragging, confirm from inside it first:
   ```sh
   stty size   # prints "rows columns" — must read "25 80" before proceeding
   ```
   If it doesn't, either drag to fit or, for xterm-compatible emulators, request an exact
   resize: `printf '\e[8;25;80t'`.
2. Launch the text GUI: `mfgparams`
3. **Expected**: the application starts — no "terminal too small" message, menu bar visible,
   Machining tree reachable. (If step 1's size wasn't exact, this may fail even on a
   correct implementation — re-check `stty size` before concluding anything.)
4. Walk every screen reachable from the main menu, confirming each against the table below,
   per FR-005/FR-006 and `research.md #3`'s scroll-vs-clip distinction:

   | Screen | How to reach it | What to confirm |
   |---|---|---|
   | Drilling | Machining → Drilling | Every field label, value, and the bottom status/hint row is visible with no cut-off row; Tab/arrow keys reach every field. |
   | Milling | Machining → Milling | Same as Drilling — this is the field-densest operation screen (research.md #4), most likely to fall short first. |
   | Turning | Machining → Turning | Same as Drilling — never measured against a real terminal before this feature. |
   | Configuration | menu bar → Configuration | Screen opens; if content exceeds 25 lines (likely with a non-default `--materials-config`), confirm Up/Down scrolls to reveal the rest rather than the screen refusing to open or crashing. |
   | About | menu bar → About | Opens, short content fully visible. |
   | Help | menu bar → Help | Opens, short content fully visible. |

5. **If any operation screen (Drilling/Milling/Turning) shows a cut-off row or overlapping
   content**: this is the FR-006 case. File it as a task to compact that screen's rendering
   (research.md #5 — no technique is prescribed in advance; pick the smallest change that
   closes the gap), re-apply, and re-run this same check until it passes.
6. **If Configuration/About/Help/the Machining tree fail to open, crash, or don't scroll to
   reveal overflow content**: this is a regression outside this feature's expected change
   set (research.md #3 says these already handle overflow) — investigate before proceeding.

## Part 2 — Confirm terminals below the floor are still rejected (User Story 2 / SC-002)

1. Resize to **79 columns x 25 lines** (`stty size` reads "25 79"). Run `mfgparams`.
   **Expected**: rejected with a "terminal too small" message before any UI appears; the
   message states a minimum of 80x25 (not 80x30).
2. Resize to **80 columns x 24 lines** (`stty size` reads "24 80"). Run `mfgparams`.
   **Expected**: same rejection.
3. These two also have automated coverage (`tests/integration/test_tui_terminal_too_small.py`)
   — this manual pass is a sanity check that the automated boundary matches what a human
   actually sees, not a substitute for it.

## Outcome

This walkthrough is complete, and the feature's manual-verification task done, once every
row in Part 1's table passes (with any FR-006 compaction work applied and re-verified) and
both Part 2 checks reject as expected.
