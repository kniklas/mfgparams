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
import os
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


def test_the_console_frame_is_found_past_the_import_machinery():
    """`importlib.import_module` puts the standard library between the console
    and the failure, and those frames must not hide the console's.

    Locating the console by the *innermost non-machinery* frame is what makes
    the two-step rule work; scanning without skipping machinery would stop at
    `importlib/__init__.py` and never see the console at all.
    """

    import mfgparams.console.cli as console_cli

    console_file = Path(console_cli.__file__)
    namespace: dict = {}
    source = f"import importlib\n\n\ndef main():\n    importlib.import_module({_ABSENT!r})\n"
    exec(compile(source, str(console_file), "exec"), namespace)  # noqa: S102

    try:
        namespace["main"]()
    except ModuleNotFoundError as exc:
        frames = []
        traceback = exc.__traceback__
        while traceback is not None:
            frames.append(traceback.tb_frame.f_code.co_filename)
            traceback = traceback.tb_next

        # The premise: machinery frames really are present, and really are
        # below the console's. Without this the assertion below is vacuous.
        console_at = frames.index(str(console_file))
        assert any(entry_point._is_import_machinery(f) for f in frames[console_at + 1 :]), frames
        assert entry_point._requested_by_the_console(exc)
    else:  # pragma: no cover - the import above cannot succeed
        pytest.fail(f"{_ABSENT} is installed; pick a name that is not")


@pytest.mark.parametrize(
    "filename,machinery",
    [
        ("<frozen importlib._bootstrap>", True),
        (os.path.join(os.path.dirname(importlib.__file__), "__init__.py"), True),
        (os.path.join(os.path.dirname(importlib.__file__), "util.py"), True),
        # A *vendored* package that happens to be called `importlib`. Matching
        # on the directory's name rather than its path would skip its frames
        # and attribute its failures to whoever imported it.
        (os.path.join("somelib", "importlib", "compat.py"), False),
        (os.path.join("site-packages", "rich", "__init__.py"), False),
    ],
)
def test_import_machinery_is_recognised_by_path_not_by_name(filename, machinery):
    assert entry_point._is_import_machinery(filename) is machinery


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


def test_the_console_extra_wins_over_a_core_declaration_of_the_same_name(monkeypatch):
    """A name can be declared both without an extra and under `console`.

    A core requirement carrying an environment marker that does not apply to
    the running interpreter (`tomli; python_version < "3.11"` on 3.12) is not
    installed there, so if the console re-declares it, the extra is exactly
    what supplies it. Ranking the core declaration first would re-raise for a
    module `pip install mfgparams[console]` would genuinely have fixed.

    Simulated by declaring different metadata, not by patching the predicate:
    `_declared_requirements` is the reader this guard consults, and swapping
    what it reads is the same kind of substitution as `simulate_missing`.
    """

    monkeypatch.setattr(
        entry_point,
        "_declared_requirements",
        lambda: [("tomli", None), ("tomli", "console")],
    )

    assert not entry_point._is_broken_core(
        "tomli"
    ), "the console extra declares tomli, so installing it is a fix that works"


@pytest.mark.parametrize(
    "declared,module,broken",
    [
        # `PyYAML` installs `yaml`. Neither lookup matches the import name, so
        # the fall-through decides -- and the friendly path is already correct,
        # since a name we do not recognise is most likely the missing extra.
        ([("pyyaml", None), ("pyyaml", "console")], "yaml", False),
        ([("pyyaml", None)], "yaml", False),
        ([("pillow", "console")], "PIL", False),
        # The residual gap, recorded rather than engineered around: two
        # *different* distributions supplying the same import name. That is an
        # install conflict, not a packaging arrangement worth supporting.
        ([("foo", None), ("foo_bar", "console")], "foo", True),
    ],
    ids=["both-declared", "core-only", "console-only", "residual-gap"],
)
def test_a_distribution_name_that_is_not_the_import_name(monkeypatch, declared, module, broken):
    """The import-vs-distribution mismatch is harmless *here*, unlike in the
    execution-time guard, because both lookups miss together and the
    fall-through is the friendly path.

    This is the case a reader is most likely to mistake for a bug, so it is
    pinned rather than argued in a comment alone.
    """

    monkeypatch.setattr(entry_point, "_declared_requirements", lambda: declared)

    assert entry_point._is_broken_core(module) is broken


def test_a_core_only_requirement_is_still_a_broken_install(monkeypatch):
    """The tie-break must not swallow the case it was carved out of."""

    monkeypatch.setattr(entry_point, "_declared_requirements", lambda: [("tomli", None)])

    assert entry_point._is_broken_core("tomli")


@pytest.mark.parametrize(
    "module,broken",
    [
        ("mfgparams", True),
        ("mfgparams.registry", True),
        # A separate distribution whose name merely starts the same way. It is
        # not part of our install, so its absence is not our damage.
        ("mfgparams_plugin", False),
        ("mfgparams_plugin.thing", False),
    ],
)
def test_only_our_own_package_counts_as_ours(monkeypatch, module, broken):
    monkeypatch.setattr(entry_point, "_declared_requirements", list)

    assert entry_point._is_broken_core(module) is broken


def test_the_console_module_form_is_guarded_too(simulate_missing, capsys):
    """FR-011 is unqualified: it covers *invoking the console*, not one entry
    point. `python -m mfgparams.console` is a form a user reaches by guessing,
    so it must not be the one that answers with a stack trace."""

    import runpy

    simulate_missing("some_console_dependency")
    monkeypatch_free_modules = ("mfgparams.console.__main__",)
    for name in monkeypatch_free_modules:
        sys.modules.pop(name, None)

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("mfgparams.console", run_name="__main__")

    stderr = capsys.readouterr().err
    assert excinfo.value.code == 1
    assert "Traceback" not in stderr
    assert "pip install mfgparams[console]" in stderr


def test_an_exception_with_no_traceback_is_not_attributed_to_the_console():
    """A hand-raised error carries no frames, so there is no requester to
    attribute -- and an unattributable failure must not be blamed on the extra."""

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


def test_a_lazy_import_of_our_own_module_is_still_a_broken_install(monkeypatch):
    """Provenance is necessary at execution time, but it is not sufficient.

    "Did the console ask for this?" and "could the extra supply it?" are
    different questions, and a module of *ours* that the console imported
    lazily answers *yes* to the first while remaining a damaged install. Asking
    only about provenance answers it with `pip install mfgparams[console]` --
    advice that cannot work, and exactly what the contract's "MUST NOT catch
    import failures originating from the core package" rule forbids. So the
    import-time question is asked here too.
    """

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(
        console_cli,
        "main",
        _console_main_that_imports(
            "mfgparams.processes.machining.no_such_process",
            from_file=Path(console_cli.__file__),
        ),
    )

    with pytest.raises(ModuleNotFoundError):
        entry_point.main()


def _installed_package(tmp_path, monkeypatch, name: str, body: str) -> None:
    """Put a real, importable package called ``name`` on ``sys.path``.

    A real package is the point: these tests are about which *frame* raises,
    and only genuinely executing an import produces the frames the guard reads.
    """

    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").write_text(body)
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    monkeypatch.delitem(sys.modules, name, raising=False)


def test_a_console_library_s_own_missing_dependency_is_attributed_to_the_console(
    tmp_path, monkeypatch, capsys
):
    """A half-installed extra must not produce the traceback FR-011 forbids.

    Once `[console]` is non-empty, the likely failure is not "the extra was
    never installed" but "it is installed and something under it is missing":
    `rich` present, its own `pygments` absent. The deepest frame belonging to
    anyone's code is then the *library's* module body, and blaming it re-raises
    -- on precisely the path `pip install mfgparams[console]` repairs.

    A module body did not choose to be there; something imported it. Skipping
    it lands on the console frame that asked, which is the honest answer.
    """

    import mfgparams.console.cli as console_cli

    _installed_package(tmp_path, monkeypatch, "console_library_pkg", f"import {_ABSENT}\n")
    monkeypatch.setattr(
        console_cli,
        "main",
        _console_main_that_imports("console_library_pkg", from_file=Path(console_cli.__file__)),
    )

    status = entry_point.main()
    stderr = capsys.readouterr().err

    assert status == 1
    assert "Traceback" not in stderr
    assert "pip install mfgparams[console]" in stderr


def test_a_library_that_imports_via_a_helper_is_still_the_console_s_dependency(
    tmp_path, monkeypatch, capsys
):
    """The import cascade is what matters, not the shape of the frame at its end.

    A library need not spell its dependencies as bare module-scope `import`
    statements: `matplotlib` resolves its own in `_check_versions()`, and a
    hoisted check loop or a module-scope comprehension does the same. That puts
    an ordinary *call* frame at the bottom of what is still the console's
    import, so a rule that merely skipped module bodies would re-raise here --
    the raw traceback FR-011 forbids, on a half-installed extra.
    """

    import mfgparams.console.cli as console_cli

    _installed_package(
        tmp_path,
        monkeypatch,
        "helper_importing_pkg",
        f"def _setup():\n    import {_ABSENT}\n\n\n_setup()\n",
    )
    monkeypatch.setattr(
        console_cli,
        "main",
        _console_main_that_imports("helper_importing_pkg", from_file=Path(console_cli.__file__)),
    )

    status = entry_point.main()
    stderr = capsys.readouterr().err

    assert status == 1
    assert "Traceback" not in stderr
    assert "pip install mfgparams[console]" in stderr


def test_a_library_s_lazy_import_inside_a_call_is_still_its_own_bug(tmp_path, monkeypatch, capsys):
    """The other side of the same rule, and the reason it is about *frames*
    rather than about "is it third-party".

    Skipping module bodies must not become "blame the console for anything a
    library does". A library that imports something missing from inside one of
    its own *functions* is not resolving a dependency of its import; it is
    running, and that is its bug. It re-raises, as before.
    """

    import mfgparams.console.cli as console_cli

    _installed_package(
        tmp_path,
        monkeypatch,
        "calling_library_pkg",
        f"def go():\n    import {_ABSENT}\n",
    )
    namespace: dict = {}
    source = "def main():\n    import calling_library_pkg\n    calling_library_pkg.go()\n"
    exec(compile(source, str(Path(console_cli.__file__)), "exec"), namespace)  # noqa: S102
    monkeypatch.setattr(console_cli, "main", namespace["main"])

    with pytest.raises(ModuleNotFoundError) as excinfo:
        entry_point.main()

    assert excinfo.value.name == _ABSENT


@pytest.mark.parametrize(
    "returned", ["could not open the report file", ""], ids=["message", "empty-string"]
)
def test_a_non_integer_status_is_reported_rather_than_coerced(monkeypatch, capsys, returned):
    """`return "message"` / `sys.exit("message")` is a common convention.

    `int()` on such a status raises `ValueError` *inside the entry point*,
    replacing whatever the console was trying to say with the traceback this
    whole module exists to prevent -- and on the failure path, where the user
    can least afford it. Print it and report failure, as `sys.exit` does.
    """

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(console_cli, "main", lambda: returned)

    status = entry_point.main()
    stderr = capsys.readouterr().err

    assert status == 1
    assert "Traceback" not in stderr
    # Compared exactly rather than with `in`: `"" in stderr` is true of every
    # string, so the empty-string case would assert nothing about the output.
    assert stderr == f"{returned}\n"


def test_the_unnamed_fallback_is_looked_up_rather_than_inlined(
    simulate_missing, monkeypatch, capsys
):
    """Principle VIII covers the fallback phrase too.

    Editing the catalog must change the output; if it does not, the phrase is
    spliced in as an English literal and a translated run would emit it
    verbatim inside an otherwise translated sentence.
    """

    from mfgparams.locales import en

    monkeypatch.setitem(en.MESSAGES, entry_point._UNNAMED_DEPENDENCY_MESSAGE_ID, "jakas zaleznosc")

    simulate_missing(None)
    entry_point.main()

    assert "jakas zaleznosc" in capsys.readouterr().err


def test_a_pep_562_lazy_submodule_is_still_the_console_s_dependency(tmp_path, monkeypatch, capsys):
    """The cascade's evidence need not sit directly below the console.

    PEP 562 lazy submodules are how a heavy library keeps its import cheap:
    `from lib import thing` runs `lib.__getattr__("thing")`, an ordinary *call*
    frame, and the import happens beneath *that*. A rule looking only at the
    frame directly below the console sees a call and re-raises -- the traceback
    FR-011 forbids, on the same half-installed extra as the other two shapes.
    """

    import mfgparams.console.cli as console_cli

    package = tmp_path / "lazy_attr_pkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "import importlib\n\n\ndef __getattr__(name):\n"
        "    return importlib.import_module(f'lazy_attr_pkg.{name}')\n"
    )
    (package / "screen.py").write_text(f"import {_ABSENT}\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    monkeypatch.delitem(sys.modules, "lazy_attr_pkg", raising=False)

    namespace: dict = {}
    source = "def main():\n    from lazy_attr_pkg import screen\n"
    exec(compile(source, str(Path(console_cli.__file__)), "exec"), namespace)  # noqa: S102
    monkeypatch.setattr(console_cli, "main", namespace["main"])

    status = entry_point.main()
    stderr = capsys.readouterr().err

    assert status == 1
    assert "Traceback" not in stderr
    assert "pip install mfgparams[console]" in stderr


def test_the_innermost_console_frame_is_what_counts_not_the_first(tmp_path, monkeypatch, capsys):
    """The console can appear twice in one traceback, and only the deeper one
    describes what was actually attempted.

    A library invoked by the console calls back into it -- a formatter hook, a
    completion callback -- and *that* frame runs the import. Anchoring on the
    first console frame puts the library's own call frame inside the scanned
    region, which then reads as "the console called a function" and re-raises.
    """

    import mfgparams.console.cli as console_cli

    (tmp_path / "callback_lib.py").write_text("def run(callback):\n    return callback()\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    monkeypatch.delitem(sys.modules, "callback_lib", raising=False)

    namespace: dict = {}
    source = (
        "import callback_lib\n\n\ndef main():\n"
        f"    return callback_lib.run(lambda: __import__({_ABSENT!r}))\n"
    )
    exec(compile(source, str(Path(console_cli.__file__)), "exec"), namespace)  # noqa: S102
    monkeypatch.setattr(console_cli, "main", namespace["main"])

    assert entry_point.main() == 1
    assert "pip install mfgparams[console]" in capsys.readouterr().err


def test_machinery_frames_are_skipped_before_the_console_directory_test(tmp_path, monkeypatch):
    """`Path("<frozen importlib._bootstrap>").resolve()` is *relative to cwd*.

    Run from inside the console directory it resolves to a path under it, so a
    machinery frame would pass the "is this the console?" test and be taken for
    the innermost console frame. Skipping machinery first is what stops that;
    without it, a library's own failed `import_module` is answered with
    "install the console extra".
    """

    import mfgparams.console.cli as console_cli

    (tmp_path / "importing_lib.py").write_text(
        f"import importlib\n\n\ndef go():\n    importlib.import_module({_ABSENT!r})\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    monkeypatch.delitem(sys.modules, "importing_lib", raising=False)
    monkeypatch.chdir(Path(console_cli.__file__).parent)

    namespace: dict = {}
    source = "import importing_lib\n\n\ndef main():\n    importing_lib.go()\n"
    exec(compile(source, str(Path(console_cli.__file__)), "exec"), namespace)  # noqa: S102
    monkeypatch.setattr(console_cli, "main", namespace["main"])

    with pytest.raises(ModuleNotFoundError) as excinfo:
        entry_point.main()

    assert excinfo.value.name == _ABSENT
