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
from pathlib import Path

import pytest

import mfgparams
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


def _console_main_that_imports(module: str, *, from_file):
    """A stand-in console ``main()`` whose lazy import of ``module`` fails.

    The failure is simulated **at the dependency** -- `module` genuinely is not
    installed, so the interpreter raises the real `ModuleNotFoundError` from a
    real `import` statement -- and never at the guard's own condition, which
    `contracts/console-entry-contract.md` forbids because patching the
    condition asserts nothing about the behaviour FR-011 specifies.

    What the stand-in controls is *provenance*: compiling it with
    ``from_file`` as its filename puts that path in the traceback, exactly
    where a lazy import written at that location would put it. The console has
    no lazy import today (#63 permits one to be added), so there is no real
    call site to point the finder at yet.
    """
    namespace: dict = {}
    source = f"def main():\n    import {module}\n    return 0\n"
    exec(compile(source, str(from_file), "exec"), namespace)  # noqa: S102
    return namespace["main"]


_ABSENT = "definitely_not_an_installed_distribution_xyz"


def test_a_lazy_console_dependency_still_gets_the_friendly_message(monkeypatch, capsys):
    """FR-011 covers the run, not only the import.

    #63 permits the console to import a heavy dependency lazily -- inside the
    call rather than at module scope. That import fails *after* the entry point
    has committed to running, so a guard wrapped around the import alone lets
    the raw traceback through on exactly the path the extra exists to describe.
    """

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(
        console_cli,
        "main",
        _console_main_that_imports(_ABSENT, from_file=Path(console_cli.__file__)),
    )

    status = entry_point.main()
    stderr = capsys.readouterr().err

    assert status == 1
    assert "Traceback" not in stderr
    assert "pip install mfgparams[console]" in stderr
    assert _ABSENT in stderr


def test_a_lazy_import_deeper_inside_the_console_is_also_attributed(monkeypatch, capsys):
    """Any file under the console package counts, not just `cli.py`."""

    import mfgparams.console.cli as console_cli

    deeper = Path(console_cli.__file__).parent / "some_future_screen.py"
    monkeypatch.setattr(console_cli, "main", _console_main_that_imports(_ABSENT, from_file=deeper))

    assert entry_point.main() == 1
    assert "pip install mfgparams[console]" in capsys.readouterr().err


@pytest.mark.parametrize(
    "requester",
    [
        # A third-party library the console merely *called*: its own bug.
        Path(sys.prefix) / "lib" / "site-packages" / "some_library" / "widget.py",
        # Core code. A missing import here is a broken install of ours.
        Path(mfgparams.__file__).parent / "registry.py",
    ],
    ids=["third-party-library", "core-module"],
)
def test_a_run_time_failure_the_console_did_not_ask_for_is_re_raised(monkeypatch, requester):
    """The execution-time guard asks *who requested the module*, not what it is
    called -- and answers "not the console" by re-raising.

    Attribution by name cannot work here: the `console` extra records a
    distribution name (`PyYAML`) while the exception carries an import name
    (`yaml`), and resolving one to the other needs metadata that is by
    definition absent when the import fails. Since this guard's default is to
    re-raise, every such miss would fail in the direction FR-011 forbids.
    """

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(
        console_cli, "main", _console_main_that_imports(_ABSENT, from_file=requester)
    )

    with pytest.raises(ModuleNotFoundError) as excinfo:
        entry_point.main()

    assert excinfo.value.name == _ABSENT


def test_the_import_name_never_has_to_match_a_distribution_name(monkeypatch, capsys):
    """The regression this design exists for.

    `PyYAML` installs the module `yaml`; `Pillow` installs `PIL`. A guard
    comparing `exc.name` against the extra's declared distribution names misses
    every such package and re-raises the traceback instead.
    """

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(
        console_cli,
        "main",
        _console_main_that_imports("yaml_but_not_installed", from_file=Path(console_cli.__file__)),
    )

    assert entry_point.main() == 1
    assert "pip install mfgparams[console]" in capsys.readouterr().err


def test_provenance_ignores_the_import_machinery_frames(monkeypatch):
    """`_requesting_file` must skip `<frozen importlib._bootstrap>` and friends,
    or it would attribute every failure to the interpreter and never fire."""

    import mfgparams.console.cli as console_cli

    console_file = Path(console_cli.__file__)
    raising = _console_main_that_imports(_ABSENT, from_file=console_file)

    try:
        raising()
    except ModuleNotFoundError as exc:
        assert entry_point._requesting_file(exc) == str(console_file)
        assert entry_point._requested_by_the_console(exc)
    else:  # pragma: no cover - the import above cannot succeed
        pytest.fail(f"{_ABSENT} is installed; pick a name that is not")


def test_provenance_looks_past_importlib_s_own_frames(monkeypatch, capsys):
    """`importlib.import_module` is a real call site, and a real frame.

    A lazy import written as `importlib.import_module("rich")` puts
    `importlib/__init__.py` between the console's frame and the frozen
    bootstrap ones. Stopping at the first frame that is merely *not* angle
    bracketed would attribute the failure to the standard library and re-raise.
    """

    import mfgparams.console.cli as console_cli

    console_file = Path(console_cli.__file__)
    namespace: dict = {}
    source = f"import importlib\n\n\ndef main():\n    importlib.import_module({_ABSENT!r})\n"
    exec(compile(source, str(console_file), "exec"), namespace)  # noqa: S102
    monkeypatch.setattr(console_cli, "main", namespace["main"])

    assert entry_point.main() == 1
    assert "pip install mfgparams[console]" in capsys.readouterr().err


def test_an_exception_with_no_traceback_is_not_attributed_to_the_console():
    """A hand-raised error carries no frames, so there is no requester to
    attribute -- and an unattributable failure must not be blamed on the extra."""

    assert entry_point._requesting_file(ModuleNotFoundError("no traceback")) is None
    assert not entry_point._requested_by_the_console(ModuleNotFoundError("no traceback"))


@pytest.mark.parametrize(
    "marker,expected",
    [
        ('  extra == "console"', "console"),
        ("  extra == 'console'", "console"),
        ("extra=='console'", "console"),
        ('python_version < "3.11" and extra == "console"', "console"),
        ('extra == "dev"', "dev"),
        ('python_version < "3.11"', None),
        ("", None),
    ],
)
def test_the_extra_marker_is_parsed_not_substring_matched(marker, expected):
    """Quoting and spacing in a `Requires-Dist` marker are not guaranteed, so
    the gating extra is parsed rather than matched as a fixed substring.

    A marker this failed to recognise would not merely lose a friendly message:
    the requirement would fall into the *core* set, where `_is_broken_core`
    calls it a damaged install and re-raises the traceback FR-011 prevents.
    """

    found = entry_point._EXTRA_MARKER.search(marker)

    assert (found.group(1) if found else None) == expected
