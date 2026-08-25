"""Unit/integration tests for scripts/sync_agent_integrations.py
(specs/011-multi-agent-skill-sync tasks.md T007, T012, T015).

`scripts/` is not part of the installed `mfgparams` package (it is
CI-only tooling, research.md #5), so the module under test is imported
directly by path rather than via a package import.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sync_agent_integrations as sai  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_status_cache():
    sai._global_status.cache_clear()
    yield
    sai._global_status.cache_clear()


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# --- load_installed_integrations (T007) -------------------------------------


def test_load_installed_integrations_reads_config(tmp_path, monkeypatch):
    config = tmp_path / "integration.json"
    config.write_text(json.dumps({"installed_integrations": ["copilot", "claude", "cursor"]}))
    monkeypatch.setattr(sai, "INTEGRATION_CONFIG", config)

    assert sai.load_installed_integrations() == ["copilot", "claude", "cursor"]


# --- run_integration_status (T007) -------------------------------------------


def test_run_integration_status_returns_manifest_for_key_and_caches():
    status_json = json.dumps(
        {
            "manifests": {
                "copilot": {"modified_files": [], "missing_files": []},
                "claude": {"modified_files": ["skills/x.md"], "missing_files": []},
            }
        }
    )
    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)) as mock_run:
        result_copilot = sai.run_integration_status("copilot")
        result_claude = sai.run_integration_status("claude")

    assert result_copilot == {"modified_files": [], "missing_files": []}
    assert result_claude == {"modified_files": ["skills/x.md"], "missing_files": []}
    # Two integrations queried, but the underlying CLI is invoked once (cached).
    assert mock_run.call_count == 1


def test_run_integration_status_parses_json_even_on_nonzero_exit():
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": ["a"]}}})
    with patch.object(sai.subprocess, "run", return_value=_completed(1, status_json)):
        result = sai.run_integration_status("copilot")
    assert result == {"modified_files": ["a"]}


# --- run_integration_upgrade (T007) ------------------------------------------


def test_run_integration_upgrade_modified_blocked_skips_upgrade_call():
    status_json = json.dumps(
        {"manifests": {"copilot": {"modified_files": [".github/prompts/x.md"]}}}
    )
    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)) as mock_run:
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_MODIFIED_BLOCKED
    assert result.blocked_file == ".github/prompts/x.md"
    # Only the status call happened; upgrade must never be invoked when blocked.
    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0][:3] == ["specify", "integration", "status"]


def test_run_integration_upgrade_generic_failure():
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(1, "", "network error contacting upstream")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_FAILED
    assert "network error" in result.error


def test_run_integration_upgrade_with_changes(monkeypatch):
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: [".github/prompts/x.md"])

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, " M .github/prompts/x.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_UPGRADED_WITH_CHANGES
    assert result.changed_files == [".github/prompts/x.md"]


def test_run_integration_upgrade_no_change(monkeypatch):
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: [".github/prompts/x.md"])

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, "")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_UPGRADED_NO_CHANGE
    assert result.changed_files == []


def test_run_integration_upgrade_detects_deletion_only_drift(monkeypatch):
    """A file present in the manifest *before* the upgrade but absent
    *after* it (upstream deleted a generated file) must still be detected -
    scoping git status to only the post-upgrade manifest's paths would miss
    it entirely and misreport the run as no drift."""
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    manifest_calls = iter(
        [
            [".github/prompts/x.md", ".github/prompts/removed.md"],  # before
            [".github/prompts/x.md"],  # after: removed.md is gone
        ]
    )
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: next(manifest_calls))

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            assert ".github/prompts/removed.md" in cmd
            return _completed(0, " D .github/prompts/removed.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_UPGRADED_WITH_CHANGES
    assert result.changed_files == [".github/prompts/removed.md"]


def test_run_integration_upgrade_git_status_failure_is_reported(monkeypatch):
    """A failed `git status` commonly returns empty stdout, which must not
    be misread as 'nothing changed' - that would silently hide a real
    change (second-round Copilot review)."""
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: ["x.md"])

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(1, "", "fatal: git status failed")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_FAILED
    assert "git status failed" in result.error


def test_run_integration_upgrade_missing_manifest_after_upgrade_fails(monkeypatch):
    """`specify integration upgrade <key>` exits 0 with "Nothing to
    upgrade" and makes no changes at all when the manifest is absent (an
    installed-but-never-materialized integration) - must not be silently
    read as 'no drift' (third-round Copilot review)."""
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: None)

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "No manifest found for integration 'copilot'. Nothing to upgrade.")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_FAILED
    assert "never actually installed" in result.error


# --- check_shared_infra_modified (FR-008, third-round Copilot review) -------


def test_check_shared_infra_modified_none_when_clean():
    status_json = json.dumps({"manifests": {"speckit": {"modified_files": []}}})
    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)):
        assert sai.check_shared_infra_modified() is None


def test_check_shared_infra_modified_returns_first_file():
    status_json = json.dumps(
        {"manifests": {"speckit": {"modified_files": [".specify/templates/tasks-template.md"]}}}
    )
    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)):
        assert sai.check_shared_infra_modified() == ".specify/templates/tasks-template.md"


def test_check_shared_infra_modified_none_when_key_absent():
    """No `speckit` entry at all (e.g. a mock that only lists per-agent
    integrations) must not raise - just report nothing modified."""
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)):
        assert sai.check_shared_infra_modified() is None


# --- derive_run_outcome (T007) -----------------------------------------------


def _result(key, status, **kw):
    return sai.IntegrationResult(key=key, status=status, **kw)


def test_derive_run_outcome_no_drift():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_UPGRADED_NO_CHANGE),
            _result("claude", sai.STATUS_UPGRADED_NO_CHANGE),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_NO_DRIFT


def test_derive_run_outcome_pull_request():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_UPGRADED_NO_CHANGE),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_PR


def test_derive_run_outcome_mixed_blocked_and_changed_is_still_pull_request():
    """A blocked integration doesn't sink a run that has real changes to PR
    elsewhere - it's disclosed transparently in that PR's body instead
    (FR-008), not treated as a silent partial-failure omission."""
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_MODIFIED_BLOCKED, blocked_file="x.md"),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_PR


def test_derive_run_outcome_all_blocked_with_no_changes_is_failed():
    """When nothing at all changed, a blocked integration has no PR to be
    disclosed in, so the run is failed instead of a pointless empty PR."""
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_MODIFIED_BLOCKED, blocked_file="x.md"),
            _result("claude", sai.STATUS_UPGRADED_NO_CHANGE),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_FAILED


def test_derive_run_outcome_failed_takes_priority_over_upgraded_with_changes():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_FAILED, error="boom"),
            _result("claude", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_FAILED


def test_derive_run_outcome_failed_takes_priority_over_modified_blocked():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_FAILED, error="boom"),
            _result("claude", sai.STATUS_MODIFIED_BLOCKED, blocked_file="x.md"),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_FAILED


# --- compose_pull_request_body (T015) ----------------------------------------


def test_compose_pull_request_body_names_all_changed_integrations():
    body = sai.compose_pull_request_body(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["b"]),
        ]
    )
    assert "`copilot`" in body
    assert "`claude`" in body
    assert "Not updated" not in body


def test_compose_pull_request_body_includes_blocked_callout_alongside_changes():
    body = sai.compose_pull_request_body(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_MODIFIED_BLOCKED, blocked_file=".claude/skills/x.md"),
        ]
    )
    assert "`copilot`" in body
    assert "Not updated" in body
    assert "`claude`" in body
    assert ".claude/skills/x.md" in body


def test_compose_pull_request_body_no_blocked_section_when_nothing_blocked():
    body = sai.compose_pull_request_body(
        [_result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"])]
    )
    assert "Not updated" not in body


def test_compose_pull_request_body_notes_shared_infra_modification():
    body = sai.compose_pull_request_body(
        [_result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"])],
        shared_infra_modified_file=".specify/templates/tasks-template.md",
    )
    assert ".specify/templates/tasks-template.md" in body


def test_compose_pull_request_body_no_shared_infra_note_when_unset():
    body = sai.compose_pull_request_body(
        [_result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"])]
    )
    assert "shared Spec Kit infrastructure" not in body


# --- main() end-to-end (T012) -------------------------------------------------


# --- check_specify_cli_up_to_date (FR-013) -----------------------------------


def test_check_specify_cli_up_to_date_no_update():
    stdout = "Up to date: 1.0.0\n"
    with patch.object(sai.subprocess, "run", return_value=_completed(0, stdout)):
        result = sai.check_specify_cli_up_to_date()
    assert result.status == sai.CLI_CHECK_UP_TO_DATE


def test_check_specify_cli_up_to_date_update_available():
    stdout = "Update available: 1.0.0 → v1.0.1\n\nTo upgrade:\n  specify self upgrade\n"
    with patch.object(sai.subprocess, "run", return_value=_completed(0, stdout)):
        result = sai.check_specify_cli_up_to_date()
    assert result.status == sai.CLI_CHECK_UPDATE_AVAILABLE
    assert result.detail == "v1.0.1"


def test_check_specify_cli_up_to_date_network_failure_is_inconclusive():
    stdout = "Installed: 1.0.0\nCould not check latest release: network error\n"
    with patch.object(sai.subprocess, "run", return_value=_completed(0, stdout)):
        result = sai.check_specify_cli_up_to_date()
    assert result.status == sai.CLI_CHECK_INCONCLUSIVE


def test_check_specify_cli_up_to_date_nonzero_exit_is_inconclusive():
    """An unexpected crash (distinct from the CLI's own documented exit-0
    graceful-failure text) must also be inconclusive, not silently treated
    as up to date."""
    with patch.object(sai.subprocess, "run", return_value=_completed(1, "", "traceback...")):
        result = sai.check_specify_cli_up_to_date()
    assert result.status == sai.CLI_CHECK_INCONCLUSIVE
    assert "traceback" in result.detail


def test_check_specify_cli_up_to_date_unrecognized_exit_zero_text_is_inconclusive():
    """An exit-0 message that is neither the success marker nor a
    previously-known failure string (e.g. the CLI's own "Current version
    could not be determined." path) must still default to inconclusive,
    not silently pass as up to date - third-round Copilot review."""
    stdout = "Current version could not be determined.\nLatest release: v1.0.1\n"
    with patch.object(sai.subprocess, "run", return_value=_completed(0, stdout)):
        result = sai.check_specify_cli_up_to_date()
    assert result.status == sai.CLI_CHECK_INCONCLUSIVE


def _stub_self_check_up_to_date(cmd):
    """Shared fake_run branch: every main()-level test below must handle
    the FR-013 `specify self check` call main() now makes first."""
    if cmd[:3] == ["specify", "self", "check"]:
        return _completed(0, "Up to date: 1.0.0\n")
    return None


def test_main_no_drift_writes_has_changes_false(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot"])
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})

    def fake_run(cmd, **kwargs):
        stub = _stub_self_check_up_to_date(cmd)
        if stub is not None:
            return stub
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, "")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    assert exit_code == 0
    assert "has_changes=false" in output_file.read_text()


def test_main_drift_found_writes_has_changes_true(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot"])
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: ["x.md"])
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})

    def fake_run(cmd, **kwargs):
        stub = _stub_self_check_up_to_date(cmd)
        if stub is not None:
            return stub
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, " M x.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    output_content = output_file.read_text()
    assert exit_code == 0
    assert "has_changes=true" in output_content
    assert "copilot" in output_content


def test_main_notes_shared_infra_modification_in_pr_body(tmp_path, monkeypatch):
    """End-to-end proof that a locally-modified shared speckit file reaches
    the composed PR body through main() (third-round Copilot review)."""
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot"])
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: ["x.md"])
    status_json = json.dumps(
        {
            "manifests": {
                "copilot": {"modified_files": []},
                "speckit": {"modified_files": [".specify/templates/tasks-template.md"]},
            }
        }
    )

    def fake_run(cmd, **kwargs):
        stub = _stub_self_check_up_to_date(cmd)
        if stub is not None:
            return stub
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, " M x.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    output_content = output_file.read_text()
    assert exit_code == 0
    assert ".specify/templates/tasks-template.md" in output_content


def test_main_failure_exits_nonzero(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot"])
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": ["x.md"]}}})

    def fake_run(cmd, **kwargs):
        stub = _stub_self_check_up_to_date(cmd)
        if stub is not None:
            return stub
        return _completed(0, status_json)

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    assert exit_code == 1
    assert "has_changes=false" in output_file.read_text()


def test_main_mixed_blocked_and_changed_still_opens_pr_with_callout(tmp_path, monkeypatch):
    """End-to-end proof that a blocked integration alongside a genuinely
    changed one reaches OUTCOME_PR through main() (not just through
    compose_pull_request_body() called directly) - closing the gap where
    the blocked-callout branch was previously unreachable in production."""
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot", "claude"])
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: ["x.md"])
    status_json = json.dumps(
        {
            "manifests": {
                "copilot": {"modified_files": []},
                "claude": {"modified_files": [".claude/skills/y.md"]},
            }
        }
    )

    def fake_run(cmd, **kwargs):
        stub = _stub_self_check_up_to_date(cmd)
        if stub is not None:
            return stub
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, " M x.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    output_content = output_file.read_text()
    assert exit_code == 0
    assert "has_changes=true" in output_content
    assert "`copilot`" in output_content
    assert "Not updated" in output_content
    assert ".claude/skills/y.md" in output_content


def test_main_all_blocked_no_changes_fails(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot", "claude"])
    status_json = json.dumps(
        {
            "manifests": {
                "copilot": {"modified_files": ["x.md"]},
                "claude": {"modified_files": []},
            }
        }
    )

    def fake_run(cmd, **kwargs):
        stub = _stub_self_check_up_to_date(cmd)
        if stub is not None:
            return stub
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, "")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    assert exit_code == 1
    assert "has_changes=false" in output_file.read_text()


def test_main_stale_cli_fails_without_checking_integrations(tmp_path, monkeypatch):
    """When a newer specify-cli release exists, main() must fail immediately
    and never call load_installed_integrations()/run_integration_upgrade()
    at all - those would only report a false no-drift against the stale,
    bundled templates (FR-013)."""
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    def fail_if_called():
        raise AssertionError("load_installed_integrations() must not be called")

    monkeypatch.setattr(sai, "load_installed_integrations", fail_if_called)
    stdout = "Update available: 1.0.0 → v1.0.1\n"

    with patch.object(sai.subprocess, "run", return_value=_completed(0, stdout)):
        exit_code = sai.main()

    assert exit_code == 1
    assert "has_changes=false" in output_file.read_text()


def test_main_inconclusive_cli_check_also_fails_without_checking_integrations(
    tmp_path, monkeypatch
):
    """An inconclusive specify-cli check (e.g. GitHub unreachable) must fail
    the run exactly like a confirmed-stale one - not be silently treated as
    'assume up to date' (spec.md SC-001; second-round Copilot review)."""
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    def fail_if_called():
        raise AssertionError("load_installed_integrations() must not be called")

    monkeypatch.setattr(sai, "load_installed_integrations", fail_if_called)
    stdout = "Installed: 1.0.0\nCould not check latest release: network error\n"

    with patch.object(sai.subprocess, "run", return_value=_completed(0, stdout)):
        exit_code = sai.main()

    assert exit_code == 1
    assert "has_changes=false" in output_file.read_text()
