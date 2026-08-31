"""FR-011: invoking the console without its dependencies explains the fix.

The ``console`` extra is empty on delivery, so this path cannot be reached by
uninstalling anything -- there is nothing to uninstall yet. It is specified and
tested now anyway, because the design question it answers is easy to get wrong
and expensive to rediscover: an extra gates *dependencies*, not modules, so
``mfgparams.console`` is importable whether or not the user asked for
``[console]``. A guard written as "is the console module importable?" would
answer "yes, always" and never fire (research.md #2).

The guard therefore wraps the lazy console import and keys on *which* module
failed, which is what the tests below simulate: a missing third-party
dependency gets the friendly message, while a failure inside our own
distribution is a broken install and must surface as itself rather than
sending the user to fix something that is not wrong.
"""

from __future__ import annotations

import importlib
import importlib.abc
import sys

import pytest

import mfgparams.__main__ as entry_point

_CONSOLE_MODULES = ("mfgparams.console", "mfgparams.console.cli")


class _FailOnConsoleImport(importlib.abc.MetaPathFinder):
    """Raise ``ModuleNotFoundError(name=...)`` when the console is imported."""

    def __init__(self, missing: str) -> None:
        self._missing = missing

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "mfgparams.console.cli":
            raise ModuleNotFoundError(f"No module named {self._missing!r}", name=self._missing)
        return None


@pytest.fixture
def simulate_missing(monkeypatch):
    """Make the console's import fail as though ``missing`` were absent."""

    def _install(missing: str) -> None:
        for name in _CONSOLE_MODULES:
            monkeypatch.delitem(sys.modules, name, raising=False)
        monkeypatch.setattr(sys, "meta_path", [_FailOnConsoleImport(missing), *sys.meta_path])

    return _install


def test_console_missing_dependency_reports_the_install_command(simulate_missing, capsys):
    simulate_missing("some_console_dependency")

    status = entry_point.main()
    captured = capsys.readouterr()

    assert status != 0, "a console that could not start must not report success"
    assert "pip install mfgparams[console]" in captured.err
    assert captured.out == "", "the guidance belongs on stderr, not stdout"


def test_console_missing_dependency_emits_one_message_and_no_traceback(simulate_missing, capsys):
    simulate_missing("some_console_dependency")

    entry_point.main()
    stderr = capsys.readouterr().err

    assert "Traceback" not in stderr
    assert stderr.count("pip install mfgparams[console]") == 1, "say it once"


def test_console_missing_dependency_message_comes_from_the_catalog(simulate_missing, capsys):
    """Principle VIII: user-facing text is catalogued, never inlined -- and the
    entry must live in the *core* catalog, since a message explaining that the
    console is unavailable cannot be looked up from inside the console
    (contracts/console-entry-contract.md)."""

    from mfgparams.locales import en

    assert entry_point._MISSING_CONSOLE_MESSAGE_ID in en.MESSAGES

    simulate_missing("some_console_dependency")
    entry_point.main()

    expected = en.MESSAGES[entry_point._MISSING_CONSOLE_MESSAGE_ID]
    assert capsys.readouterr().err.strip() == expected.strip()


def test_console_missing_dependency_does_not_mask_a_broken_core(simulate_missing):
    """A ``ModuleNotFoundError`` rooted at ``mfgparams`` is a broken install,
    not a missing extra, and must propagate."""

    simulate_missing("mfgparams.console.cli")

    with pytest.raises(ModuleNotFoundError) as excinfo:
        entry_point.main()

    assert excinfo.value.name == "mfgparams.console.cli"


def test_console_starts_normally_when_its_dependencies_are_present(monkeypatch):
    """The guard is invisible on the happy path (FR-012)."""

    import mfgparams.console.cli as console_cli

    called = []
    monkeypatch.setattr(console_cli, "main", lambda: called.append(True))

    assert entry_point.main() == 0
    assert called == [True]
