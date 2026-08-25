"""Test: the package version has exactly one source of truth (T052).

Constitution Principle IV requires a single version definition. ``pyproject.toml``
declares ``dynamic = ["version"]`` and reads ``mfgparams.__version__``, so
the two can only agree — this test fails loudly if anyone reintroduces a
hard-coded ``[project] version`` alongside it.
"""

from __future__ import annotations

import re
from importlib import metadata
from pathlib import Path

import pytest

import mfgparams

_PYPROJECT = Path(mfgparams.__file__).resolve().parents[2] / "pyproject.toml"


def test_runtime_version_matches_the_installed_distribution():
    assert mfgparams.__version__ == metadata.version("mfgparams")


def test_version_is_a_valid_release_identifier():
    assert re.fullmatch(r"\d+\.\d+\.\d+", mfgparams.__version__)


@pytest.mark.skipif(not _PYPROJECT.is_file(), reason="not an editable/source checkout")
def test_pyproject_does_not_redeclare_a_static_version():
    project_table = _PYPROJECT.read_text().split("[project]", 1)[1].split("\n[", 1)[0]

    assert 'dynamic = ["version"]' in project_table
    assert not re.search(r"^version\s*=", project_table, re.MULTILINE), (
        "pyproject.toml must not declare a static [project] version; the "
        "single source of truth is mfgparams.__version__ (Constitution IV)"
    )


def test_milling_release_is_at_least_the_minor_that_introduced_it():
    """Milling is an additive public API, shipped in 0.3.0 or later."""

    major, minor, _patch = (int(part) for part in mfgparams.__version__.split("."))

    assert (major, minor) >= (0, 3)
    assert hasattr(mfgparams, "calculate_end_milling")
    assert hasattr(mfgparams, "calculate_face_milling")
