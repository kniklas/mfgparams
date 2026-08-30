"""Static check: ``tox`` and CI's ``test`` job run the *same* thing.

README.md and
``specs/013-tox-multi-python-testing/contracts/multi-version-testing-contract.md``
both promise a contributor that a green ``tox`` means a green ``test``
matrix. Nothing enforced that promise, and every way of breaking it is
invisible: both sides stay green, they just test different things. Issue
#71 hit all three variants in one pull request:

* **extras** - CI installed ``.[dev]`` while tox installed ``.[test]``;
* **pytest flags** - CI restated ``--cov-fail-under=90`` on the command
  line, which *overrides* ``addopts`` rather than accumulating, so raising
  the threshold in ``pyproject.toml`` would have raised it for tox while CI
  silently kept enforcing the old value;
* **install mode** - tox 4 defaults to ``package = sdist``, so tox ran a
  **smaller suite** than CI (814 tests versus 815) for the whole pull
  request, undetected until review round 6 of 10.

All three are fixed. This module exists so they cannot come back (#75 P1.2).

The pytest-argument check is deliberately an *agreement* test with an
explicit allowlist rather than a list of required flags: a flag added to
one side and not the other fails here by default, so the person adding it
has to either add it to both or record why it belongs to one. That is the
property the three findings above all violated.

Not covered here, on purpose: this asserts the two *definitions* agree, not
that they produce identical results. Only actually running both does that,
which is what CI and ``tox`` already are.
"""

from __future__ import annotations

import configparser
import pathlib
import shlex

import pytest

yaml = pytest.importorskip("yaml")

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
TOX_INI = _REPO_ROOT / "tox.ini"

# Arguments legitimately passed by only one side. Each needs a reason, and
# adding to this set is the reviewable moment - it is how a real divergence
# gets noticed instead of merged.
CI_ONLY_PYTEST_ARGS = {
    # Produces the coverage.xml the Codecov upload step consumes. tox has no
    # Codecov step, and writing the file there would be dead output.
    "--cov-report=xml",
}
TOX_ONLY_PYTEST_ARGS = {
    # tox's passthrough for `tox -e py311 -- -k foo`. CI never forwards
    # user arguments.
    "{posargs}",
}


@pytest.fixture(scope="module")
def ci_test_job() -> dict:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"]["test"]


@pytest.fixture(scope="module")
def tox_testenv() -> configparser.SectionProxy:
    parser = configparser.ConfigParser()
    parser.read(TOX_INI, encoding="utf-8")
    return parser["testenv"]


def _ci_run_steps(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def _pytest_arguments(command: str) -> set[str]:
    """Arguments after the ``pytest`` token, as a set."""
    tokens = shlex.split(command)
    return set(tokens[tokens.index("pytest") + 1 :])


def _ci_pytest_command(job: dict) -> str:
    commands = [step for step in _ci_run_steps(job) if step.startswith("pytest ")]
    assert len(commands) == 1, (
        f"expected exactly one pytest invocation in CI's test job, found "
        f"{commands!r}; this module's parity checks assume a single one"
    )
    return commands[0]


def test_ci_and_tox_install_the_same_extra(
    ci_test_job: dict, tox_testenv: configparser.SectionProxy
) -> None:
    """#71: CI installed ``.[dev]`` while tox installed ``.[test]``."""
    extra = tox_testenv["extras"].strip()
    installs = "\n".join(_ci_run_steps(ci_test_job))
    assert f'".[{extra}]"' in installs or f"'.[{extra}]'" in installs, (
        f"tox's testenv installs the {extra!r} extra; CI's test job must "
        f"install the same one, or the two run against different dependency "
        f"sets while both report green"
    )


def test_ci_and_tox_install_in_the_same_mode(
    ci_test_job: dict, tox_testenv: configparser.SectionProxy
) -> None:
    """#71's worst variant: tox's ``sdist`` default ran a smaller suite.

    At least one test keys off whether it is running from a source checkout
    (``tests/unit/test_version_single_source.py`` resolves the repo root
    from ``mfgparams.__file__``), so a non-editable install silently skips
    it. Both sides must install editable.
    """
    assert tox_testenv["package"].strip() == "editable", (
        "tox must set `package = editable`; tox 4 defaults to `sdist`, "
        "which silently runs a smaller suite than CI (issue #71)"
    )
    installs = "\n".join(_ci_run_steps(ci_test_job))
    assert "pip install -e " in installs, (
        "CI's test job must install editable (`pip install -e`), matching "
        "tox's `package = editable`"
    )


def test_ci_and_tox_pass_the_same_pytest_arguments(
    ci_test_job: dict, tox_testenv: configparser.SectionProxy
) -> None:
    """Any flag on one side only must be declared above, with a reason."""
    ci_args = _pytest_arguments(_ci_pytest_command(ci_test_job))
    tox_args = _pytest_arguments(tox_testenv["commands"].strip())

    unexplained_ci_only = ci_args - tox_args - CI_ONLY_PYTEST_ARGS
    unexplained_tox_only = tox_args - ci_args - TOX_ONLY_PYTEST_ARGS

    assert not unexplained_ci_only, (
        f"CI's test job passes {sorted(unexplained_ci_only)} to pytest and "
        f"tox does not. Add it to tox.ini so both run the same suite, or "
        f"add it to CI_ONLY_PYTEST_ARGS in this file with the reason."
    )
    assert not unexplained_tox_only, (
        f"tox passes {sorted(unexplained_tox_only)} to pytest and CI does "
        f"not. Add it to ci.yml, or to TOX_ONLY_PYTEST_ARGS here with the "
        f"reason."
    )


def test_coverage_threshold_is_not_restated_on_either_command_line(
    ci_test_job: dict, tox_testenv: configparser.SectionProxy
) -> None:
    """#71: ``--cov-fail-under`` on the command line *overrides* ``addopts``.

    Unlike ``--cov-report``, it does not accumulate - so restating it on
    either command line means bumping the threshold in ``pyproject.toml``
    changes it for one runner and not the other. It belongs only in
    ``[tool.pytest.ini_options].addopts``, the single source both inherit.
    """
    for label, command in (
        ("CI's test job", _ci_pytest_command(ci_test_job)),
        ("tox's testenv", tox_testenv["commands"].strip()),
    ):
        assert "--cov-fail-under" not in command, (
            f"{label} restates --cov-fail-under; it silently overrides "
            "addopts rather than accumulating, so the two runners would "
            "enforce different thresholds (issue #71)"
        )
