"""Integration test: a terminal below 25x80 exits with a clear message
(022-tui-min-size-25x80 spec.md FR-002/FR-004, quickstart.md Part 2 --
lowered back from 018-tui-splitpane-redesign's 30-row floor,
research.md #2)."""

from __future__ import annotations

import os
from unittest import mock

import pytest

import mfgparams.console.cli as cli


def _terminal_size(columns: int, lines: int) -> os.terminal_size:
    return os.terminal_size((columns, lines))


@pytest.fixture(autouse=True)
def _isolate_argv(monkeypatch):
    """See test_tui_no_tty_fallback.py's identical fixture docstring."""

    monkeypatch.setattr("sys.argv", ["mfgparams"])


def test_main_exits_1_when_terminal_is_too_narrow(capsys):
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        # lines held at exactly the floor so this isolates a columns-only
        # failure, not a combined columns+lines one.
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(79, 25)),
    ):
        status = cli.main()

    assert status == 1
    captured = capsys.readouterr()
    assert "79" in captured.err
    assert "25" in captured.err  # the required minimum, per the message template


def test_main_exits_1_when_terminal_is_too_short(capsys):
    """24: one below the 25-row floor (022-tui-min-size-25x80), isolating a
    lines-only failure at the boundary now in effect."""

    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 24)),
    ):
        status = cli.main()

    assert status == 1
    captured = capsys.readouterr()
    assert "24" in captured.err


def test_main_succeeds_at_exactly_the_minimum_size():
    """25x80 is the minimum *supported* size, not the threshold for
    rejection (022-tui-min-size-25x80 FR-002) -- exactly-minimum must not
    be treated as "too small"."""

    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 25)),
    ):
        from mfgparams.console.tui import terminal_capability

        result = terminal_capability.check()

    assert result.supported is True
