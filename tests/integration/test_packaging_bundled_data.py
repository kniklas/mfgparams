"""Packaging test: bundled TOML files ship inside a built wheel (T017;
quickstart.md Scenario 2).

Invokes ``python -m build`` and inspects the resulting wheel's namelist.
Skipped if the ``build`` package is not installed (dev-only tooling).

The skip check imports ``build.__main__`` specifically, not just ``build``:
running ``python -m build`` locally leaves a ``build/`` scratch directory at
the repo root (gitignored, but not cleaned up afterward) as a side effect,
regardless of ``--outdir``. On an interpreter where the real ``build``
package isn't installed (e.g. a `tox` environment, since it's dev-only
tooling not part of the ``dev`` extra), Python's implicit namespace-package
mechanism resolves ``import build`` to that stray directory instead of
raising ``ImportError`` — which used to make ``pytest.importorskip("build")``
wrongly not skip, and the test would then fail instead of being skipped
(specs/013-tox-multi-python-testing; found via `tox` erroring on every
Python version after a local `python -m build` run). A namespace package has
no ``__main__`` submodule, so importing that specifically still raises
``ImportError`` and skips correctly either way.
"""

from __future__ import annotations

import glob
import importlib.machinery
import inspect
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib  # type: ignore[no-redef]

import pytest


def test_wheel_contains_bundled_materials_and_tools_toml(tmp_path):
    pytest.importorskip("build.__main__")

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert (
        result.returncode == 0
    ), f"python -m build failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    wheels = glob.glob(str(tmp_path / "*.whl"))
    assert wheels, "expected python -m build to produce a wheel"

    names = zipfile.ZipFile(wheels[0]).namelist()
    assert any(n.endswith("data/materials.toml") for n in names), names
    assert any(n.endswith("drilling/data/tools.toml") for n in names), names
    assert any(n.endswith("end_milling/data/tools.toml") for n in names), names
    assert any(n.endswith("face_milling/data/tools.toml") for n in names), names


def test_packaged_materials_include_hardwood_softwood_and_engineered(tmp_path):
    pytest.importorskip("build.__main__")

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr

    wheel_path = Path(sorted(glob.glob(str(tmp_path / "*.whl")))[0])
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


def test_packaging_tests_guard_against_build_dunder_main_not_bare_build():
    """Source-level guard: confirms the two tests above still call
    `pytest.importorskip("build.__main__")`, not the bare `"build"` this
    file used before specs/013-tox-multi-python-testing -- a plain
    string-literal revert wouldn't be caught by
    `test_stray_build_scratch_directory_does_not_fool_the_skip_guard` alone,
    since that test only proves the general mechanism, not that these two
    call sites actually use it.
    """
    for test_func in (
        test_wheel_contains_bundled_materials_and_tools_toml,
        test_packaged_materials_include_hardwood_softwood_and_engineered,
    ):
        source = inspect.getsource(test_func)
        assert 'importorskip("build.__main__")' in source, (
            f"{test_func.__name__} must guard with "
            'pytest.importorskip("build.__main__"), not the bare "build"'
        )
