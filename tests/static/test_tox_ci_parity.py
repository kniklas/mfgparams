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

The pytest-argument check compares normalised token *sequences* rather than
parsing flags and values. An earlier version paired ``(flag, value)`` by
hand and had to guess which flags take a value, which mis-paired
``--no-cov {posargs}``; comparing sequences needs no such guess. Order
sensitivity is deliberate - both sides are meant to be written the same
way, and a diff of two sequences is a better failure message than a set
difference.

Not covered here, on purpose: this asserts the two *definitions* agree, not
that they produce identical results. Only running both does that, which is
what CI and ``tox`` already are.
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

# Settings `[testenv]` must declare outright. Skipping a missing key is
# right for a `[testenv:*]` override (it inherits) but wrong for `[testenv]`
# itself, which inherits from nothing: deleting `package` there reverts tox
# to its `sdist` default - the 814-vs-815 divergence above - and a
# skip-if-absent check passes green (code review finding).
REQUIRED_TESTENV_SETTINGS = ("extras", "package", "commands")

# Arguments legitimately passed by only one side. Each needs a reason, and
# adding to this set is the reviewable moment - it is how a real divergence
# gets noticed instead of merged.
CI_ONLY_PYTEST_ARGS = (
    # Produces the coverage.xml the Codecov upload step consumes. tox has no
    # Codecov step, and writing the file there would be dead output.
    "--cov-report=xml",
)
TOX_ONLY_PYTEST_ARGS = (
    # tox's passthrough for `tox -e py311 -- -k foo`. CI never forwards
    # user arguments.
    "{posargs}",
)


def _ci_test_job() -> dict:
    """CI's ``test`` job.

    A plain helper rather than a fixture, and ``importorskip`` rather than a
    module-level import: a bare checkout installed with ``pip install -e .``
    (no extras) is a supported way to run this suite, and an unguarded
    import would make that a collection error. Only the checks that actually
    need CI call this, so the tox-only assertions still run in such an
    environment instead of the whole module skipping green having verified
    nothing. An earlier version put this in a fixture that *every* test
    requested, which had exactly the outcome it claimed to prevent (code
    review finding; same shape as ``test_python_version_consistency.py``).
    """
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"]["test"]


@pytest.fixture(scope="module")
def tox_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(TOX_INI, encoding="utf-8")
    return parser


def _split_tokens(text: str) -> list[str]:
    """``shlex.split`` that tolerates shell content it cannot parse.

    An apostrophe in a comment inside a ``run: |`` block ("# don't cache")
    makes ``shlex.split`` raise ``No closing quotation``. Without this the
    module fails with an opaque traceback on an unrelated workflow edit
    (code review finding).
    """
    try:
        return shlex.split(text)
    except ValueError:
        return []


def _invokes_pytest(tokens: list[str]) -> bool:
    """True when these tokens *run* pytest, rather than merely mentioning it.

    ``pip install pytest pytest-cov`` contains the token and does not
    invoke it; ``python -m pytest`` does (code review finding).
    """
    if not tokens:
        return False
    if tokens[0] == "pytest":
        return True
    return tokens[:3] == ["python", "-m", "pytest"]


def _pytest_arguments(command: str) -> list[str]:
    tokens = _split_tokens(command)
    return tokens[tokens.index("pytest") + 1 :]


def _without(arguments: list[str], allowed: tuple[str, ...]) -> list[str]:
    return [argument for argument in arguments if argument not in allowed]


def _tox_pytest_envs(config: configparser.ConfigParser) -> list[str]:
    """``[testenv]`` plus every per-version override that runs pytest.

    Reading only ``[testenv]`` leaves the hole the sibling
    ``test_packaging_marker_still_gates.py`` already closes: tox lets
    ``[testenv:py39]`` replace ``extras``, ``package`` or ``commands``
    outright, so one override reintroduces all three #71 variants with this
    module reporting success.

    Envs that do not run pytest are skipped, not an error: a future
    ``[testenv:lint]`` running ``ruff`` is legitimate, and the sibling
    ``test_python_version_consistency.py`` already treats such envs as
    expected. ``[testenv:packaging]`` is excluded for a different reason -
    it runs a different selection by design, and CI runs it in ``build``,
    not the ``test`` matrix (code review findings).
    """
    envs = ["testenv"] + [
        name
        for name in config.sections()
        if name.startswith("testenv:") and name != "testenv:packaging"
    ]
    return [
        env
        for env in envs
        if env == "testenv" or _invokes_pytest(_split_tokens(config[env].get("commands", "")))
    ]


def _tox_setting(config: configparser.ConfigParser, env: str, key: str) -> str | None:
    """``key`` as ``env`` defines it, or ``None`` when it inherits."""
    if not config.has_section(env):
        return None
    value = config[env].get(key)
    return value.strip() if value is not None else None


def _extras(value: str) -> set[str]:
    """tox's whitespace-separated list and CI's comma-separated one, as sets."""
    return {item for item in re.split(r"[,\s]+", value) if item}


def _ci_run_steps(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def _ci_pytest_command(job: dict) -> str:
    """The single line in the job that invokes pytest.

    Matched by tokenising each line rather than by prefix: a step rewritten
    as ``python -m pytest`` (the usual fix when ``pytest`` resolves outside
    the venv), or a ``run: |`` block whose first line is
    ``set -euo pipefail``, is a legitimate refactor that a prefix match
    reports as "no pytest invocation found" - blaming the workflow for the
    matcher. Taking the matching *line* also stops a multi-line block's
    other tokens leaking in as phantom CI-only arguments (code review
    finding).
    """
    lines = [
        line.strip()
        for step in _ci_run_steps(job)
        for line in step.splitlines()
        if _invokes_pytest(_split_tokens(line))
    ]
    assert len(lines) == 1, (
        f"expected exactly one pytest invocation in CI's test job, found "
        f"{lines!r}; this module's parity checks assume a single one"
    )
    return lines[0]


def test_testenv_declares_the_settings_this_module_compares(
    tox_config: configparser.ConfigParser,
) -> None:
    """``[testenv]`` inherits from nothing, so a missing key is a divergence.

    Every other check below skips a section that does not define a setting,
    which is correct for an override and wrong here.
    """
    for key in REQUIRED_TESTENV_SETTINGS:
        assert _tox_setting(tox_config, "testenv", key) is not None, (
            f"tox.ini's [testenv] must declare `{key}` explicitly. Dropping "
            f"it falls back to tox's default - for `package` that is "
            f"`sdist`, which silently runs a smaller suite than CI (#71)"
        )


def test_ci_and_tox_install_the_same_extra(
    tox_config: configparser.ConfigParser,
) -> None:
    """#71: CI installed ``.[dev]`` while tox installed ``.[test]``."""
    ci_extras = _extras(
        ",".join(re.findall(r"\.\[([^\]]+)\]", "\n".join(_ci_run_steps(_ci_test_job()))))
    )
    for env in _tox_pytest_envs(tox_config):
        value = _tox_setting(tox_config, env, "extras")
        if value is None:  # inherits [testenv], already checked
            continue
        assert ci_extras == _extras(value), (
            f"[{env}] installs {sorted(_extras(value))}; CI's test job "
            f"installs {sorted(ci_extras)}. They must match exactly - a "
            f"superset on either side means the two run against different "
            f"dependency sets while both report green (issue #71)"
        )


def test_ci_and_tox_install_in_the_same_mode(
    tox_config: configparser.ConfigParser,
) -> None:
    """#71's worst variant: tox's ``sdist`` default ran a smaller suite.

    At least one test keys off whether it is running from a source checkout
    (``tests/unit/test_version_single_source.py`` resolves the repo root
    from ``mfgparams.__file__``), so a non-editable install silently skips
    it. Both sides must install editable.
    """
    for env in _tox_pytest_envs(tox_config):
        package = _tox_setting(tox_config, env, "package")
        if package is None:
            continue
        assert package == "editable", (
            f"[{env}] sets `package = {package}`; tox 4's `sdist` default "
            "silently runs a smaller suite than CI (issue #71)"
        )
    installs = "\n".join(_ci_run_steps(_ci_test_job()))
    assert "pip install -e " in installs, (
        "CI's test job must install editable (`pip install -e`), matching "
        "tox's `package = editable`"
    )


def test_ci_and_tox_pass_the_same_pytest_arguments(
    tox_config: configparser.ConfigParser,
) -> None:
    """Any argument on one side only must be declared above, with a reason."""
    ci_args = _without(_pytest_arguments(_ci_pytest_command(_ci_test_job())), CI_ONLY_PYTEST_ARGS)
    for env in _tox_pytest_envs(tox_config):
        commands = _tox_setting(tox_config, env, "commands")
        if commands is None:
            continue
        tox_args = _without(_pytest_arguments(commands), TOX_ONLY_PYTEST_ARGS)
        assert ci_args == tox_args, (
            f"CI's test job runs pytest with {ci_args} and [{env}] with "
            f"{tox_args}. Make them match, or declare the difference in "
            f"CI_ONLY_PYTEST_ARGS / TOX_ONLY_PYTEST_ARGS in this file with "
            f"the reason."
        )


def test_coverage_threshold_is_not_restated_on_either_command_line(
    tox_config: configparser.ConfigParser,
) -> None:
    """#71: ``--cov-fail-under`` on the command line *overrides* ``addopts``.

    Unlike ``--cov-report``, it does not accumulate - so restating it on
    either command line means bumping the threshold in ``pyproject.toml``
    changes it for one runner and not the other. It belongs only in
    ``[tool.pytest.ini_options].addopts``, the single source both inherit.
    """
    commands = [
        (f"[{env}]", _tox_setting(tox_config, env, "commands"))
        for env in _tox_pytest_envs(tox_config)
    ]
    commands.append(("CI's test job", _ci_pytest_command(_ci_test_job())))

    for label, command in commands:
        if command is None:
            continue
        assert "--cov-fail-under" not in command, (
            f"{label} restates --cov-fail-under; it silently overrides "
            "addopts rather than accumulating, so the two runners would "
            "enforce different thresholds (issue #71)"
        )
