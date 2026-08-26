"""Static check: no stray references to the package's old name remain
(specs/012-rename-package-mfgparams; FR-008, SC-001).

Walks every git-tracked file — both its content and its own tracked path —
and asserts none contain ``machine_calc`` or ``machine-calc``
(case-insensitively, so this also catches the old ``MACHINE_CALC_*``
environment-variable prefix), except for two kinds of exclusion. Checking
the path itself (not just file contents) means a forbidden compatibility
shim such as a re-added ``src/machine_calc/__init__.py`` re-exporting
``mfgparams`` would still be caught, even though its content alone would
contain no stray reference to scan for.

1. Historical record: prior feature specs (``specs/001-*`` through
   ``specs/011-*``), this feature's own planning docs
   (``specs/012-rename-package-mfgparams/**`` — written before the GitHub
   repository itself was renamed from ``kniklas/machine-calc`` to
   ``kniklas/mfgparams`` (issue #69), so they still describe that rename as
   future/out-of-scope work), ``CHANGELOG.md`` (both its pre-existing
   entries and the new entry documenting the package rename), and
   ``tests/contract/data/README.md``'s fixture-provenance note.
2. The constitution (``.specify/memory/constitution.md``), which has its
   own amendment procedure (documented rationale + version bump) and is
   updated via ``/speckit-constitution``, not as a side effect of this
   feature's tasks (specs/012-rename-package-mfgparams/tasks.md T024).
3. This test file itself, which necessarily names the old value to define
   the check.

The GitHub repository has since been renamed to ``kniklas/mfgparams``, so
unlike when this check was first written, a ``kniklas/machine-calc`` URL in
a live (non-excluded) file — e.g. a stale README badge — is no longer
excused; it is a stray reference like any other and fails the check.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OLD_NAME_PATTERN = re.compile(r"machine[_-]calc", re.IGNORECASE)

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
        if _OLD_NAME_PATTERN.search(line):
            findings.append(f"{relative_path}:{lineno}: {line.strip()}")
    return findings


def test_no_stray_references_to_old_package_name():
    stray = []
    for relative_path in _tracked_files():
        if _is_excluded(relative_path):
            continue
        if _OLD_NAME_PATTERN.search(relative_path):
            stray.append(f"{relative_path}: old name in the tracked path itself")
        stray.extend(_stray_matches(relative_path))

    assert not stray, (
        "found stray reference(s) to the old package name outside the "
        "exclusions documented in this file's module docstring:\n" + "\n".join(stray)
    )
