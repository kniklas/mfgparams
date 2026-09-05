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


def _packaging_step(job: dict) -> dict | None:
    for step in job["steps"]:
        if f"-m {MARKER}" in step.get("run", ""):
            return step
    return None


def test_build_job_runs_the_packaging_assertions(ci_jobs: dict) -> None:
    """Something merge-blocking must still run them."""
    assert _packaging_step(ci_jobs["build"]) is not None, (
        "the `build` job must run `pytest -m packaging`; without it the "
        "wheel-contents assertions run nowhere in CI, because every `test` "
        "leg deselects them"
    )


def test_the_packaging_step_can_actually_fail_the_build_job(ci_jobs: dict) -> None:
    """Present is not the same as blocking.

    Asserting only that the step's text exists lets a disabled step satisfy
    the guard: ``continue-on-error: true`` keeps ``pytest -m packaging`` in
    the file while the assertions lose the ability to redden ``build``. That
    is the likely edit here precisely because this step's isolated,
    PyPI-touching build is the flakiness P1.3 moved out of the matrix - when
    it goes red, ``continue-on-error`` is what someone reaches for. Same
    decorative-guard shape ``test_ci_ok_aggregate_check.py`` guards at job
    level.
    """
    step = _packaging_step(ci_jobs["build"])
    assert step is not None
    build_job = ci_jobs["build"]
    for holder, label in ((step, "the packaging step"), (build_job, "the build job")):
        assert not holder.get("continue-on-error"), (
            f"{label} must not set continue-on-error: the wheel-contents "
            "assertions would stop being able to fail a required check"
        )

    assert "if" not in step, (
        "the packaging step must not be conditional: a condition that "
        "evaluates false leaves the wheel unverified while CI stays green"
    )
    # The job itself carries `if: github.event_name != 'schedule'`, like every
    # other gating job - a scheduled run has no pull request to gate. Any
    # *other* condition would narrow when the wheel gets verified - except
    # the one specs/016-ci-path-based-selection adds, which is safe only
    # because it preserves the schedule exclusion, runs `build` anyway when
    # the `changes` job itself fails (fail-open), and always runs for an
    # unmatched path (`other`); see tests/static/test_ci_path_selection.py
    # for the dedicated checks on those properties across every filtered job.
    # A condition missing any of those three pieces is exactly the silent
    # narrowing this test exists to catch.
    condition = build_job.get("if")
    if condition not in (None, "github.event_name != 'schedule'"):
        assert condition is not None
        assert "github.event_name != 'schedule'" in condition, (
            f"the build job's condition is {condition!r} and dropped the "
            "schedule exclusion - the wheel would be (pointlessly) verified "
            "on the weekly cron with no pull request to gate"
        )
        assert "needs.changes.result == 'failure'" in condition, (
            f"the build job's condition is {condition!r} and is missing the "
            "path-selection fail-open clause - a broken `changes` job would "
            "silently skip wheel verification instead of running it anyway"
        )
        assert "needs.changes.outputs.other == 'true'" in condition, (
            f"the build job's condition is {condition!r} and is missing the "
            "unmatched-path catch-all - an unanticipated changed path would "
            "silently skip wheel verification instead of running it anyway"
        )


def test_build_job_installs_the_extra_that_makes_them_run(ci_jobs: dict) -> None:
    """Otherwise they *skip*, and skipping is exit 0.

    ``_build_wheel`` guards with ``pytest.importorskip("build.__main__")``,
    so if ``build`` ever leaves the ``test`` extra - or this job's install is
    narrowed - the step reports "skipped", exits 0, and ``build`` goes green
    with the wheel entirely unverified. Before P1.3 that silent skip was
    spread across four legs; now this is the only place CI verifies the
    wheel at all, so the whole gate can vanish without anything going red.
    """
    install_steps = _run_steps(ci_jobs["build"])
    assert '".[test]"' in install_steps or "'.[test]'" in install_steps, (
        "the `build` job must install the `test` extra, which is what "
        "provides `build` and stops the packaging assertions from being "
        "importorskip-ed into a silent pass"
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
