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
from pathlib import Path

try:  # Python 3.11+ ships tomllib in the standard library.
    import tomllib
except ModuleNotFoundError:  # Python 3.9 / 3.10 fall back to the tomli backport.
    import tomli as tomllib  # type: ignore[no-redef]  # tomli is a drop-in tomllib backport; mypy sees this as an invalid redefinition, but it's the intended fallback for Python <3.11

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLASSIFIER_PATTERN = re.compile(r"Programming Language :: Python :: (3\.\d+)")


def _classifier_versions() -> set[str]:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = data["project"]["classifiers"]
    versions = {
        match.group(1) for c in classifiers if (match := _CLASSIFIER_PATTERN.match(c))
    }
    assert versions, "expected at least one 'Programming Language :: Python :: 3.X' classifier"
    return versions


def _requires_python_floor() -> str:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requires_python = data["project"]["requires-python"]
    match = re.fullmatch(r">=(3\.\d+)", requires_python)
    assert match, f"expected a simple '>=3.X' requires-python, got {requires_python!r}"
    return match.group(1)


def _tox_envlist_versions() -> set[str]:
    text = (_REPO_ROOT / "tox.ini").read_text(encoding="utf-8")
    match = re.search(r"^envlist\s*=\s*(.+)$", text, re.MULTILINE)
    assert match, "expected an 'envlist = ...' line in tox.ini"
    versions = set()
    for env in match.group(1).split(","):
        env = env.strip()
        env_match = re.fullmatch(r"py3(\d+)", env)
        assert env_match, f"unexpected tox env name {env!r}, expected 'py3<minor>'"
        versions.add(f"3.{env_match.group(1)}")
    return versions


def _ci_matrix_versions() -> set[str]:
    text = (_REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    match = re.search(r"python-version:\s*\[(.*?)\]", text)
    assert match, "expected a literal 'python-version: [...]' matrix list in ci.yml"
    return {v.strip().strip("\"'") for v in match.group(1).split(",")}


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
