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

    def __init__(self, missing: str | None) -> None:
        self._missing = missing

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "mfgparams.console.cli":
            # `name=None` is legitimate: an import hook may omit it.
            raise ModuleNotFoundError(f"No module named {self._missing!r}", name=self._missing)
        return None


@pytest.fixture
def simulate_missing(monkeypatch):
    """Make the console's import fail as though ``missing`` were absent."""

    def _install(missing: str | None) -> None:
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

    expected = en.MESSAGES[entry_point._MISSING_CONSOLE_MESSAGE_ID].format(
        module=repr("some_console_dependency")
    )
    assert capsys.readouterr().err.strip() == expected.strip()


@pytest.mark.parametrize(
    "missing",
    [
        # Inside our own distribution.
        "mfgparams.console.cli",
        "mfgparams.registry",
        # A *core runtime requirement*, which a default install was supposed to
        # bring in. Not an `mfgparams.*` name, so a guard checking only for that
        # prefix reports it as a missing console extra -- and the user installs
        # `mfgparams[console]`, which cannot fix it (contracts/
        # console-entry-contract.md: "a genuinely broken core install must still
        # surface its own error").
        "tomli",
    ],
)
def test_console_missing_dependency_does_not_mask_a_broken_core(simulate_missing, missing):
    """A damaged install must surface its own error, not the friendly message."""

    simulate_missing(missing)

    with pytest.raises(ModuleNotFoundError) as excinfo:
        entry_point.main()

    assert excinfo.value.name == missing


def test_an_unnamed_import_failure_takes_the_friendly_path(simulate_missing, capsys):
    """``ModuleNotFoundError`` does not always carry a ``name``.

    Raised by hand, or by an import hook that omits it, ``exc.name`` is
    ``None`` -- and with no name there is nothing to identify as core, so the
    friendly path is the only honest answer: say the console is unavailable
    without inventing a culprit. The guard has a fallback phrase for precisely
    this, which until now was never reached.
    """

    simulate_missing(None)

    status = entry_point.main()
    stderr = capsys.readouterr().err

    assert status == 1
    assert "pip install mfgparams[console]" in stderr
    assert "a dependency" in stderr
    assert "None" not in stderr, "a missing name must not leak into the message"


def test_core_requirement_roots_are_read_from_metadata_not_restated():
    """The core set must track `pyproject.toml`, not a hand-kept copy of it."""

    roots = entry_point._core_requirement_roots()

    assert "tomli" in roots, roots
    # Extras are excluded by construction -- they are what the friendly path is for.
    assert "pytest" not in roots and "ruff" not in roots, roots


def test_the_message_names_the_module_that_is_actually_missing(simulate_missing, capsys):
    """Without the name, a misdirected message is undiagnosable."""

    simulate_missing("some_console_dependency")
    entry_point.main()

    assert "some_console_dependency" in capsys.readouterr().err


def test_console_starts_normally_when_its_dependencies_are_present(monkeypatch):
    """The guard is invisible on the happy path (FR-012)."""

    import mfgparams.console.cli as console_cli

    called = []
    monkeypatch.setattr(console_cli, "main", lambda: called.append(True) or 0)

    assert entry_point.main() == 0
    assert called == [True]


@pytest.mark.parametrize(
    "returned,expected",
    [(0, 0), (3, 3), (None, 0)],
    ids=["success", "console-reports-failure", "console-returns-nothing"],
)
def test_the_console_exit_status_is_passed_through(monkeypatch, returned, expected):
    """Swallowing the console's status would turn a future failure into a
    silent success, and this entry point documents itself as returning the
    process exit status."""

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(console_cli, "main", lambda: returned)

    assert entry_point.main() == expected
