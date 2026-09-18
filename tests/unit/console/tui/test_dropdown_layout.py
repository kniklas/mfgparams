"""022-tui-min-size-25x80: regression guard for the Help-dropdown
underflow found during this feature's manual verification on a real
80x25 terminal.

Help's float anchors via a fixed `left` (its bar offset) at every
terminal width; since a *wider* terminal only ever increases the space to
its right, `MIN_COLUMNS` (the narrowest this app ever runs) is the only
width that can possibly underflow. This asserts the arithmetic invariant
that failed for Help before the fix -- `left offset + width floor +
Frame's border overhead <= MIN_COLUMNS` -- for every bar-entry-anchored
dropdown, not just Help, so the same class of bug can't silently
reappear (e.g. a width floor tuned back up, a bar label growing longer,
or `MIN_COLUMNS` itself shrinking).

This is a pure-arithmetic check, not a rendered-layout one: this
project's TUI test strategy (`DummyOutput`-based) cannot observe what a
dropdown actually looks like on screen (Constitution Principle XIII), so
it cannot replace the manual verification that originally found this --
only guard the specific number that broke.
"""

from __future__ import annotations

from mfgparams.console.tui import app as app_mod
from mfgparams.console.tui import terminal_capability
from mfgparams.console.tui.menu import default_entries


def test_bar_dropdown_widths_fit_at_min_columns():
    entries = default_entries("en")
    offsets = app_mod._bar_entry_offsets(entries)
    index_by_value = {entry.value: index for index, entry in enumerate(entries)}

    dropdowns = {
        "machining": app_mod._MACHINING_TREE_DROPDOWN_WIDTH,
        "configuration": app_mod._CONFIGURATION_DROPDOWN_WIDTH,
        "about": app_mod._ABOUT_DROPDOWN_WIDTH,
        "help": app_mod._HELP_DROPDOWN_WIDTH,
    }
    for bar_value, width in dropdowns.items():
        left = offsets[index_by_value[bar_value]]
        needed = (width.min or 0) + app_mod._DROPDOWN_FRAME_BORDER_COLUMNS
        available = terminal_capability.MIN_COLUMNS - left
        assert needed <= available, (
            f"{bar_value!r} dropdown needs {needed} columns (width min "
            f"{width.min} + {app_mod._DROPDOWN_FRAME_BORDER_COLUMNS} frame "
            f"border) but only {available} are available at MIN_COLUMNS "
            f"({terminal_capability.MIN_COLUMNS}) from its bar offset {left}"
        )


def test_help_is_the_rightmost_bar_entry():
    """The whole reason Help needed a narrower width floor than the other
    three dropdowns (see `app._HELP_DROPDOWN_WIDTH`'s comment): it sits
    closest to the screen edge. If a future menu reorder ever changes
    that, `_HELP_DROPDOWN_WIDTH`'s narrower floor would be solving a
    problem that moved to a different entry -- this pins the assumption
    down so that reorder fails loudly here instead of silently
    reintroducing the underflow on whichever entry becomes rightmost."""

    entries = default_entries("en")
    offsets = app_mod._bar_entry_offsets(entries)
    assert offsets[-1] == max(offsets)
    assert entries[-1].value == "help"
