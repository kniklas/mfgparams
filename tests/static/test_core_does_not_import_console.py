"""Static + runtime check: the calculation core never imports the console.

FR-008 requires this to be *enforced automatically, not by convention*, and
the two checks below fail on different mistakes -- neither subsumes the other
(specs/014-process-namespaces-extras research.md #1):

1. :func:`test_no_core_module_imports_the_console` parses every module under
   ``src/mfgparams/`` with :mod:`ast` and fails on any statement naming
   ``mfgparams.console``. This catches an import that never executes at import
   time -- inside a function body, or behind ``TYPE_CHECKING`` -- which no
   runtime check can see, and states the rule where a reader will find it.

2. :func:`test_importing_the_core_leaves_the_console_unimported` imports the
   package in a *clean interpreter* and asserts ``mfgparams.console`` never
   lands in ``sys.modules``. This catches an import laundered through an
   intermediary -- core importing a module that imports the console -- which
   the per-file scan cannot see.

``mfgparams/__main__.py`` is exempt from the first check only: ``python -m
mfgparams`` requires a ``__main__.py`` at the package root and the interpreter
accepts no other location (FR-012). The exemption is narrowed by the second
check, which is what actually keeps it honest -- ``__main__.py`` may name the
console, but only from inside a function body, so importing ``mfgparams``
still never pulls it in.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import mfgparams

_SRC = Path(mfgparams.__file__).parent

#: The one file allowed to name ``mfgparams.console``, and only lazily.
#: See the module docstring and plan.md's Complexity Tracking table.
#:
#: Held as a path **relative to the package root**, not a bare filename. Matching
#: on ``Path.name`` would exempt any file called ``__main__.py`` anywhere under
#: ``src/mfgparams/`` -- a future ``processes/__main__.py`` would inherit the
#: licence to import the console without anyone deciding to grant it. plan.md's
#: Complexity Tracking promises the exemption is "narrowed to one named file",
#: and only a path comparison actually delivers that.
_EXEMPT = {"__main__.py"}

_FORBIDDEN = "mfgparams.console"


def _names_console(module: str | None) -> bool:
    """Is ``module`` the console package, or something inside it?

    A plain ``startswith`` is wrong here: it also matches a *sibling* whose name
    merely begins the same way, so a future ``mfgparams.console_helpers`` would
    be reported as a layering violation it is not. Anchoring on the dot makes
    the comparison one about package structure rather than about spelling.
    """
    return bool(module) and (module == _FORBIDDEN or module.startswith(_FORBIDDEN + "."))


def _is_exempt(relative_path: str) -> bool:
    return relative_path in _EXEMPT


def _core_modules() -> list[Path]:
    files = sorted(
        path
        for path in _SRC.rglob("*.py")
        if "console" not in path.relative_to(_SRC).parts
        and not _is_exempt(path.relative_to(_SRC).as_posix())
    )
    assert files, "no core modules found -- the layout moved and this test did not"
    return files


def _resolve_relative(relative_path: str, level: int, module: str | None) -> str:
    """Resolve a relative ``from . import`` target to its absolute dotted name.

    Relative imports are why this function exists. ``from .console import cli``
    parses to ``module='console', level=1`` -- it never contains the string
    ``mfgparams.console``, so a scan comparing ``node.module`` against the
    absolute name cannot see it. Combined with a function-local or
    ``TYPE_CHECKING`` placement, such an import is invisible to the runtime
    ``sys.modules`` check too, which would leave the layering rule unenforced
    in exactly the case this ast scan exists to cover.
    """
    package = ("mfgparams",) + Path(relative_path).parts[:-1]
    # level 1 is the containing package, level 2 its parent, and so on.
    keep = max(1, len(package) - (level - 1))
    return ".".join(package[:keep] + ((module,) if module else ()))


def _console_references(relative_path: str, source: str) -> list[str]:
    tree = ast.parse(source)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if _names_console(a.name)]
        elif isinstance(node, ast.ImportFrom):
            target = (
                node.module
                if node.level == 0
                else _resolve_relative(relative_path, node.level, node.module)
            )
            if _names_console(target):
                found.append(target)
    return found


@pytest.mark.parametrize("path", _core_modules(), ids=lambda p: p.relative_to(_SRC).as_posix())
def test_no_core_module_imports_the_console(path):
    relative = path.relative_to(_SRC).as_posix()
    offenders = _console_references(relative, path.read_text())

    assert not offenders, (
        f"{path.relative_to(_SRC).as_posix()} imports {offenders} -- the calculation "
        "core must not depend on the console (FR-008). The dependency runs one way."
    )


@pytest.mark.parametrize(
    "relative_path,exempt",
    [
        ("__main__.py", True),
        # A `__main__.py` anywhere else is a different file with no exemption.
        ("processes/__main__.py", False),
        ("processes/machining/__main__.py", False),
        ("registry.py", False),
    ],
)
def test_the_exemption_is_scoped_to_the_package_root(relative_path, exempt):
    """plan.md narrows the FR-008 exemption to *one named file*. Matching on the
    bare filename would hand the same licence to every future ``__main__.py``."""

    assert _is_exempt(relative_path) is exempt


@pytest.mark.parametrize(
    "relative_path,source",
    [
        ("registry.py", "from mfgparams.console import cli"),
        ("registry.py", "import mfgparams.console.cli"),
        ("registry.py", "from mfgparams.console.cli import main"),
        # Relative forms. Absent the resolution step these score clean.
        ("registry.py", "from .console import cli"),
        ("registry.py", "from .console.cli import main"),
        ("processes/machining/drilling/tools.py", "from ....console import cli"),
        # Placement the runtime sys.modules check cannot see, which is the whole
        # reason the ast scan exists alongside it.
        ("registry.py", "def f():\n    from .console import cli\n"),
        ("registry.py", "import typing\nif typing.TYPE_CHECKING:\n    from .console import cli\n"),
    ],
)
def test_the_scan_detects_every_import_form(relative_path, source):
    assert _console_references(relative_path, source), f"missed: {source!r}"


@pytest.mark.parametrize(
    "relative_path,source",
    [
        ("registry.py", "from mfgparams.processes.machining.drilling import calculate"),
        ("registry.py", "from .models import CalculationResult"),
        ("registry.py", "from . import units"),
        # Not the console: a sibling whose name merely starts the same way.
        ("registry.py", "from mfgparams.console_helpers import x"),
    ],
)
def test_the_scan_does_not_fire_on_legitimate_imports(relative_path, source):
    assert not _console_references(relative_path, source), f"false positive: {source!r}"


def test_the_exempt_module_exists_and_is_still_exempt():
    """A guard on the guard: silently losing the exemption's subject would
    turn the check above into a tautology."""

    for name in _EXEMPT:
        assert (_SRC / name).is_file(), f"{name} is exempt but does not exist"


@pytest.mark.parametrize(
    "module",
    [
        "mfgparams",
        "mfgparams.processes.machining.drilling",
        "mfgparams.processes.machining.milling",
        "mfgparams.processes.machining.milling.end_milling",
        "mfgparams.processes.machining.milling.face_milling",
        # The exempt module itself: importing it must not run its lazy import.
        "mfgparams.__main__",
    ],
)
def test_importing_the_core_leaves_the_console_unimported(module):
    """Run in a clean interpreter -- this session has already imported the
    console for other tests, so an in-process check would prove nothing."""

    code = (
        "import importlib, sys; "
        f"importlib.import_module({module!r}); "
        "print('\\n'.join(n for n in sys.modules if n.startswith('mfgparams.console')))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    leaked = completed.stdout.split()
    assert not leaked, (
        f"importing {module} pulled in {leaked}; the console must stay out of "
        "sys.modules until something actually asks for it (FR-008)"
    )
