# Research: CI Path-Based Job Selection

## 1. Mechanism for computing which paths changed

**Decision**: Add a `changes` job to `ci.yml` using `dorny/paths-filter@v3` (pinned by tag,
same convention as this workflow's other third-party actions), guarded by
`if: github.event_name != 'schedule'` — identical guard to every job it would gate. It emits
one boolean output per path category (see data-model.md); every filtered job adds
`needs: [changes]` and reads `needs.changes.outputs.<category>` in its own `if:`.

**Rationale**: The spec's own Assumptions section already ruled out GitHub's native
`paths:`/`paths-ignore:` workflow-level trigger filters — they operate per-workflow, not
per-job, so a non-matching PR would never produce a `ci-ok` run at all, permanently blocking
the PR (the exact failure mode `ci-ok`'s own existing comment on required-check semantics
warns about). A per-job `if:` computed from actual changed files is the only mechanism that
preserves "the workflow always runs; individual jobs decide whether to." `dorny/paths-filter`
is a widely-used, actively maintained action built exactly for this (per-filter boolean job
outputs consumable by downstream `if:` conditions) rather than reinventing diff computation in
a hand-rolled script — consistent with this repo's existing pattern of trusting well-known
pinned third-party actions for undifferentiated CI plumbing (`codecov/codecov-action`,
`peter-evans/create-pull-request`, etc.) while reserving hand-written Python for
project-specific logic (`scripts/check_maintainability.py`).

**Alternatives considered**:
- `tj-actions/changed-files` — comparable capability, but returns file lists rather than
  named boolean filters, pushing the category-matching logic into shell/Python in each
  consuming job instead of centralizing it in one filter job's YAML config. Rejected: more
  duplicated logic across 7 jobs for no capability gain.
- Hand-rolled `git diff --name-only $BASE...$HEAD | grep` script — no new dependency, but
  reimplements base-ref resolution `dorny/paths-filter` already handles correctly for both
  `pull_request` (diff against PR base) and `push` (diff against the pre-push SHA) events,
  and would need its own tests for that resolution logic. Rejected as needless reinvention.

## 2. Path category → glob mapping

**Decision**: Four named categories, matching spec.md's Assumptions section exactly:

| Category | Globs |
|---|---|
| `python` | `src/**`, `tests/**`, `pyproject.toml`, `tox.ini`, `scripts/sync_agent_integrations.py`, `scripts/setup_skill_symlinks.py` |
| `docs` | `docs/**` |
| `ci_config` | `.github/workflows/**` |
| `other` (catch-all) | Everything not matched by any named filter above **or** by the known-non-code paths in spec.md's Assumptions (`specs/**`, `.github/skills/**`, root `*.md`, `.claude/**`), via a *separate* `paths-filter` step with `predicate-quantifier: every` and a positive `'**'` entry followed by one `!`-prefixed exclusion per excluded glob — data-model.md's Path Category "Corrections" note walks through why two earlier, plausible-looking forms (a single `!(a/**|b/**|...)` extglob string, then the same list form under the *default* quantifier) both silently matched everything anyway |

**Rationale**: `docs` job's dependency on Python source (docstrings feed the Sphinx build,
per spec.md Assumptions) is expressed as `needs.changes.outputs.python == 'true' ||
needs.changes.outputs.docs == 'true'` in that job's own `if:`, rather than folding `src/**`
into the `docs` filter itself — keeping each named filter a disjoint, single-purpose glob set
that mirrors one category, with the *job* being the place multiple categories combine. This
avoids the alternative of overlapping filters (`docs` filter itself containing `src/**`),
which would make the mapping harder to audit at a glance in the new static test.

`other` exists solely to satisfy FR-003 (never silently under-cover an unanticipated path) —
any file (a new top-level dotfile, a renamed directory) that matches none of `python`/`docs`/
`ci_config` sets `other: true`, and every filtered job's `if:` ORs in `other` so it runs
unconditionally for such a change.

## 3. `ci-ok`'s pass/fail predicate

**Decision**: Change the embedded Python assertion in `ci-ok`'s step from:

```python
failures = {name: r for name, r in needs.items() if r.get("result") != "success"}
```

to:

```python
failures = {name: r for name, r in needs.items() if r.get("result") not in ("success", "skipped")}
```

**Rationale**: This is the direct implementation of FR-005 and spec.md's clarified SC-001/
SC-002 split — a job intentionally skipped by path selection must read as non-blocking, while
`failure` and `cancelled` still fail `ci-ok` exactly as today. This is a one-line, narrowly
scoped change to an already-tested assertion (`tests/static/
test_ci_ok_aggregate_check.py::test_ci_ok_actually_asserts_its_dependencies` already pins the
presence of `sys.exit(1)` and `NEEDS_JSON`; the new static test module adds a case asserting
`"skipped"` is accepted and `"failure"`/`"cancelled"` are not).

**Alternative considered**: Leave `ci-ok`'s predicate unchanged and instead make every
filtered job report `success` (e.g., a trivial passing step) instead of `skipped` when path
selection excludes it. Rejected: this is strictly worse for FR-008 (the `quality-summary`
comment already has a `skipped` case in its `status_label()` function specifically to render
this state distinctly — see #4 below) and it would misrepresent, to any human or tool reading
the Actions UI, that a job ran and passed when it did not run at all.

## 4. `quality-summary`'s rendering of skipped jobs

**Finding, not a decision**: No change needed. `quality-summary`'s `status_label()` bash
function (`ci.yml`, Build summary step) already maps `skipped` → `⏭️ skipped`, distinct from
`success`/`failure`/`cancelled`, because a job can already be skipped today for unrelated
reasons (e.g. a cancelled workflow run leaving downstream jobs unskipped-but-never-started).
FR-008 is therefore already satisfied by existing code — confirmed by reading the function
rather than assumed, since specs/004's own contract predates this feature and could plausibly
have missed this case.

## 5. Fail-open behavior when the `changes` job itself fails

**Decision**: This is the central correctness risk this feature introduces, with no existing
precedent in this repo to copy verbatim (the closest analog, the `performance` job's
`continue-on-error: true`, solves a different problem — a job that ran and failed staying
non-blocking, not a job that never got the chance to run). Every filtered job's `if:` MUST
explicitly override GitHub Actions' implicit `success()`-gating with `!cancelled()` (the same
idiom already used in this file for the `performance` job's summary step), and MUST OR in
`needs.changes.result == 'failure'`, e.g.:

```yaml
if: >-
  !cancelled() && github.event_name != 'schedule' &&
  (github.event_name == 'workflow_dispatch' ||
   needs.changes.result == 'failure' ||
   needs.changes.outputs.python == 'true' || needs.changes.outputs.ci_config == 'true')
```

The `github.event_name == 'workflow_dispatch'` clause is FR-006's manual-dispatch bypass, not
part of the fail-open mechanism itself — it is included in the same expression here (rather
than a separate `if:`) because both are unconditional-run overrides evaluated the same way,
and GitHub Actions has no way to compose two independent `if:` conditions on one job.

**Rationale**: GitHub Actions implicitly ANDs a bare `if:` expression with `success()` of all
listed `needs:` *unless* the expression itself contains `always()`, `cancelled()`, or
`failure()`. Without the `!cancelled()` override, a `changes` job failure (a bad pin, an
upstream `dorny/paths-filter` outage, a malformed glob) would cause every downstream filtered
job to be silently skipped rather than run — and skipped jobs are exactly the case FR-005/
decision #3 above just taught `ci-ok` to treat as non-blocking. Left unaddressed, this
feature would hand a future filter-mechanism outage the exact "decorative guard" failure mode
`code-review/SKILL.md` §7a bands CRITICAL: `ci-ok` goes green while no quality gate actually
ran. Failing open (running the job anyway when the filter is broken) is the same
"default to running when uncertain" principle FR-003 already applies to unmatched paths,
applied to mechanism failure instead of path novelty.

`changes` itself is added to `ci-ok`'s `needs:` list and to `tests/static/
test_ci_ok_aggregate_check.py`'s `REQUIRED_JOBS` (not `SUPPORTING_JOBS`): unlike `performance`
or `quality-summary`, a failed `changes` job is a real signal that the filtering mechanism
broke, and `changes` has no upstream dependency of its own, so it can only ever report
`success` or `failure` on a non-scheduled run (never `skipped`) — the uniform success-or-
skipped predicate in decision #3 is safe for it without a special case.

## 6. Documentation cross-references that go stale

**Finding**: Three existing documents assert, as current fact, that `ci-ok` blocks on *any*
non-`success` result from its dependencies — true today, no longer true once this feature
ships:

- `specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md`'s `ci-ok` row:
  "Blocks merge when: Any of the eight gating jobs failing, being cancelled, or being
  skipped."
- `.github/skills/code-review/SKILL.md` §7a and `.github/skills/pr-review-loop/SKILL.md` §5:
  both describe `ci-ok` as passing "only when all eight individually succeed."

**Decision**: Update all three as part of this feature's tasks (not deferred), since they are
direct, checkable claims this feature makes false the moment `ci.yml` merges — the same
"artifacts must match the code" discipline slice 015 applied retroactively
(specs/015-console-i18n-relocation, `/speckit-converge` findings). `tests/static/
test_ci_ok_aggregate_check.py`'s own docstring on `test_ci_ok_only_excludes_scheduled_runs`
needs the same treatment: its stated rationale ("the assertion step sees 'skipped' and fails")
is no longer why `ci-ok` must exclude scheduled runs — that exclusion is now justified purely
by "no pull request exists to gate on a schedule run," not by the assertion's predicate — but
the assertion (`ci-ok` must still exclude `schedule`) is unchanged and the test itself needs
no new assertion, only a corrected comment.

## 7. Matrix-job (`test`) granularity

**Decision**: Path selection applies to the `test` job as a whole (all four
Python-version matrix legs together), not per-leg.

**Rationale**: Matches spec.md FR-002's job-level framing and Key Entities (job-to-category
mapping is per named job, `test` is one job with a matrix strategy). Per-leg selection would
require the filter decision to flow into `strategy.matrix` itself, adding real complexity for
no benefit this spec asks for — a change to `src/**` needs every supported interpreter to run
regardless of which specific file changed.
