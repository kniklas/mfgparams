"""Regenerate installed coding-agent integrations (Copilot, Claude Code, ...)
from Spec Kit's upstream template source and report whether anything
changed, for the periodic multi-agent skill sync workflow
(specs/011-multi-agent-skill-sync).

Not part of the mfgparams package: this is CI-only tooling invoked by
.github/workflows/ci.yml's sync-agent-integrations job.
"""

from __future__ import annotations

import functools
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_CONFIG = REPO_ROOT / ".specify" / "integration.json"

# data-model.md "Sync Run" outcome vocabulary.
OUTCOME_NO_DRIFT = "no-drift"
OUTCOME_PR = "pull-request-opened-or-updated"
OUTCOME_FAILED = "failed"

# data-model.md "Integration" status vocabulary.
STATUS_MODIFIED_BLOCKED = "modified-blocked"
STATUS_UPGRADED_NO_CHANGE = "upgraded-no-change"
STATUS_UPGRADED_WITH_CHANGES = "upgraded-with-changes"
STATUS_FAILED = "failed"


_UPDATE_AVAILABLE_RE = re.compile(r"Update available:\s*\S+\s*→\s*(\S+)")
_UP_TO_DATE_RE = re.compile(r"Up to date:")


# check_specify_cli_up_to_date() outcome vocabulary (FR-013).
CLI_CHECK_UP_TO_DATE = "up-to-date"
CLI_CHECK_UPDATE_AVAILABLE = "update-available"
CLI_CHECK_INCONCLUSIVE = "inconclusive"


@dataclass
class CliCheckResult:
    status: str
    detail: str | None = None


def check_specify_cli_up_to_date() -> CliCheckResult:
    """Run `specify self check` (read-only - it never modifies the
    installation) and classify the result.

    This is a genuine live check against GitHub's Releases API (unlike
    `specify integration upgrade`, whose templates are bundled inside the
    installed CLI package itself - research.md #2 addendum), so it is the
    only way this workflow can actually detect that upstream has moved on
    since the pinned version, given FR-012 forbids the workflow from ever
    bumping that pin itself.

    Anything short of a confirmed `CLI_CHECK_UP_TO_DATE` is
    `CLI_CHECK_INCONCLUSIVE` - an unexpected non-zero exit, or *any* CLI
    output that isn't the explicit `Up to date:` success marker (this
    includes the CLI's own documented graceful-failure text for a network
    outage or rate limit, but also anything else not specifically
    anticipated here, e.g. `Current version could not be determined.` when
    local version metadata is unavailable) - which the caller MUST treat as
    a failure too, not silently proceed past: spec.md SC-001 promises the
    maintainer is *always* notified within a week, and a silently-swallowed
    "couldn't check" would break that promise exactly as easily as a
    genuinely stale pin would. Matching on the one known-good success
    marker (rather than maintaining a blocklist of known-bad ones) means an
    unanticipated future CLI message defaults to safely inconclusive
    instead of being misread as confirmed-current.
    """
    proc = subprocess.run(
        ["specify", "self", "check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return CliCheckResult(
            status=CLI_CHECK_INCONCLUSIVE,
            detail=proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}",
        )
    match = _UPDATE_AVAILABLE_RE.search(proc.stdout)
    if match:
        return CliCheckResult(status=CLI_CHECK_UPDATE_AVAILABLE, detail=match.group(1))
    if _UP_TO_DATE_RE.search(proc.stdout):
        return CliCheckResult(status=CLI_CHECK_UP_TO_DATE)
    return CliCheckResult(status=CLI_CHECK_INCONCLUSIVE, detail=proc.stdout.strip())


def load_installed_integrations() -> list[str]:
    """Read the installed integration keys from .specify/integration.json.

    Reading this list (rather than hard-coding integration names) is what
    lets a future integration be picked up with zero workflow/script
    changes (FR-010).
    """
    data = json.loads(INTEGRATION_CONFIG.read_text())
    return list(data["installed_integrations"])


@functools.lru_cache(maxsize=1)
def _global_status() -> dict[str, Any]:
    """Run `specify integration status --json` once per process and cache
    the parsed result; every installed integration's status is reported in
    a single call, so callers should not re-invoke the CLI per integration.

    The command exits non-zero whenever *any* installed integration has a
    finding (missing/modified files) - that is normal, expected input for
    this drift check, not a tooling failure, so stdout is parsed regardless
    of the exit code.
    """
    proc = subprocess.run(
        ["specify", "integration", "status", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    result: dict[str, Any] = json.loads(proc.stdout)
    return result


def run_integration_status(key: str) -> dict[str, Any]:
    """Return the parsed `specify integration status --json` entry for one
    integration (research.md #1): its `modified_files`/`missing_files`.
    """
    manifests: dict[str, Any] = _global_status().get("manifests", {})
    entry: dict[str, Any] = manifests.get(key, {})
    return entry


SHARED_INFRA_KEY = "speckit"


def check_shared_infra_modified() -> str | None:
    """Return the first locally-modified shared-infrastructure file, if
    any, else `None`.

    Every `specify integration upgrade <key>` call also reconciles shared
    infrastructure tracked by the separate `speckit` manifest - verified in
    the installed CLI's `integration_upgrade` implementation, which calls
    `_install_shared_infra_or_exit` unconditionally, not just for the
    default integration - so a locally-modified shared file is relevant
    regardless of which specific integration's upgrade happens to run in
    this loop. `run_integration_status()` already generically reads
    `manifests.<key>` from the shared, cached global status payload, and
    `speckit` is itself one of the keys that command reports, so this
    reuses that helper directly rather than adding a second status-parsing
    path (FR-008's "surface that fact" duty is not limited to
    per-integration generated files).
    """
    status = run_integration_status(SHARED_INFRA_KEY)
    modified = status.get("modified_files") or []
    return modified[0] if modified else None


@dataclass
class IntegrationResult:
    key: str
    status: str
    changed_files: list[str] = field(default_factory=list)
    blocked_file: str | None = None
    error: str | None = None


def _manifest_tracked_paths(key: str) -> list[str] | None:
    """Return the manifest's tracked file paths, or `None` if the manifest
    file itself doesn't exist - distinct from a manifest that exists but
    genuinely tracks zero files. The distinction matters: `specify
    integration upgrade <key>` exits 0 with "Nothing to upgrade" and makes
    no changes at all when the manifest is absent (an installed-but-never-
    materialized integration - e.g. `key` listed in
    `.specify/integration.json` without ever running `specify integration
    install <key>`), which `run_integration_upgrade()` must not silently
    read as "no drift."
    """
    manifest_path = REPO_ROOT / ".specify" / "integrations" / f"{key}.manifest.json"
    if not manifest_path.exists():
        return None
    data = json.loads(manifest_path.read_text())
    return list(data.get("files", {}).keys())


def run_integration_upgrade(key: str) -> IntegrationResult:
    """Run `specify integration upgrade <key>` (never `--force`) and
    classify the outcome for that integration (data-model.md "Integration").

    A locally-modified file is detected via `run_integration_status()`
    *before* attempting the upgrade, so that case is reported precisely as
    `modified-blocked` (FR-008) rather than inferred by parsing the CLI's
    own block message - and the upgrade subprocess, which would only block
    anyway, is never invoked for that integration (FR-012's "don't silently
    discard a hand-edit" intent).
    """
    try:
        status = run_integration_status(key)
    except Exception as exc:  # subprocess/JSON failure querying status itself
        return IntegrationResult(key=key, status=STATUS_FAILED, error=str(exc))

    modified_files = status.get("modified_files") or []
    if modified_files:
        return IntegrationResult(
            key=key,
            status=STATUS_MODIFIED_BLOCKED,
            blocked_file=modified_files[0],
        )

    paths_before = _manifest_tracked_paths(key)

    proc = subprocess.run(
        ["specify", "integration", "upgrade", key, "--script", "py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return IntegrationResult(
            key=key,
            status=STATUS_FAILED,
            error=proc.stderr.strip() or proc.stdout.strip(),
        )

    # Union of the manifest's tracked paths before and after the upgrade: a
    # path removed by the upgrade (upstream deleted a generated file) is
    # absent from the *new* manifest, so relying on the post-upgrade list
    # alone would miss that deletion entirely and misreport it as no drift.
    paths_after = _manifest_tracked_paths(key)
    if paths_after is None:
        # The manifest still doesn't exist after "upgrading" - `upgrade`
        # exits 0 with "Nothing to upgrade" against a missing manifest and
        # makes no changes at all, so this integration was never actually
        # installed. Silently reporting no drift here would hide a
        # genuinely broken/incomplete integration entry.
        return IntegrationResult(
            key=key,
            status=STATUS_FAILED,
            error=(
                f"no manifest found for integration {key!r} even after "
                f"upgrade - it is listed in .specify/integration.json but "
                f"was never actually installed (run `specify integration "
                f"install {key}` first)"
            ),
        )
    tracked_paths = sorted(set(paths_before or []) | set(paths_after))
    changed_files: list[str] = []
    if tracked_paths:
        diff = subprocess.run(
            ["git", "status", "--porcelain", "--", *tracked_paths],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if diff.returncode != 0:
            # A failed `git status` commonly returns empty stdout, which
            # would otherwise be silently misread as "nothing changed" -
            # exactly the kind of silent false-negative FR-007 forbids.
            return IntegrationResult(
                key=key,
                status=STATUS_FAILED,
                error=diff.stderr.strip() or "git status failed",
            )
        changed_files = [line[3:] for line in diff.stdout.splitlines() if line.strip()]

    if changed_files:
        return IntegrationResult(
            key=key, status=STATUS_UPGRADED_WITH_CHANGES, changed_files=changed_files
        )
    return IntegrationResult(key=key, status=STATUS_UPGRADED_NO_CHANGE)


@dataclass
class SyncRunOutcome:
    outcome: str
    integrations: list[IntegrationResult]
    shared_infra_modified_file: str | None = None


def derive_run_outcome(integrations: list[IntegrationResult]) -> SyncRunOutcome:
    """Priority-ordered derivation per data-model.md "Sync Run":
    failed > upgraded-with-changes > modified-blocked > no-drift.

    A generic tooling/network failure (`failed`) always aborts the run: it
    is not a safe, disclosed condition, so no partial pull request is ever
    opened over it (spec.md's partial-failure edge case). A locally-modified
    file (`modified-blocked`) is different in kind - it is the CLI's own
    deliberate, expected safety mechanism (research.md #1) - so it does not
    by itself block a pull request for *other* integrations that did have
    real changes; it is instead surfaced transparently in that same pull
    request's body (FR-008; compose_pull_request_body()). Only when nothing
    at all changed (every integration is either blocked or already
    up to date) does a modified-blocked integration make the run `failed`,
    since there would otherwise be nothing to actually put in a pull
    request.
    """
    if any(r.status == STATUS_FAILED for r in integrations):
        return SyncRunOutcome(outcome=OUTCOME_FAILED, integrations=integrations)
    if any(r.status == STATUS_UPGRADED_WITH_CHANGES for r in integrations):
        return SyncRunOutcome(outcome=OUTCOME_PR, integrations=integrations)
    if any(r.status == STATUS_MODIFIED_BLOCKED for r in integrations):
        return SyncRunOutcome(outcome=OUTCOME_FAILED, integrations=integrations)
    return SyncRunOutcome(outcome=OUTCOME_NO_DRIFT, integrations=integrations)


def compose_pull_request_body(
    integrations: list[IntegrationResult],
    shared_infra_modified_file: str | None = None,
) -> str:
    """Produce the pull-request body per contracts/sync-workflow-contract.md
    "Sync Pull Request body contract": changed integrations named first,
    then (only when at least one other integration also changed) a callout
    for any integration blocked by a locally-modified file (FR-008;
    data-model.md "Sync Pull Request".blocked_integrations), then (if set)
    a note about a locally-modified *shared* infrastructure file
    (check_shared_infra_modified()) - informational only, since a normal
    (non-`--force`) upgrade silently skips existing shared files rather
    than blocking on them, but FR-008 still requires surfacing the fact.
    """
    changed = [r.key for r in integrations if r.status == STATUS_UPGRADED_WITH_CHANGES]
    blocked = [
        (r.key, r.blocked_file)
        for r in integrations
        if r.status == STATUS_MODIFIED_BLOCKED and r.blocked_file
    ]

    lines = [
        "Automated sync: regenerated the following coding-agent "
        "integration(s) from Spec Kit's upstream template source "
        "(specs/011-multi-agent-skill-sync).",
        "",
        "**Changed integrations:**",
    ]
    lines.extend(f"- `{key}`" for key in changed)

    if blocked:
        lines.append("")
        lines.append("**Not updated (locally-modified file detected — review before " "merging):**")
        lines.extend(f"- `{key}`: `{file}`" for key, file in blocked)

    if shared_infra_modified_file:
        lines.append("")
        lines.append(
            "**Note:** shared Spec Kit infrastructure has a locally-modified "
            f"file (`{shared_infra_modified_file}`) that this sync did not "
            "touch — review whether that customization is still intended."
        )

    return "\n".join(lines) + "\n"


def _write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        if "\n" in value:
            delimiter = "SYNC_OUTPUT_EOF"
            fh.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
        else:
            fh.write(f"{name}={value}\n")


def write_workflow_output(result: SyncRunOutcome) -> None:
    """Write `has_changes`/`pr_body` to `$GITHUB_OUTPUT` (FR-004;
    contracts/sync-workflow-contract.md "no-drift" guarantee) so the
    workflow can conditionally invoke the PR-creation step.
    """
    has_changes = result.outcome == OUTCOME_PR
    _write_github_output("has_changes", "true" if has_changes else "false")
    body = (
        compose_pull_request_body(result.integrations, result.shared_infra_modified_file)
        if has_changes
        else ""
    )
    _write_github_output("pr_body", body)


def main() -> int:
    cli_check = check_specify_cli_up_to_date()
    if cli_check.status != CLI_CHECK_UP_TO_DATE:
        # Fail-and-notify (spec.md FR-013): this workflow never bumps its
        # own pinned specify-cli version (FR-012), so a stale pin can only
        # be surfaced, never silently worked around. No integration checks
        # run in this case - they would only report a false "no drift"
        # against the stale, bundled templates (research.md #2 addendum).
        # An inconclusive check (network/rate-limit/unexpected failure)
        # fails the run too, with a distinct message - silently proceeding
        # past "couldn't verify" would break spec.md SC-001's guarantee
        # exactly as easily as a confirmed-stale pin would.
        write_workflow_output(SyncRunOutcome(outcome=OUTCOME_FAILED, integrations=[]))
        if cli_check.status == CLI_CHECK_UPDATE_AVAILABLE:
            print(
                f"::error::A newer specify-cli release is available "
                f"({cli_check.detail}); this workflow never bumps its own "
                f"pinned version (FR-012). A maintainer must update the pin "
                f"in .github/workflows/ci.yml and .specify/integration.json, "
                f"then re-run this workflow.",
                file=sys.stderr,
            )
        else:
            print(
                f"::error::Could not verify whether specify-cli is up to "
                f"date ({cli_check.detail}); treating this as a failure "
                f"rather than silently proceeding (FR-013). Re-run this "
                f"workflow once the check succeeds.",
                file=sys.stderr,
            )
        return 1

    results = [run_integration_upgrade(key) for key in load_installed_integrations()]

    outcome = derive_run_outcome(results)
    outcome.shared_infra_modified_file = check_shared_infra_modified()
    write_workflow_output(outcome)

    failed_run = outcome.outcome == OUTCOME_FAILED
    for r in results:
        if r.status == STATUS_MODIFIED_BLOCKED:
            # A blocked integration doesn't fail the run by itself when at
            # least one other integration still has real changes to PR
            # (derive_run_outcome); it's a warning there, not an error,
            # since it's already disclosed in the PR body (FR-008).
            level = "error" if failed_run else "warning"
            print(
                f"::{level}::Integration '{r.key}' blocked: locally-modified "
                f"file {r.blocked_file!r} detected (run `specify integration "
                f"status --json` for details)",
                file=sys.stderr,
            )
        elif r.status == STATUS_FAILED:
            print(
                f"::error::Integration '{r.key}' failed: {r.error}",
                file=sys.stderr,
            )

    return 1 if failed_run else 0


if __name__ == "__main__":
    sys.exit(main())
