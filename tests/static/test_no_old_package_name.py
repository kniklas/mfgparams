"""Static check: no stray references to the package's old name remain
(specs/012-rename-package-mfgparams; FR-008, SC-001).

Walks every git-tracked file and asserts none contain ``machine_calc`` or
``machine-calc`` (case-insensitively, so this also catches the old
``MACHINE_CALC_*`` environment-variable prefix), except for the documented
exclusions in specs/012-rename-package-mfgparams/data-model.md's Exclusion
rule:

1. Lines that are, or contain, a URL pointing at the (unrenamed) GitHub
   repository slug ``kniklas/machine-calc`` — badges, issue links, the
   ``LICENSE.md`` notice — or its GitHub Pages URL shape,
   ``kniklas.github.io/machine-calc``.
2. Historical record: prior feature specs (``specs/001-*`` through
   ``specs/011-*``), this feature's own planning docs
   (``specs/012-rename-package-mfgparams/**``), ``CHANGELOG.md`` (both its
   pre-existing entries and the new entry documenting this rename), and
   ``tests/contract/data/README.md``'s fixture-provenance note.
3. The constitution (``.specify/memory/constitution.md``), which has its
   own amendment procedure (documented rationale + version bump) and is
   updated via ``/speckit-constitution``, not as a side effect of this
   feature's tasks (specs/012-rename-package-mfgparams/tasks.md T024).
4. This test file itself, which necessarily names the old value to define
   the check.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OLD_NAME_PATTERN = re.compile(r"machine[_-]calc", re.IGNORECASE)
_REPO_URL_SUBSTRINGS = ("kniklas/machine-calc", "kniklas.github.io/machine-calc")

_EXCLUDED_FILES = {
    "CHANGELOG.md",
    "tests/contract/data/README.md",
    "tests/static/test_no_old_package_name.py",
    ".specify/memory/constitution.md",
}

_EXCLUDED_PREFIXES = (
    "specs/001-",
    "specs/002-",
    "specs/003-",
    "specs/004-",
    "specs/005-",
    "specs/006-",
    "specs/007-",
    "specs/008-",
    "specs/009-",
    "specs/010-",
    "specs/011-",
    "specs/012-rename-package-mfgparams/",
)


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _is_excluded(relative_path: str) -> bool:
    if relative_path in _EXCLUDED_FILES:
        return True
    return any(relative_path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def _stray_matches(relative_path: str) -> list[str]:
    path = _REPO_ROOT / relative_path
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        return []

    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        checked_line = line
        for substring in _REPO_URL_SUBSTRINGS:
            checked_line = checked_line.replace(substring, "")
        if _OLD_NAME_PATTERN.search(checked_line):
            findings.append(f"{relative_path}:{lineno}: {line.strip()}")
    return findings


def test_no_stray_references_to_old_package_name():
    stray = []
    for relative_path in _tracked_files():
        if _is_excluded(relative_path):
            continue
        stray.extend(_stray_matches(relative_path))

    assert not stray, (
        "found stray reference(s) to the old package name outside the "
        "documented exclusions (specs/012-rename-package-mfgparams/"
        "data-model.md's Exclusion rule):\n" + "\n".join(stray)
    )
