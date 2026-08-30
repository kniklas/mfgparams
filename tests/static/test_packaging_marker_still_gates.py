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
    """This is what makes ``tox -p`` safe (issue #74).

    Checks the base ``[testenv]`` *and* every per-version override. tox lets
    ``[testenv:py39]`` replace ``commands`` outright, so asserting only on
    the base section leaves a hole: one such override reinstates four
    isolated ``python -m build`` runs and re-opens the ``<repo>/build/``
    race while this guard stays green. That is the same shape as the #71
    finding where a version check was not scoped to ``jobs.test``.
    """
    sections = ["testenv"] + [
        name
        for name in tox_config.sections()
        if name.startswith("testenv:") and name != f"testenv:{MARKER}"
    ]
    for name in sections:
        commands = tox_config[name].get("commands")
        if commands is None:  # inherits [testenv], already checked
            continue
        assert f'-m "not {MARKER}"' in commands, (
            f"[{name}] must deselect the packaging marker, or parallel envs "
            "race on the shared <repo>/build/ scratch tree (#74)"
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


def test_marker_is_registered() -> None:
    """Registration is what makes the marker name reviewable in one place.

    An unregistered marker is not silent - pytest warns, and under
    ``--strict-markers`` it is a hard collection error. The reason to
    assert it here is that ``-m`` expressions are strings scattered across
    ``ci.yml`` and ``tox.ini``: the declaration in ``pyproject.toml`` is
    the one place a reviewer can see what the marker means and that its
    name is spelled the same everywhere.
    """
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'"{MARKER}: ' in pyproject, (
        f"the {MARKER!r} marker must be declared in " "[tool.pytest.ini_options].markers"
    )
