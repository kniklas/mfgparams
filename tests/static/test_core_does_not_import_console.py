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
_EXEMPT = {"__main__.py"}

_FORBIDDEN = "mfgparams.console"


def _core_modules() -> list[Path]:
    files = sorted(
        path
        for path in _SRC.rglob("*.py")
        if "console" not in path.relative_to(_SRC).parts and path.name not in _EXEMPT
    )
    assert files, "no core modules found -- the layout moved and this test did not"
    return files


def _console_references(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if a.name.startswith(_FORBIDDEN)]
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith(_FORBIDDEN):
                found.append(node.module)
    return found


@pytest.mark.parametrize("path", _core_modules(), ids=lambda p: p.relative_to(_SRC).as_posix())
def test_no_core_module_imports_the_console(path):
    offenders = _console_references(path)

    assert not offenders, (
        f"{path.relative_to(_SRC).as_posix()} imports {offenders} -- the calculation "
        "core must not depend on the console (FR-008). The dependency runs one way."
    )


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
