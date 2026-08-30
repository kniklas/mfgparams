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
import re
import shlex

import pytest

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
    # `importorskip`, not a module-level import: a bare checkout installed
    # with a plain `pip install -e .` (no extras) is a supported way to run
    # this suite, and an unguarded import would make that a collection error.
    # Scoped to this fixture rather than the module so the tox-only checks -
    # `package = editable`, and no restated `--cov-fail-under` - still run
    # there, instead of the whole module skipping green having verified
    # nothing (code review finding; same reasoning as
    # `test_python_version_consistency.py`).
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"]["test"]


@pytest.fixture(scope="module")
def tox_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(TOX_INI, encoding="utf-8")
    return parser


def _tox_version_envs(config: configparser.ConfigParser) -> list[str]:
    """``[testenv]`` plus every per-version override of it.

    Reading only ``[testenv]`` leaves the hole the sibling
    `test_packaging_marker_still_gates.py` already closes: tox lets
    ``[testenv:py39]`` replace ``extras``, ``package`` or ``commands``
    outright, so a single override reintroduces all three #71 variants with
    this module reporting success. ``[testenv:packaging]`` is excluded - it
    deliberately runs a different selection, and CI runs it in the `build`
    job, not the `test` matrix (code review finding).
    """
    return ["testenv"] + [
        name
        for name in config.sections()
        if name.startswith("testenv:") and name != "testenv:packaging"
    ]


def _tox_setting(config: configparser.ConfigParser, env: str, key: str) -> str | None:
    """``key`` as ``env`` defines it, or ``None`` when it inherits."""
    value = config[env].get(key) if config.has_section(env) or env == "testenv" else None
    return value.strip() if value is not None else None


def _ci_run_steps(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def _ci_pytest_command(job: dict) -> str:
    """The single line in the job that invokes pytest.

    Matched by tokenising each line rather than `startswith("pytest ")`: a
    step rewritten as `python -m pytest ...` (the usual fix when `pytest`
    resolves outside the venv), or a `run: |` block whose first line is
    `set -euo pipefail`, is a legitimate refactor that a prefix match
    reports as "no pytest invocation found" - blaming the workflow for the
    matcher's limitation. Taking the matching *line* also stops a
    multi-line block's other tokens leaking in as phantom CI-only arguments
    (code review finding).
    """
    lines = [
        line.strip()
        for step in _ci_run_steps(job)
        for line in step.splitlines()
        if "pytest" in shlex.split(line)
    ]
    assert len(lines) == 1, (
        f"expected exactly one pytest invocation in CI's test job, found "
        f"{lines!r}; this module's parity checks assume a single one"
    )
    return lines[0]


def _pytest_arguments(command: str) -> list[tuple[str, str | None]]:
    """Arguments after ``pytest`` as ordered ``(flag, value)`` pairs.

    A flat set loses the flag-to-value association, so
    ``-m fast -k "not packaging"`` and ``-m "not packaging" -k fast``
    compare equal while selecting disjoint tests - exactly the divergence
    this module exists to catch. It also collapses repeated flags such as
    ``-W`` (code review finding).
    """
    tokens = shlex.split(command)
    tokens = tokens[tokens.index("pytest") + 1 :]
    pairs: list[tuple[str, str | None]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("-") and "=" in token:
            flag, _, value = token.partition("=")
            pairs.append((flag, value))
        elif (
            token.startswith("-")
            and index + 1 < len(tokens)
            and not tokens[index + 1].startswith("-")
        ):
            pairs.append((token, tokens[index + 1]))
            index += 1
        else:
            pairs.append((token, None))
        index += 1
    return pairs


def _ci_installed_extras(job: dict) -> set[str]:
    """Every ``.[...]`` extra CI's test job installs.

    A membership check ("tox's extra appears somewhere") passes when CI
    installs a *superset*. Adding `.[dev]` alongside `.[test]` is the #71
    divergence returning in the direction this job's own comment warns
    about: with `dev` present, `test (3.9)` fails at install time the first
    time `sphinx`/`mypy`/`bandit` drops 3.9 (code review finding).
    """
    return set(re.findall(r"\.\[([^\]]+)\]", "\n".join(_ci_run_steps(job))))


def test_ci_and_tox_install_the_same_extra(
    ci_test_job: dict, tox_config: configparser.ConfigParser
) -> None:
    """#71: CI installed ``.[dev]`` while tox installed ``.[test]``."""
    ci_extras = _ci_installed_extras(ci_test_job)
    for env in _tox_version_envs(tox_config):
        extra = _tox_setting(tox_config, env, "extras")
        if extra is None:  # inherits [testenv], already checked
            continue
        assert ci_extras == {extra}, (
            f"[{env}] installs the {extra!r} extra; CI's test job installs "
            f"{sorted(ci_extras)}. They must match exactly - a superset on "
            f"either side means the two run against different dependency "
            f"sets while both report green (issue #71)"
        )


def test_ci_and_tox_install_in_the_same_mode(
    ci_test_job: dict, tox_config: configparser.ConfigParser
) -> None:
    """#71's worst variant: tox's ``sdist`` default ran a smaller suite.

    At least one test keys off whether it is running from a source checkout
    (``tests/unit/test_version_single_source.py`` resolves the repo root
    from ``mfgparams.__file__``), so a non-editable install silently skips
    it. Both sides must install editable.
    """
    for env in _tox_version_envs(tox_config):
        package = _tox_setting(tox_config, env, "package")
        if package is None:
            continue
        assert package == "editable", (
            f"[{env}] sets `package = {package}`; tox 4's `sdist` default "
            "silently runs a smaller suite than CI (issue #71)"
        )
    installs = "\n".join(_ci_run_steps(ci_test_job))
    assert "pip install -e " in installs, (
        "CI's test job must install editable (`pip install -e`), matching "
        "tox's `package = editable`"
    )


def test_ci_and_tox_pass_the_same_pytest_arguments(
    ci_test_job: dict, tox_config: configparser.ConfigParser
) -> None:
    """Any flag on one side only must be declared above, with a reason."""
    ci_args = _pytest_arguments(_ci_pytest_command(ci_test_job))
    ci_only_allowed = {(flag, None) for flag in CI_ONLY_PYTEST_ARGS} | {
        (flag.partition("=")[0], flag.partition("=")[2])
        for flag in CI_ONLY_PYTEST_ARGS
        if "=" in flag
    }

    for env in _tox_version_envs(tox_config):
        commands = _tox_setting(tox_config, env, "commands")
        if commands is None:
            continue
        tox_args = _pytest_arguments(commands)
        tox_only_allowed = {(flag, None) for flag in TOX_ONLY_PYTEST_ARGS}

        unexplained_ci_only = set(ci_args) - set(tox_args) - ci_only_allowed
        unexplained_tox_only = set(tox_args) - set(ci_args) - tox_only_allowed

        assert not unexplained_ci_only, (
            f"CI's test job passes {sorted(unexplained_ci_only)} to pytest "
            f"and [{env}] does not. Add it to tox.ini so both run the same "
            f"suite, or add it to CI_ONLY_PYTEST_ARGS in this file with the "
            f"reason."
        )
        assert not unexplained_tox_only, (
            f"[{env}] passes {sorted(unexplained_tox_only)} to pytest and "
            f"CI does not. Add it to ci.yml, or to TOX_ONLY_PYTEST_ARGS "
            f"here with the reason."
        )


def test_coverage_threshold_is_not_restated_on_either_command_line(
    ci_test_job: dict, tox_config: configparser.ConfigParser
) -> None:
    """#71: ``--cov-fail-under`` on the command line *overrides* ``addopts``.

    Unlike ``--cov-report``, it does not accumulate - so restating it on
    either command line means bumping the threshold in ``pyproject.toml``
    changes it for one runner and not the other. It belongs only in
    ``[tool.pytest.ini_options].addopts``, the single source both inherit.
    """
    commands = [("CI's test job", _ci_pytest_command(ci_test_job))]
    for env in _tox_version_envs(tox_config):
        value = _tox_setting(tox_config, env, "commands")
        if value is not None:
            commands.append((f"[{env}]", value))

    for label, command in commands:
        assert "--cov-fail-under" not in command, (
            f"{label} restates --cov-fail-under; it silently overrides "
            "addopts rather than accumulating, so the two runners would "
            "enforce different thresholds (issue #71)"
        )
