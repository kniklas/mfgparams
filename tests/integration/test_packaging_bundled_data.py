"""Packaging test: bundled TOML files ship inside a built wheel (T017;
quickstart.md Scenario 2).

Invokes ``python -m build`` and inspects the resulting wheel's namelist.

``build`` is part of the ``test`` extra (which ``dev`` includes via
``mfgparams[test]``), so `tox` and CI's `test` job both run these assertions
for real — they are not skipped in automation. The ``importorskip`` guard is
for the remaining case: a bare environment with neither extra installed, e.g.
someone running ``pytest`` against a plain ``pip install -e .`` checkout.

That guard imports ``build.__main__`` specifically, not just ``build``:
running ``python -m build`` leaves a ``build/`` scratch directory at the repo
root (gitignored, but not cleaned up afterward) as a side effect, regardless
of ``--outdir``. On an interpreter where the real ``build`` package isn't
installed, Python's implicit namespace-package mechanism resolves
``import build`` to that stray directory instead of raising ``ImportError``
— which used to make ``pytest.importorskip("build")`` wrongly not skip, and
the test would then fail instead of being skipped
(specs/013-tox-multi-python-testing; found via `tox` erroring on every Python
version after a local `python -m build` run, back when `tox` installed an
extra that did not carry ``build``). A namespace package has no ``__main__``
submodule, so importing that specifically still raises ``ImportError`` and
skips correctly either way.
"""

from __future__ import annotations

import ast
import glob
import importlib.machinery
import inspect
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib  # type: ignore[no-redef]

import pytest


def _build_wheel(outdir: Path) -> Path:
    """Build the project's wheel into ``outdir`` and return its path, skipping
    the calling test if the ``build`` package isn't importable.

    Note this uses `build`'s default *isolated* mode, which pip-installs the
    `[build-system].requires` backend into a throwaway environment — i.e. it
    touches the network. That is deliberate: it exercises the same path a real
    `pip install mfgparams` takes, which is the whole point of asserting on the
    wheel's contents. The cost is contained by building **once** per module
    rather than once per test (code review finding); the environment that runs
    these tests already had to reach PyPI to install `.[test]` in the first
    place, so this adds no new class of dependency.
    """
    pytest.importorskip("build.__main__")

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert (
        result.returncode == 0
    ), f"python -m build failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    wheels = sorted(glob.glob(str(outdir / "*.whl")))
    assert wheels, "expected python -m build to produce a wheel"
    return Path(wheels[0])


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory) -> Path:
    """One wheel build shared by every test in this module."""
    return _build_wheel(tmp_path_factory.mktemp("wheel"))


def test_wheel_contains_bundled_materials_and_tools_toml(built_wheel):
    names = zipfile.ZipFile(built_wheel).namelist()
    assert any(n.endswith("data/materials.toml") for n in names), names
    assert any(n.endswith("drilling/data/tools.toml") for n in names), names
    assert any(n.endswith("end_milling/data/tools.toml") for n in names), names
    assert any(n.endswith("face_milling/data/tools.toml") for n in names), names


def test_packaged_materials_include_hardwood_softwood_and_engineered(built_wheel):
    wheel_path = built_wheel
    with zipfile.ZipFile(wheel_path) as archive:
        materials_file = next(
            name for name in archive.namelist() if name.endswith("data/materials.toml")
        )
        data = tomllib.loads(archive.read(materials_file).decode("utf-8"))

    names = [entry["name"] for entry in data["materials"]]
    for required in ("Oak", "Maple", "Pine", "Spruce", "Fir", "Plywood", "MDF"):
        assert required in names


def test_stray_build_scratch_directory_does_not_fool_the_skip_guard(tmp_path):
    """Regression test for the shadowing bug fixed in
    specs/013-tox-multi-python-testing: a `build/` directory with no
    `__init__.py` (exactly what `python -m build` leaves behind at the repo
    root) is resolved by Python as an implicit namespace package. Confirms
    that shape of "fake" `build` package satisfies a bare `import build` but
    not `import build.__main__` -- the actual property the two tests above
    rely on `pytest.importorskip("build.__main__")` to detect.

    Uses `importlib.machinery.PathFinder.find_spec` scoped to a `path=[...]`
    containing only the fake directory, rather than mutating `sys.path`/
    `sys.modules` on the real interpreter: this test's own process may have
    the genuine `build` package installed (dev-only tooling, present when
    running the full local suite), and per PEP 420 a regular package found
    anywhere on `sys.path` always wins over an earlier namespace-package
    candidate -- so a `sys.path`-based simulation wouldn't actually
    reproduce the bug on such an interpreter.
    """
    (tmp_path / "build").mkdir()

    spec = importlib.machinery.PathFinder.find_spec("build", path=[str(tmp_path)])
    assert spec is not None, "expected an implicit namespace package to be found"
    assert spec.origin is None, "expected a namespace package (no __init__.py, no origin file)"

    main_spec = importlib.machinery.PathFinder.find_spec(
        "build.__main__", path=spec.submodule_search_locations
    )
    assert main_spec is None, "a namespace package must not resolve build.__main__"


def _importorskip_arguments(func) -> list[str]:
    """Every constant argument passed to an ``importorskip(...)`` call inside
    ``func``, found by parsing the function rather than by matching source
    text.

    A substring check over `inspect.getsource` was the original
    implementation and is not semantic: it fails on a pure restyle (single
    quotes, a line break inside the call) while a mere *comment* containing
    the literal would satisfy it even if the real call had been reverted to
    the bare `"build"`. This mirrors the ast-based approach
    `tests/static/test_no_hardcoded_strings.py` already uses for the same
    shape of source-level guard (code review finding,
    specs/013-tox-multi-python-testing).
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    return [
        arg.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Attribute) and node.func.attr == "importorskip")
            or (isinstance(node.func, ast.Name) and node.func.id == "importorskip")
        )
        for arg in node.args
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    ]


def test_packaging_tests_guard_against_build_dunder_main_not_bare_build():
    """Source-level guard: confirms `_build_wheel` -- the single place the two
    wheel-content tests above reach `python -m build` through -- still skips on
    `"build.__main__"`, not the bare `"build"` this file used before
    specs/013-tox-multi-python-testing. A plain string-literal revert wouldn't
    be caught by
    `test_stray_build_scratch_directory_does_not_fool_the_skip_guard` alone,
    since that test only proves the general mechanism, not that the real call
    site uses it.
    """
    arguments = _importorskip_arguments(_build_wheel)
    assert arguments == ["build.__main__"], (
        "_build_wheel must guard with "
        'pytest.importorskip("build.__main__"), not the bare "build" -- '
        f"found {arguments!r}"
    )
