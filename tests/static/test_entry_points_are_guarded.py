"""Every way to start the console routes through the FR-011 guard.

`console-entry-contract.md` names three invocation forms and requires all three
to reach `mfgparams.__main__:main`, which is where the missing-dependency guard
lives. That is a claim about *which modules are runnable*, and nothing in the
contract enforces it -- so a fourth form can appear the moment someone adds an
`if __name__ == "__main__"` block to a module deep in the package, as
`console/cli.py` carried until this test was written. Running that module
directly started the REPL with no guard at all, and with a console dependency
missing it printed the raw traceback FR-011 forbids -- reachable by exactly the
guessing that justifies guarding `python -m mfgparams.console` in the first
place.

A runnable module is one Python will execute for `python -m <name>`: a
`__main__.py`, or any module with a top-level `if __name__ == "__main__"`
block. This test fails if a new one appears anywhere it is not expected.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import mfgparams

_SRC = Path(mfgparams.__file__).parent

#: The only modules allowed to be runnable, each with the form it serves.
#: Both delegate to the guarded `mfgparams.__main__:main`; see the contract.
_RUNNABLE = {
    "__main__.py": "python -m mfgparams",
    "console/__main__.py": "python -m mfgparams.console",
}


def _is_dunder_main_test(node: ast.stmt) -> bool:
    """Is ``node`` an ``if __name__ == "__main__":`` statement?"""
    if not isinstance(node, ast.If):
        return False

    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _has_main_block(source: str) -> bool:
    # Top level only: a nested one does not make the module runnable.
    return any(_is_dunder_main_test(node) for node in ast.parse(source).body)


def _modules() -> list[Path]:
    files = sorted(_SRC.rglob("*.py"))
    assert files, "no modules found -- the layout moved and this test did not"
    return files


@pytest.mark.parametrize("path", _modules(), ids=lambda p: p.relative_to(_SRC).as_posix())
def test_only_the_declared_shims_are_runnable(path):
    relative = path.relative_to(_SRC).as_posix()
    runnable = path.name == "__main__.py" or _has_main_block(path.read_text())

    assert runnable == (relative in _RUNNABLE), (
        f"{relative} is {'runnable' if runnable else 'not runnable'}, and the contract "
        f"expects the opposite. Every way to start the console must route through the "
        f"guarded `mfgparams.__main__:main` (FR-011); a module made runnable here is a "
        f"new, unguarded entry point. Declared runnable modules: {sorted(_RUNNABLE)}."
    )


def test_the_declared_shims_all_exist():
    """A guard on the guard: losing a shim would make the check above vacuous."""

    for relative in _RUNNABLE:
        assert (_SRC / relative).is_file(), f"{relative} is declared runnable but does not exist"


@pytest.mark.parametrize(
    "source,runnable",
    [
        ('if __name__ == "__main__":\n    pass\n', True),
        ("if __name__ == '__main__':\n    pass\n", True),
        # Not a top-level block, so `python -m` never reaches it.
        ('def f():\n    if __name__ == "__main__":\n        pass\n', False),
        ('if __name__ == "__not_main__":\n    pass\n', False),
        ('if __file__ == "__main__":\n    pass\n', False),
        ("if __name__:\n    pass\n", False),
        ('x = "__main__"\n', False),
    ],
)
def test_the_detector_recognises_the_block(source, runnable):
    assert _has_main_block(source) is runnable
