"""Detect whether the running terminal can support the text GUI (FR-006, FR-008, FR-011).

research.md #2: prompt-toolkit does **not** raise when stdin/stdout are not a
real TTY -- it prints an unlocalized warning to stderr and silently degrades
to a plain-text output mode. That is exactly the behavior FR-006 forbids, so
this module contains **no prompt-toolkit import** and must run *before* any
prompt-toolkit object is constructed: it is the only thing standing between
an unsupported terminal and that silent degradation.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass

#: 022-tui-min-size-25x80 FR-001/FR-002/research.md #1: lowered back to 25,
#: restoring the classic 80x25 terminal standard -- 018-tui-splitpane-
#: redesign had raised this to 30 (from 017's 25) because the complete
#: layout (menu bar + tree + an operation's left/right panes) didn't
#: reliably fit the old floor. This feature's manual verification
#: (quickstart.md, Constitution Principle XIII) is the required check that
#: every screen still fits at 25, compacting any that don't (FR-006).
#: MIN_COLUMNS is unaffected either way (the prototype's combined pane
#: width already fit comfortably within 80).
MIN_COLUMNS = 80
MIN_LINES = 25


@dataclass(frozen=True)
class TerminalCapability:
    """The result of checking whether this process can run the text GUI.

    Attributes:
        supported: ``True`` only if both stdin and stdout are a real TTY and
            the terminal is at least :data:`MIN_COLUMNS`x:data:`MIN_LINES`.
        has_tty: Whether both stdin and stdout are attached to a terminal.
        columns: The detected terminal width (best-effort; a non-TTY still
            reports *some* size via ``shutil.get_terminal_size``'s fallback).
        lines: The detected terminal height, same caveat as ``columns``.
    """

    supported: bool
    has_tty: bool
    columns: int
    lines: int


def check() -> TerminalCapability:
    """Check the current process's terminal for text-GUI support.

    Never raises. Reads real state (``sys.stdin.isatty()``,
    ``sys.stdout.isatty()``, ``shutil.get_terminal_size()``) rather than
    assuming a capability -- this is the FR-006/FR-008/FR-011 precondition
    every entry point must check before constructing a prompt-toolkit
    ``Application``.
    """

    has_tty = sys.stdin.isatty() and sys.stdout.isatty()
    size = shutil.get_terminal_size(fallback=(0, 0))
    columns, lines = size.columns, size.lines
    big_enough = columns >= MIN_COLUMNS and lines >= MIN_LINES
    return TerminalCapability(
        supported=has_tty and big_enough, has_tty=has_tty, columns=columns, lines=lines
    )
