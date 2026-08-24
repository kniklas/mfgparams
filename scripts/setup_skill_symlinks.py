#!/usr/bin/env python3
"""Symlink genuinely shared, hand-authored skills from `.github/skills/`
(GitHub Copilot's skill directory) into `.claude/skills/` (Claude Code's),
per Constitution Principle XI's "genuinely shared, hand-authored skills"
exception (v1.9.0): each skill stays a single canonical directory under
`.github/skills/<name>/` (containing `SKILL.md` and any supporting files),
referenced elsewhere only via a symlink to that directory, never a
hand-copied duplicate.

Safe to re-run: an already-correct symlink is left untouched, a symlink
pointing at the wrong target is corrected, a plain-text placeholder file
left by a Windows checkout without symlink support is replaced with a
real symlink, and a real file/directory already at the destination that
isn't one of those is never overwritten (reported as a conflict instead,
since it may be a contributor's unrelated content).

Usage: python scripts/setup_skill_symlinks.py [--check]

    --check: report what would change (or is already correct) without
        writing anything; exits non-zero if any skill is missing/wrong,
        for use as a manual verification step.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / ".github" / "skills"
DEST_DIR = REPO_ROOT / ".claude" / "skills"

# Skills deliberately excluded from the symlink even though they have a
# `.github/skills/<name>/SKILL.md`. `code-review` collides with Claude
# Code's own bundled `/code-review` skill (correctness/bug-hunting review,
# `--fix`/`--comment`/`ultra`); Claude Code resolves same-name conflicts by
# giving a project skill precedence over a bundled one, so symlinking it
# would silently shadow the bundled skill instead of adding to it. Add a
# name here (with a comment explaining why) if a future `.github/skills/`
# entry turns out to collide with another Claude Code bundled skill.
EXCLUDED = {"code-review"}


def discover_source_skills() -> list[str]:
    if not SOURCE_DIR.is_dir():
        return []
    return sorted(
        p.name
        for p in SOURCE_DIR.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file() and p.name not in EXCLUDED
    )


def _relative_target(name: str) -> str:
    # Relative to DEST_DIR, so the symlink still resolves if the repo is
    # moved/cloned elsewhere rather than baking in an absolute path.
    return os.path.relpath(SOURCE_DIR / name, DEST_DIR)


# A leading `/`, `\\` (including a UNC `\\\\server\\share`), or `C:\\`-style
# drive prefix - i.e. the shapes that make a symlink target absolute.
_ABSOLUTE_PREFIX = re.compile(r"^([/\\]|[A-Za-z]:[/\\])")

# Stands in for the leading separator of an absolute target in the
# normalized component tuple. It can never collide with a real component,
# because the split below is on exactly this character class.
_ROOT = "/"


def _normalize_target(target: str) -> tuple[str, ...]:
    """Split a symlink-target-like path into normalized components.

    `os.path.relpath()` returns backslash-separated paths on Windows, while
    a symlink target stored in a git blob (and returned by `os.readlink()`
    on POSIX, and by a Windows checkout that *did* materialize a real
    symlink) uses forward slashes - a raw string comparison between the two
    would report a perfectly valid Windows checkout as wrong. Also strips
    surrounding whitespace/newlines, so a plain-text placeholder file's
    trailing newline doesn't cause a false mismatch either.

    Absoluteness is kept as a leading `_ROOT` component: the empty string a
    leading separator splits off is dropped along with the other empties,
    so without it an absolute target that happens to share the expected
    target's components (`/../../.github/skills/<name>` against
    `../../.github/skills/<name>`) would compare *equal* and be reported as
    already linked - even though it resolves somewhere else entirely, and
    the expected target this is compared against is always relative
    (`_relative_target()`).
    """
    stripped = target.strip()
    parts = tuple(part for part in re.split(r"[\\/]+", stripped) if part not in ("", "."))
    if _ABSOLUTE_PREFIX.match(stripped):
        return (_ROOT,) + parts
    return parts


def _windows_symlink_hint(error: OSError) -> str:
    # core.symlinks is a *git checkout-time* setting - it controls whether
    # `git checkout`/`git clone` materializes a committed symlink for you
    # (see _matches_placeholder()'s recovery case) and has no bearing on
    # whether this script's own os.symlink() call succeeds right now, so it
    # is deliberately not presented as a requirement alongside Developer
    # Mode/elevation below - a contributor who already has one of those
    # enabled needs neither a config change nor a reclone to get past this.
    static_hint = (
        "On Windows, creating a symlink requires either Developer Mode "
        "(Settings > Update & Security > For developers > Developer Mode) "
        "or running this script from an elevated (Administrator) "
        "terminal."
    )
    return f"    Could not create the symlink ({error}). {static_hint}"


def _discard_stash(stash: Path) -> None:
    """Remove a stash directory created by `_stash_and_symlink()` along with
    the single entry moved into it (always a symlink or a plain file, never
    a real directory - `sync_one()` reports those as conflicts and never
    gets here). Errors are swallowed: failing to tidy up scratch state must
    not turn an otherwise successful run into a failure, and `unlink()`
    refusing a real directory leaves the stash in place rather than
    destroying anything.
    """

    with contextlib.suppress(OSError):
        for entry in stash.iterdir():
            entry.unlink()
        stash.rmdir()


def _stash_and_symlink(dest: Path, target: str) -> OSError | None:
    """Replace an existing `dest` with a symlink to `target`, moving the old
    entry into an exclusively-created stash directory first and restoring it
    if symlink creation fails.

    The old entry is moved *out of the way* and the new symlink is then
    created at `dest` directly, rather than building the link at a scratch
    path and swapping it over `dest`. On Windows the swap direction is not
    available to us: `os.replace()` goes through `MoveFileExW`, which
    cannot replace an existing entry when either side names a directory -
    and a symlink created with `target_is_directory=True` *is* a directory
    entry, while the checkout placeholder it must replace is a regular
    file. Swapping would therefore fail on exactly the Windows recovery
    path this script exists for, even when `os.symlink()` itself succeeded.

    `tempfile.mkdtemp()` is what makes the stash safe: it creates the
    directory exclusively, so - unlike a predictable `<name>.tmp` scratch
    name - it can never collide with, and never removes, an unrelated
    contributor file that happens to sit at that path.
    """

    try:
        stash = Path(tempfile.mkdtemp(dir=str(dest.parent), prefix=f".{dest.name}.stash-"))
    except OSError as exc:
        return exc

    stashed = stash / dest.name
    try:
        os.replace(dest, stashed)
    except OSError as exc:
        _discard_stash(stash)
        return exc

    try:
        os.symlink(target, dest, target_is_directory=True)
    except OSError as exc:
        try:
            os.replace(stashed, dest)
        except OSError as restore_exc:
            return OSError(
                f"{exc}; the original entry could not be put back either and "
                f"has been left at {stashed} ({restore_exc})"
            )
        _discard_stash(stash)
        return exc

    _discard_stash(stash)
    return None


def _create_symlink_safely(dest: Path, target: str) -> OSError | None:
    """Create a symlink at `dest` pointing to `target` without destroying
    whatever (if anything) is currently at `dest` unless creation actually
    succeeds.

    Returns `None` on success, or the `OSError` on failure - in the failure
    case `dest` is left as it was before the call (a caller replacing an
    existing, wrong-target symlink or a Windows placeholder file never ends
    up with neither the old nor the new one), and no scratch state is left
    behind. See `_stash_and_symlink()` for how the replacement is sequenced
    and why.

    `target_is_directory=True` is always correct here since every symlink
    this script creates points at a skill *directory*
    (`.github/skills/<name>/`, holding `SKILL.md` plus any supporting
    files); on Windows, omitting it would create a *file*-type reparse
    point pointing at a directory, which some directory-aware tools/APIs
    (Explorer, `dir`) don't resolve correctly. Ignored on POSIX.
    """

    if dest.is_symlink() or dest.exists():
        return _stash_and_symlink(dest, target)

    try:
        os.symlink(target, dest, target_is_directory=True)
    except OSError as exc:
        return exc
    return None


def _matches_placeholder(dest: Path, expected_target: str) -> bool:
    """True if `dest` is a plain-text file whose content is exactly the
    expected symlink target - the shape `git checkout` produces for a
    symlink blob when `core.symlinks` is `false` (the common Windows
    default without Developer Mode / an elevated clone), rather than
    materializing a real symlink.
    """

    if not dest.is_file():
        return False
    try:
        content = dest.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    return _normalize_target(content) == _normalize_target(expected_target)


def _sync_existing_symlink(
    dest: Path, name: str, expected_target: str, *, check_only: bool
) -> tuple[bool, str]:
    """Handle `sync_one()` when `dest` already is a symlink (correct, wrong
    target, or pointing at a since-removed skill). Extracted to keep
    `sync_one()` within the configured cyclomatic-complexity threshold.
    """

    actual_target = os.readlink(dest)
    if (
        _normalize_target(actual_target) == _normalize_target(expected_target)
        and (SOURCE_DIR / name / "SKILL.md").is_file()
    ):
        return True, f"ok      {name} (already linked)"
    if check_only:
        return False, f"WRONG   {name} (points to {actual_target!r}, expected {expected_target!r})"
    error = _create_symlink_safely(dest, expected_target)
    if error is not None:
        return False, f"FAILED  {name}\n{_windows_symlink_hint(error)}"
    return True, f"fixed   {name} (was pointing to {actual_target!r})"


def _sync_existing_non_symlink(
    dest: Path, name: str, expected_target: str, *, check_only: bool
) -> tuple[bool, str]:
    """Handle `sync_one()` when `dest` exists but is not a symlink: either a
    Windows plain-text placeholder (recoverable) or a real file/directory
    (never clobbered). Extracted for the same reason as the sibling
    `_sync_existing_symlink()` above.
    """

    if not _matches_placeholder(dest, expected_target):
        # A real file/directory, not a symlink and not a placeholder: never
        # clobber it, it may be a contributor's own unrelated content.
        return False, (
            f"CONFLICT {name} (a real file/directory already exists at {dest}, not touching it)"
        )

    # git materialized the symlink blob as a plain-text file instead of a
    # real symlink (core.symlinks=false at checkout, notably on Windows
    # without Developer Mode) - this is exactly the recoverable case this
    # script exists for, not a conflict.
    if check_only:
        return False, (
            f"PLACEHOLDER {name} (checked out as a plain-text file, not a real "
            "symlink - would replace)"
        )
    # Deliberately not unlinking the placeholder first: _create_symlink_safely()
    # moves it aside and puts it back if symlink creation fails (the exact
    # Windows privilege condition this recovery path exists for), so the
    # placeholder file - not nothing - is still there afterward.
    error = _create_symlink_safely(dest, expected_target)
    if error is not None:
        return False, f"FAILED  {name}\n{_windows_symlink_hint(error)}"
    return True, f"fixed   {name} (was a plain-text placeholder, not a real symlink)"


def sync_one(name: str, *, check_only: bool) -> tuple[bool, str]:
    """Return (is_ok, message). is_ok is True if the destination already
    is, or was just made, a correct symlink to the source skill.
    """

    dest = DEST_DIR / name
    expected_target = _relative_target(name)

    if dest.is_symlink():
        return _sync_existing_symlink(dest, name, expected_target, check_only=check_only)

    if dest.exists():
        return _sync_existing_non_symlink(dest, name, expected_target, check_only=check_only)

    if check_only:
        return False, f"MISSING {name} (would create -> {expected_target})"

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    error = _create_symlink_safely(dest, expected_target)
    if error is not None:
        return False, f"FAILED  {name}\n{_windows_symlink_hint(error)}"
    return True, f"created {name} -> {expected_target}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report status without writing anything; exit non-zero if anything is missing/wrong",
    )
    args = parser.parse_args(argv)

    names = discover_source_skills()
    if not names:
        print(f"No skills found under {SOURCE_DIR} - nothing to do.")
        return 0

    all_ok = True
    for name in names:
        ok, message = sync_one(name, check_only=args.check)
        print(message)
        all_ok = all_ok and ok

    if EXCLUDED:
        print(f"skipped {', '.join(sorted(EXCLUDED))} (see EXCLUDED in this script for why)")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
