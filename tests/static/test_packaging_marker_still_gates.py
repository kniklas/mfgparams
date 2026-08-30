"""Static check: the ``packaging`` assertions still run somewhere that gates.

Issue #75 P1.3 moved the wheel-contents assertions out of the ``test (3.x)``
matrix. That is only safe while something equally merge-blocking still runs
them. The failure mode is silent in both directions and invisible in a diff:

* drop ``-m packaging`` from the ``build`` job and they run **nowhere** in
  CI - every leg deselects them, so the suite goes green having verified
  nothing about the wheel;
* drop ``-m "not packaging"`` from the ``test`` job and the four isolated,
  network-touching ``python -m build`` runs come back inside required
  checks, which is the cost P1.3 removed.

``tox.ini``'s halves are checked too: ``envlist`` envs must deselect the
marker (this is what makes ``tox -p`` safe, issue #74) and the ``packaging``
env must exist to run them.
"""

from __future__ import annotations

import configparser
import pathlib

import pytest

yaml = pytest.importorskip("yaml")

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
TOX_INI = _REPO_ROOT / "tox.ini"

MARKER = "packaging"


def _run_steps(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


@pytest.fixture(scope="module")
def ci_jobs() -> dict:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"]


@pytest.fixture(scope="module")
def tox_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(TOX_INI, encoding="utf-8")
    return parser


def test_build_job_runs_the_packaging_assertions(ci_jobs: dict) -> None:
    """Something merge-blocking must still run them."""
    assert f"-m {MARKER}" in _run_steps(ci_jobs["build"]), (
        "the `build` job must run `pytest -m packaging`; without it the "
        "wheel-contents assertions run nowhere in CI, because every `test` "
        "leg deselects them"
    )


def test_test_matrix_deselects_the_packaging_assertions(ci_jobs: dict) -> None:
    """...and the matrix must not run them four more times."""
    assert f'-m "not {MARKER}"' in _run_steps(ci_jobs["test"]), (
        "the `test` matrix must deselect the packaging marker; running it "
        "per-interpreter puts four isolated `python -m build` invocations "
        "inside required checks (issue #75 P1.3)"
    )


def test_tox_envlist_deselects_the_packaging_assertions(
    tox_config: configparser.ConfigParser,
) -> None:
    """This is what makes ``tox -p`` safe (issue #74)."""
    assert f'-m "not {MARKER}"' in tox_config["testenv"]["commands"], (
        "tox's default testenv must deselect the packaging marker, or "
        "parallel envs race on the shared <repo>/build/ scratch tree"
    )


def test_tox_has_a_packaging_env_outside_envlist(
    tox_config: configparser.ConfigParser,
) -> None:
    section = f"testenv:{MARKER}"
    assert tox_config.has_section(section), (
        f"tox.ini must define [{section}] so the assertions deselected from "
        "envlist are still runnable locally"
    )
    assert f"-m {MARKER}" in tox_config[section]["commands"]
    assert MARKER not in tox_config["tox"]["envlist"], (
        f"the {MARKER!r} env must stay out of envlist: running it in "
        "parallel with itself reinstates the <repo>/build/ race (#74)"
    )


def test_marker_is_registered(ci_jobs: dict) -> None:
    """An unregistered marker silently deselects nothing under ``--strict-markers``
    and, worse, typos in ``-m`` expressions match no tests at all."""
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'"{MARKER}: ' in pyproject, (
        f"the {MARKER!r} marker must be declared in " "[tool.pytest.ini_options].markers"
    )
