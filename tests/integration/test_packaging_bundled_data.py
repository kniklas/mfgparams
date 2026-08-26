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
