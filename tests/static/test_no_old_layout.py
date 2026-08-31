"""Static check: the operation-first layout cannot be reintroduced (FR-017).

Walks every git-tracked file -- both its content and its own tracked path --
and asserts none names ``mfgparams.operations`` or ``mfgparams/operations``.

Modelled directly on ``tests/static/test_no_old_package_name.py``, which
already solved the subtle part: scanning tracked *paths* as well as contents is
what catches a re-added compatibility shim. A file such as
``src/mfgparams/operations/__init__.py`` re-exporting ``mfgparams.processes``
would contain no forbidden string to scan for, yet is exactly the FR-004
violation a well-meaning contributor is most likely to add -- "just a small
alias so old imports keep working". Nothing has ever been published under the
old paths, so there is no such user to help.

Deliberately a *separate* file rather than a second rule inside
``test_no_old_package_name.py``: that check answers a different question (the
old distribution name), its exclusion list is tuned to that question, and its
docstring is a careful historical record. Overloading it would make both harder
to reason about (research.md #5).

Exclusions, matching the three categories that check established:

1. Historical record: prior feature specs (``specs/001-*`` through
   ``specs/013-*``) and this feature's own planning documents
   (``specs/014-process-namespaces-extras/**``), which necessarily name the old
   paths to describe the migration away from them; and ``CHANGELOG.md``, which
   documents the restructure as a breaking change. The *directory* is excluded,
   not the string, so live files stay covered.
2. The constitution (``.specify/memory/constitution.md``), which has its own
   amendment procedure and is updated via ``/speckit-constitution``, not as a
   side effect of this feature's tasks.
3. The three tests that must *name* the old paths in order to assert their
   absence -- this file, ``test_library_api_milling.py``'s FR-004 check that
   each old module raises ``ModuleNotFoundError``, and
   ``test_packaging_bundled_data.py``'s assertion that no ``.toml`` ships under
   the old layout. Excluding them is not a loophole: each one *fails* if the
   old layout comes back, so they enforce the same rule this file does, by
   different means. Any other test naming the old paths is a stray reference
   like any other.

Note the deliberately narrow pattern. It matches only the *package-qualified*
forms, so unrelated English uses of the word "operations" -- and the
``operations`` domain vocabulary that legitimately survives the restructure,
since drilling and milling are still operations -- do not trip it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: ``mfgparams.operations`` (import form) or ``mfgparams/operations`` (path form).
_OLD_LAYOUT_PATTERN = re.compile(r"mfgparams[./]operations")

_EXCLUDED_FILES = {
    "CHANGELOG.md",
    ".specify/memory/constitution.md",
    # The checks that name the old layout to prove it is gone; see the module
    # docstring's exclusion 3. Each fails if the old layout returns.
    "tests/static/test_no_old_layout.py",
    "tests/contract/test_library_api_milling.py",
    "tests/integration/test_packaging_bundled_data.py",
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
    "specs/012-",
    "specs/013-",
    "specs/014-process-namespaces-extras/",
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

    return [
        f"{relative_path}:{lineno}: {line.strip()}"
        for lineno, line in enumerate(text.splitlines(), start=1)
        if _OLD_LAYOUT_PATTERN.search(line)
    ]


def test_no_stray_references_to_the_operation_first_layout():
    stray = []
    for relative_path in _tracked_files():
        if _is_excluded(relative_path):
            continue
        if _OLD_LAYOUT_PATTERN.search(relative_path):
            stray.append(f"{relative_path}: old layout in the tracked path itself")
        stray.extend(_stray_matches(relative_path))

    assert not stray, (
        "found reference(s) to the operation-first layout outside the exclusions "
        "documented in this file's module docstring. There is exactly one path to "
        "each calculation and no alias period (FR-004, FR-017):\n" + "\n".join(stray)
    )


def test_the_pattern_still_matches_what_it_claims_to():
    """A guard on the guard: a typo'd pattern would make the check above pass
    unconditionally, and nothing else would notice."""

    for forbidden in (
        "from mfgparams.operations.drilling import calculate",
        "src/mfgparams/operations/milling/__init__.py",
        "mfgparams.operations",
    ):
        assert _OLD_LAYOUT_PATTERN.search(forbidden), forbidden

    for allowed in (
        "from mfgparams.processes.machining.drilling import calculate",
        "the two milling sub-operations",
        "tests/unit/processes/machining/",
    ):
        assert not _OLD_LAYOUT_PATTERN.search(allowed), allowed
