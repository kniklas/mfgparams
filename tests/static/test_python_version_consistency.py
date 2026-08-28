"""Static check: the declared supported Python version range stays in sync
across packaging metadata, the local multi-version workflow, and CI
(specs/013-tox-multi-python-testing FR-008; data-model.md's Supported
Version Range validation rule).

``pyproject.toml``'s ``classifiers``, ``tox.ini``'s ``envlist``, and
``.github/workflows/ci.yml``'s ``test`` job matrix are three independent,
hand-maintained places that must all list the identical Python version set.
Without this check, bumping the supported range in one of them (e.g. adding
3.13 to ``classifiers``) and forgetting the other two would silently
reintroduce the exact "claimed support isn't actually verified" gap
specs/013-tox-multi-python-testing exists to close — this test turns that
into an immediate, obvious test failure instead of a silent drift.
"""

from __future__ import annotations

import re
from configparser import ConfigParser
from pathlib import Path

import yaml

try:  # Python 3.11+ ships tomllib in the standard library.
    import tomllib
except ModuleNotFoundError:  # Python 3.9 / 3.10 fall back to the tomli backport.
    import tomli as tomllib  # type: ignore[no-redef]  # tomli is a drop-in tomllib backport; mypy sees this as an invalid redefinition, but it's the intended fallback for Python <3.11

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLASSIFIER_PATTERN = re.compile(r"Programming Language :: Python :: (3\.\d+)")


def _classifier_versions() -> set[str]:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = data["project"]["classifiers"]
    versions = {match.group(1) for c in classifiers if (match := _CLASSIFIER_PATTERN.match(c))}
    assert versions, "expected at least one 'Programming Language :: Python :: 3.X' classifier"
    return versions


def _requires_python_floor() -> str:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requires_python = data["project"]["requires-python"]
    match = re.fullmatch(r">=(3\.\d+)", requires_python)
    assert match, f"expected a simple '>=3.X' requires-python, got {requires_python!r}"
    return match.group(1)


def _tox_envlist_versions() -> set[str]:
    # Read with configparser rather than a regex: tox's equally idiomatic
    # multi-line `envlist` form (one env per continuation line) would leave a
    # single-line regex capturing only the first entry, failing this check on a
    # purely cosmetic reformat with a misleading "envlist does not match
    # classifiers" message (code review finding,
    # specs/013-tox-multi-python-testing).
    parser = ConfigParser()
    parser.read(_REPO_ROOT / "tox.ini", encoding="utf-8")
    assert parser.has_option("tox", "envlist"), "expected an 'envlist' option under [tox]"
    versions = set()
    for env in re.split(r"[,\s]+", parser.get("tox", "envlist").strip()):
        # Non-interpreter envs (a `lint` or `docs` env, say) are legitimately
        # part of an envlist and are simply not version claims — skip them
        # rather than hard-failing the suite on their presence.
        env_match = re.fullmatch(r"py3(\d+)", env)
        if env_match:
            versions.add(f"3.{env_match.group(1)}")
    assert versions, "expected at least one 'py3<minor>' env in tox.ini's envlist"
    return versions


def _ci_workflow() -> dict:
    # Parsed as YAML rather than scanned with a regex: a regex for
    # `python-version: [...]` matches the FIRST such list anywhere in the
    # file, so adding any other matrixed job above `test` would silently
    # point this guard at the wrong matrix and let the `test` matrix drift
    # unchecked — exactly the failure FR-008 exists to prevent (code review
    # finding, specs/013-tox-multi-python-testing).
    text = (_REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    assert isinstance(workflow, dict), "expected ci.yml to parse as a YAML mapping"
    return workflow


def _ci_matrix_versions() -> set[str]:
    jobs = _ci_workflow()["jobs"]
    assert "test" in jobs, "expected a 'test' job in ci.yml"
    matrix = jobs["test"]["strategy"]["matrix"]
    versions = matrix["python-version"]
    assert isinstance(versions, list) and versions, (
        "expected ci.yml's `test` job to declare a non-empty "
        "`strategy.matrix.python-version` list"
    )
    # YAML resolves an unquoted `3.10` to the float 3.1, which would silently
    # compare unequal to the "3.10" classifier; require the quoted string form.
    for version in versions:
        assert isinstance(version, str), (
            f"expected ci.yml's `test` matrix versions to be quoted strings, got "
            f"{version!r} — an unquoted YAML version number is parsed as a float"
        )
    return set(versions)


def _ci_canonical_version() -> str:
    canonical = _ci_workflow()["env"]["PYTHON_VERSION"]
    assert isinstance(
        canonical, str
    ), f"expected ci.yml's `env.PYTHON_VERSION` to be a quoted string, got {canonical!r}"
    return canonical


def test_supported_python_versions_are_consistent_everywhere():
    classifiers = _classifier_versions()
    tox_envlist = _tox_envlist_versions()
    ci_matrix = _ci_matrix_versions()

    assert tox_envlist == classifiers, (
        f"tox.ini envlist {sorted(tox_envlist)} does not match pyproject.toml "
        f"classifiers {sorted(classifiers)}"
    )
    assert ci_matrix == classifiers, (
        f"ci.yml test job matrix {sorted(ci_matrix)} does not match pyproject.toml "
        f"classifiers {sorted(classifiers)}"
    )


def test_requires_python_floor_matches_the_oldest_classifier():
    floor = _requires_python_floor()
    oldest_classifier = min(_classifier_versions(), key=lambda v: tuple(map(int, v.split("."))))
    assert floor == oldest_classifier, (
        f"requires-python floor {floor!r} does not match the oldest declared "
        f"classifier {oldest_classifier!r}"
    )


def test_ci_canonical_version_is_a_supported_version():
    # ci.yml's env.PYTHON_VERSION is the canonical leg several `if:` conditions
    # (e.g. the test job's Codecov upload) compare `matrix.python-version`
    # against, so it must always be one of the actually-supported versions —
    # otherwise those conditions silently become permanently false the moment
    # this version is dropped from the supported range (code review finding,
    # specs/013-tox-multi-python-testing).
    canonical = _ci_canonical_version()
    classifiers = _classifier_versions()
    assert canonical in classifiers, (
        f"ci.yml's env.PYTHON_VERSION {canonical!r} is not one of the supported "
        f"versions {sorted(classifiers)}"
    )
