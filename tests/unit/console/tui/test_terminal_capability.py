"""Unit tests for terminal_capability.check() (tasks.md T009).

research.md #2: this module must correctly detect an unsupported terminal
*before* anything prompt-toolkit-related runs, so these tests mock only
`sys.stdin.isatty`/`sys.stdout.isatty`/`shutil.get_terminal_size` -- no
prompt-toolkit import is exercised (or needed) here at all.
"""

from __future__ import annotations

import os
from unittest import mock

from mfgparams.console.tui import terminal_capability as tc


def _terminal_size(columns: int, lines: int) -> os.terminal_size:
    return os.terminal_size((columns, lines))


def test_supported_when_tty_and_big_enough():
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 30)),
    ):
        result = tc.check()

    assert result.supported is True
    assert result.has_tty is True
    assert result.columns == 80
    assert result.lines == 30


def test_larger_than_minimum_is_still_supported():
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(120, 40)),
    ):
        result = tc.check()

    assert result.supported is True


def test_not_supported_when_no_tty():
    with (
        mock.patch("sys.stdin.isatty", return_value=False),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 30)),
    ):
        result = tc.check()

    assert result.supported is False
    assert result.has_tty is False


def test_not_supported_when_stdout_is_not_a_tty_either():
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=False),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 30)),
    ):
        result = tc.check()

    assert result.supported is False
    assert result.has_tty is False


def test_not_supported_when_too_few_columns():
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        # lines held at exactly the floor so this isolates a columns-only
        # failure, not a combined columns+lines one.
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(79, 25)),
    ):
        result = tc.check()

    assert result.supported is False
    assert result.has_tty is True
    assert result.columns == 79


def test_not_supported_when_too_few_lines():
    """022-tui-min-size-25x80 research.md #2: the floor is lowered back to
    25 (from 018-tui-splitpane-redesign's 30) -- 24 is one below the new
    floor, isolating a lines-only failure at the boundary now in effect."""

    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 24)),
    ):
        result = tc.check()

    assert result.supported is False
    assert result.lines == 24


def test_never_raises_even_with_a_zero_fallback_size():
    with (
        mock.patch("sys.stdin.isatty", return_value=False),
        mock.patch("sys.stdout.isatty", return_value=False),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(0, 0)),
    ):
        result = tc.check()

    assert result.supported is False


def test_module_does_not_import_prompt_toolkit():
    """research.md #2: this module must be checkable before any
    prompt-toolkit object exists, so it must not import prompt-toolkit at
    all -- otherwise importing it would itself risk the same silent
    degradation this module exists to detect ahead of."""

    assert "prompt_toolkit" not in vars(tc)
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(tc))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(alias.name.startswith("prompt_toolkit") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("prompt_toolkit")
