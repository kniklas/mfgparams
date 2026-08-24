"""Unit tests for scripts/setup_skill_symlinks.py (Constitution Principle XI
v1.9.0's "genuinely shared, hand-authored skills" exception).

`scripts/` is not part of the installed `machine_calc` package (it is
CI-only tooling, mirroring scripts/sync_agent_integrations.py's test
setup), so the module under test is imported directly by path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import setup_skill_symlinks as sss  # noqa: E402


@pytest.fixture()
def dirs(tmp_path, monkeypatch):
    source = tmp_path / ".github" / "skills"
    dest = tmp_path / ".claude" / "skills"
    source.mkdir(parents=True)
    dest.mkdir(parents=True)
    monkeypatch.setattr(sss, "SOURCE_DIR", source)
    monkeypatch.setattr(sss, "DEST_DIR", dest)
    return source, dest


def _make_skill(source: Path, name: str) -> None:
    skill_dir = source / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\n")


def _scratch_entries(dest: Path) -> list[str]:
    """Names of leftover scratch entries created by _create_symlink_safely()."""
    return sorted(p.name for p in dest.iterdir() if ".tmp-symlink" in p.name)


# --- discover_source_skills ---------------------------------------------------


def test_discover_source_skills_finds_dirs_with_skill_md(dirs):
    source, _ = dirs
    _make_skill(source, "pr-review-loop")
    _make_skill(source, "skill-authoring")
    (source / "not-a-skill").mkdir()  # no SKILL.md - must be ignored

    assert sss.discover_source_skills() == ["pr-review-loop", "skill-authoring"]


def test_discover_source_skills_excludes_code_review(dirs):
    source, _ = dirs
    _make_skill(source, "code-review")
    _make_skill(source, "pr-review-loop")

    assert sss.discover_source_skills() == ["pr-review-loop"]


def test_discover_source_skills_missing_source_dir_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(sss, "SOURCE_DIR", tmp_path / "does-not-exist")
    monkeypatch.setattr(sss, "DEST_DIR", tmp_path / ".claude" / "skills")

    assert sss.discover_source_skills() == []


# --- sync_one ------------------------------------------------------------------


def test_sync_one_creates_missing_symlink(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert "created" in message
    link = dest / "pr-review-loop"
    assert link.is_symlink()
    assert (link / "SKILL.md").read_text() == "---\nname: pr-review-loop\n---\n"


def test_sync_one_check_only_reports_missing_without_writing(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")

    ok, message = sss.sync_one("pr-review-loop", check_only=True)

    assert ok is False
    assert "MISSING" in message
    assert not (dest / "pr-review-loop").exists()


def test_sync_one_already_correct_is_ok_and_untouched(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    sss.sync_one("pr-review-loop", check_only=False)

    ok, message = sss.sync_one("pr-review-loop", check_only=True)

    assert ok is True
    assert "already linked" in message


def test_sync_one_fixes_wrong_target(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    _make_skill(source, "skill-authoring")
    # Point the pr-review-loop destination at the wrong source skill.
    (dest / "pr-review-loop").symlink_to(source / "skill-authoring")

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert "fixed" in message
    assert (dest / "pr-review-loop").resolve() == (source / "pr-review-loop").resolve()


def test_sync_one_check_only_reports_wrong_without_fixing(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    _make_skill(source, "skill-authoring")
    (dest / "pr-review-loop").symlink_to(source / "skill-authoring")

    ok, message = sss.sync_one("pr-review-loop", check_only=True)

    assert ok is False
    assert "WRONG" in message
    assert (dest / "pr-review-loop").resolve() == (source / "skill-authoring").resolve()


def test_sync_one_never_clobbers_a_real_directory(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    real_dir = dest / "pr-review-loop"
    real_dir.mkdir()
    (real_dir / "unrelated.txt").write_text("contributor's own content")

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is False
    assert "CONFLICT" in message
    assert not real_dir.is_symlink()
    assert (real_dir / "unrelated.txt").exists()


def test_sync_one_backslash_target_still_reads_as_ok(dirs):
    """A Windows checkout that *did* materialize a real symlink stores the
    target as `os.readlink()` returns it; the correctness check must not
    depend on `os.path.relpath()`'s separator style (backslash on Windows,
    forward slash on POSIX) matching that verbatim.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    sss.sync_one("pr-review-loop", check_only=False)
    expected = os.readlink(dest / "pr-review-loop")
    backslash_style = expected.replace("/", "\\")

    assert sss._normalize_target(backslash_style) == sss._normalize_target(expected)


def test_sync_one_replaces_windows_placeholder_file(dirs):
    """git checks a symlink blob out as a plain-text file containing the
    target string when `core.symlinks=false` (the common Windows default
    without Developer Mode) - this must be recognized and replaced with a
    real symlink, not reported as an unrelated-content conflict.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    expected_target = sss._relative_target("pr-review-loop")
    placeholder = dest / "pr-review-loop"
    placeholder.write_text(expected_target)  # exactly what git checkout produces

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert "placeholder" in message.lower()
    assert placeholder.is_symlink()
    assert (placeholder / "SKILL.md").read_text() == "---\nname: pr-review-loop\n---\n"


def test_sync_one_check_only_reports_placeholder_without_replacing(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    expected_target = sss._relative_target("pr-review-loop")
    placeholder = dest / "pr-review-loop"
    placeholder.write_text(expected_target)

    ok, message = sss.sync_one("pr-review-loop", check_only=True)

    assert ok is False
    assert "PLACEHOLDER" in message
    assert not placeholder.is_symlink()
    assert placeholder.read_text() == expected_target


def test_sync_one_unrelated_file_content_is_still_a_conflict(dirs):
    """A regular file that happens to exist at the destination but whose
    content is *not* the expected symlink target must not be mistaken for
    a placeholder - it may be a contributor's own unrelated file.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    unrelated = dest / "pr-review-loop"
    unrelated.write_text("this is not a symlink placeholder")

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is False
    assert "CONFLICT" in message
    assert unrelated.read_text() == "this is not a symlink placeholder"


def test_sync_one_placeholder_fix_failure_leaves_placeholder_intact(dirs, monkeypatch):
    """If `os.symlink()` fails while replacing a Windows plain-text
    placeholder, the placeholder file itself must not be deleted first -
    the caller should be left with the placeholder (recoverable by
    re-running once Developer Mode/elevation is available), not nothing.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    expected_target = sss._relative_target("pr-review-loop")
    placeholder = dest / "pr-review-loop"
    placeholder.write_text(expected_target)

    monkeypatch.setattr(
        sss.os, "symlink", lambda *a, **k: (_ for _ in ()).throw(OSError("simulated"))
    )

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is False
    assert "FAILED" in message
    assert not placeholder.is_symlink()
    assert placeholder.read_text() == expected_target


def test_create_symlink_safely_passes_target_is_directory(dirs, monkeypatch):
    """Every symlink this script creates points at a skill *directory*
    (.github/skills/<name>/), so target_is_directory=True must always be
    passed - on Windows, omitting it creates a file-type reparse point
    that some directory-aware tools don't resolve correctly.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    calls: list[dict] = []
    real_symlink = sss.os.symlink

    def _recording_symlink(target, dest_path, **kwargs):
        calls.append(kwargs)
        return real_symlink(target, dest_path, **kwargs)

    monkeypatch.setattr(sss.os, "symlink", _recording_symlink)

    sss.sync_one("pr-review-loop", check_only=False)

    assert calls and calls[0].get("target_is_directory") is True


def test_create_symlink_safely_handles_replace_failure(dirs, monkeypatch):
    """If os.replace() itself fails (not just os.symlink()), the failure
    must be caught, the temporary symlink cleaned up, and FAILED returned
    - not an uncaught exception escaping sync_one()/main().
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")

    monkeypatch.setattr(
        sss.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("simulated replace"))
    )

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is False
    assert "FAILED" in message
    assert not (dest / "pr-review-loop").exists()
    assert _scratch_entries(dest) == []


def test_create_symlink_safely_leaves_no_scratch_entry_on_success(dirs):
    """The temporary link is swapped into place, never left behind."""
    source, dest = dirs
    _make_skill(source, "pr-review-loop")

    ok, _ = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert _scratch_entries(dest) == []


def test_create_symlink_safely_never_removes_an_occupying_scratch_path(dirs):
    """An unrelated contributor file already sitting at a scratch-looking
    path must survive: this tool is documented as non-clobbering, so it
    must not delete anything it did not create itself.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    squatter = dest / "pr-review-loop.tmp-symlink"
    squatter.write_text("someone's unrelated work")

    ok, _ = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert (dest / "pr-review-loop").is_symlink()
    assert squatter.is_file()
    assert squatter.read_text() == "someone's unrelated work"


def test_create_symlink_safely_survives_a_directory_at_the_scratch_path(dirs):
    """A *directory* at a scratch-looking path must neither be removed nor
    raise an uncaught `IsADirectoryError` out of `sync_one()`/`main()`.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    squatter = dest / "pr-review-loop.tmp-symlink"
    squatter.mkdir()
    (squatter / "keep.txt").write_text("keep me")

    ok, _ = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert (dest / "pr-review-loop").is_symlink()
    assert (squatter / "keep.txt").read_text() == "keep me"


def test_sync_one_wrong_target_fix_failure_leaves_original_symlink_intact(dirs, monkeypatch):
    """If `os.symlink()` fails while fixing a wrong-target symlink (e.g. a
    Windows privilege error), the pre-existing symlink must not be
    destroyed - the caller should see FAILED, not silently lose both the
    old and new symlink.
    """
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    _make_skill(source, "skill-authoring")
    (dest / "pr-review-loop").symlink_to(source / "skill-authoring")

    def _raise(*_args, **_kwargs):
        raise OSError("simulated: privilege not held")

    monkeypatch.setattr(sss.os, "symlink", _raise)

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is False
    assert "FAILED" in message
    assert "Windows" in message
    # The original (wrong-target) symlink must still be there, untouched.
    assert (dest / "pr-review-loop").is_symlink()
    assert (dest / "pr-review-loop").resolve() == (source / "skill-authoring").resolve()


# --- main ------------------------------------------------------------------


def test_main_returns_zero_when_everything_ok(dirs, capsys):
    source, _ = dirs
    _make_skill(source, "pr-review-loop")

    assert sss.main([]) == 0
    assert sss.main(["--check"]) == 0


def test_main_returns_nonzero_when_check_finds_missing(dirs):
    source, _ = dirs
    _make_skill(source, "pr-review-loop")

    assert sss.main(["--check"]) == 1


def test_main_no_source_skills_returns_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sss, "SOURCE_DIR", tmp_path / "does-not-exist")
    monkeypatch.setattr(sss, "DEST_DIR", tmp_path / ".claude" / "skills")

    assert sss.main([]) == 0
    assert "nothing to do" in capsys.readouterr().out.lower()
