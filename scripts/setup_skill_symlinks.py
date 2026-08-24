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
import uuid
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


def _normalize_target(target: str) -> tuple[str, ...]:
    """Split a symlink-target-like path into normalized components.

    `os.path.relpath()` returns backslash-separated paths on Windows, while
    a symlink target stored in a git blob (and returned by `os.readlink()`
    on POSIX, and by a Windows checkout that *did* materialize a real
    symlink) uses forward slashes - a raw string comparison between the two
    would report a perfectly valid Windows checkout as wrong. Also strips
    surrounding whitespace/newlines, so a plain-text placeholder file's
    trailing newline doesn't cause a false mismatch either.
    """
    return tuple(part for part in re.split(r"[\\/]+", target.strip()) if part not in ("", "."))


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


def _create_symlink_safely(dest: Path, target: str) -> OSError | None:
    """Create a symlink at `dest` pointing to `target` without destroying
    whatever (if anything) is currently at `dest` unless creation actually
    succeeds: the new symlink is created at a temporary path first, then
    atomically swapped into place with `os.replace()`, which renames the
    directory entry itself (not its referent) on both POSIX and Windows.

    Returns `None` on success, or the `OSError` on failure - in the
    failure case `dest` is left exactly as it was before the call (a
    caller replacing an existing, wrong-target symlink or a Windows
    placeholder file never ends up with neither the old nor the new one),
    and the temporary link is cleaned up so a failed run doesn't leave a
    stray `<name>.tmp-symlink-<suffix>` entry behind.

    The temporary path carries a random suffix and is only ever removed
    again if *this* call is what created it: a fixed scratch name could
    collide with an unrelated contributor file (or directory) sitting at
    that path, and removing it would make a tool documented as
    non-clobbering destroy exactly the kind of content it promises not to
    touch. On the (practically impossible) collision, `os.symlink()`
    raises `FileExistsError` and the call reports failure instead.

    `target_is_directory=True` is always correct here since every symlink
    this script creates points at a skill *directory*
    (`.github/skills/<name>/`, holding `SKILL.md` plus any supporting
    files); on Windows, omitting it would create a *file*-type reparse
    point pointing at a directory, which some directory-aware tools/APIs
    (Explorer, `dir`) don't resolve correctly. Ignored on POSIX.
    """

    tmp_dest = dest.with_name(f"{dest.name}.tmp-symlink-{uuid.uuid4().hex[:8]}")
    created = False
    try:
        os.symlink(target, tmp_dest, target_is_directory=True)
        created = True
        os.replace(tmp_dest, dest)
    except OSError as exc:
        if created:
            # Cleanup must not mask the failure that actually matters, and
            # only ever removes the link created just above.
            with contextlib.suppress(OSError):
                tmp_dest.unlink()
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
    # replaces `dest` atomically via os.replace() only once the new symlink
    # has actually been created, so if creation fails (the exact Windows
    # privilege condition this recovery path exists for), the placeholder
    # file - not nothing - is still there afterward.
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
