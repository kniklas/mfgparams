# Contract: PR Quality Check Summary Comment

This is not a library/network API contract; it is the interface this feature exposes to
contributors and reviewers reading a pull request, and the interface between CI jobs that
produces it. It documents the guaranteed shape/behavior so consumers (reviewers) and future
maintainers (editing `.github/workflows/ci.yml`) can rely on it without re-reading the
workflow YAML.

## Trigger contract

- The summary job (`quality-summary`) MUST only execute its comment-posting logic when
  `github.event_name == 'pull_request'` (spec.md FR-006).
- It MUST NOT run, and MUST NOT post or update any comment, for `push` (including
  push-to-`main`), `schedule`, or `workflow_dispatch`-triggered runs.
- It MUST still evaluate (via `if: always()`) even when one or more of its `needs:` jobs
  failed or was cancelled, so it can accurately report failure/cancellation rather than being
  skipped itself (spec.md User Story 1 Acceptance Scenario 3).

## Input contract (what `quality-summary` consumes)

| Input | Shape | Guarantee |
|---|---|---|
| `needs.<job>.result` for `lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test`, `build`, `docs` | one of `success`/`failure`/`cancelled`/`skipped` | Always present for every listed job once it is included in `needs:`; GitHub Actions guarantees exactly one of these four values per dependency |
| ~~`needs.test.outputs.coverage_pct`~~ **— superseded by `013-tox-multi-python-testing`; see the row below** | string containing an integer percentage (e.g. `"93"`) | Present whenever the `test` job itself reaches the coverage-report step (i.e. `pytest` ran, regardless of pass/fail on the coverage threshold); absent/empty if the job failed before that step (e.g. environment setup failure) — the summary MUST render a fallback placeholder in that case, never a fabricated number (spec.md Edge Cases: "job fails so early that it produces no parseable metric output") |
| the `coverage-pct` **artifact** (`coverage-pct.txt`) | string containing an integer percentage (e.g. `"93"`) | **Replaces the job output above.** `013-tox-multi-python-testing` made `test` a Python-version matrix, and a matrix job publishes one output value from whichever leg finishes last — so no job output can name which interpreter a coverage number came from, and coverage genuinely differs per interpreter here. The canonical `env.PYTHON_VERSION` leg now writes the percentage to this artifact instead, and `quality-summary` downloads it with `continue-on-error: true`. The guarantee is otherwise unchanged: present whenever that leg reached its coverage-report step, absent when it did not, and the summary MUST render the fallback placeholder in that case rather than a fabricated number. See `specs/013-tox-multi-python-testing/research.md` #5 |
| `needs.complexity.outputs.mi_summary` | short string (e.g. `"avg=74.3 worst=A"`) | Present only on the `complexity` job's passing path (research.md #4); absent when the job fails (violations are already visible via `status: failure`, and the summary MUST still show that check as failed with a fallback indicator, not a fabricated metric) |

## Output contract (the rendered PR comment)

The comment body MUST include, at minimum:

1. **One row per quality check** (`lint`, `complexity`, `typecheck`, `security`,
   `dependency-scan`, `test`, `build`, `docs`), each showing:
   - The check's name.
   - A clear, unambiguous status indicator distinguishing all four of `success` / `failure`
     / `cancelled` / `skipped` (e.g. distinct emoji/labels per state — never collapsing
     `skipped`/`cancelled` into a bare "failed" or omitting the row) (FR-007).
   - The check's metric value if it has one (`test` → coverage percentage; `complexity` →
     Maintainability Index summary), or an explicit "no metric" placeholder for all other
     checks (FR-005; User Story 3 Acceptance Scenario 3).
2. **One overall status** summarizing the run as a whole (FR-004), computed as:
   - `FAIL` if any check's status is `failure`.
   - Otherwise a distinct cancelled/incomplete indicator if any check's status is
     `cancelled`.
   - Otherwise `PASS` (a `skipped` check does not, by itself, flip the overall status to
     `FAIL`, per spec.md's Assumptions on `dependency-scan`/`build`/`docs` following the same
     rules as the named checks).
3. **A stable identifying marker** (the sticky-comment action's `header: quality-check-summary`
   input), not necessarily visible as rendered text, but reliably present across every posted/
   updated instance of the comment so the same comment is always found and edited in place on
   subsequent runs (FR-009).

## Idempotency / update contract

- Exactly one such comment MUST exist per pull request at any time, regardless of how many
  times CI has run for that PR (FR-003; SC-001; SC-003).
- Each subsequent pull-request-triggered run MUST replace the existing comment's full content
  with that run's results; it MUST NOT append, duplicate, or leave stale partial content
  (User Story 2 Acceptance Scenarios 1-2; Edge Cases: rapid concurrent runs converge to the
  most recently completed run's results).

## Failure-isolation contract

- A failure to post or update the comment (e.g. `Resource not accessible by integration` on a
  fork-originated pull request where the default `GITHUB_TOKEN` is read-only) MUST NOT:
  - Change the reported/required status of any of the eight underlying quality-check jobs.
  - Fail the `quality-summary` job or the overall workflow run.
  (FR-008; spec.md Edge Cases on fork PRs with restricted permissions.)
- This isolation is scoped to the comment-posting step only; a bug in the summary-assembly
  logic itself (e.g. malformed Markdown generation) is NOT covered by this guarantee and MUST
  still surface as a visible job failure for maintainers to fix (research.md #6).
