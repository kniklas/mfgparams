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

**Known limitation, accepted rather than designed around**: on `pull_request` events,
`dorny/paths-filter` reads the changed-file list from GitHub's REST API, which is documented
to paginate/truncate on an unusually large file count (dorny/paths-filter upstream issue
#227). A truncated list would make `changes` report `success` with incomplete category
outputs rather than `failure`, so the fail-open clause (decision #5) would not trigger, and a
file outside the truncated page could silently skip a job that should have run for it.
Switching `pull_request` mode to the same git-based diffing `push` already uses (decision #1's
checkout) would close this, but needs its own careful base-ref resolution for merge commits
and is not worth the added complexity for a small, single-maintainer library repository where
a pull request touching enough files to hit this limit has never occurred and is not
anticipated (flagged by a local code-review pass on PR #89; not adopted as a fix).

## 2. Path category → glob mapping

**Decision**: Originally four named categories, matching spec.md's Assumptions section
exactly; Copilot's round-2 review of PR #89 found two of those Assumptions false (see
data-model.md's Path Category Corrections note #4) and added two more, narrower categories to
fix them without giving up the skip for everything else under those same paths — six today:

| Category | Globs |
|---|---|
| `python` | `src/**`, `tests/**`, `pyproject.toml`, `tox.ini`, `scripts/sync_agent_integrations.py`, `scripts/setup_skill_symlinks.py` |
| `docs` | `docs/**` |
| `ci_config` | `.github/workflows/**` |
| `skills` | `.github/skills/**`, `.claude/**` — read only by `lint` (`setup_skill_symlinks.py --check`) |
| `packaging_metadata` | `README.md`, `LICENSE.md` — read only by `build` (`pyproject.toml`'s `readme`/`license-files`) |
| `other` (catch-all) | Everything not matched by any named filter above **or** by the known-non-code paths in spec.md's Assumptions (`specs/**`, root `*.md` other than `README.md`/`LICENSE.md`), via a *separate* `paths-filter` step with `predicate-quantifier: every` and a positive `'**'` entry followed by one `!`-prefixed exclusion per excluded glob — data-model.md's Path Category "Corrections" note walks through why two earlier, plausible-looking forms (a single `!(a/**|b/**|...)` extglob string, then the same list form under the *default* quantifier) both silently matched everything anyway. `.github/skills/**`/`.claude/**`/`*.md` stay in `other`'s exclusion list even though `skills`/`packaging_metadata` now separately depend on some of those same globs — they are still "named and handled elsewhere," not unanticipated. |

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
broke. On `push`/`pull_request` it can only report `success` or `failure` — the uniform
success-or-skipped predicate in decision #3 is safe for it without a special case there. On
`workflow_dispatch` it reports `skipped` instead (added after Copilot's round-2 review of PR
#89: `changes` originally still ran, and could fail, on manual dispatch even though every
filtered job already bypasses its output for that trigger — see decision #5's example and
`contracts/path-selection-contract.md`'s Manual-dispatch bypass contract), which decision #3's
predicate already treats as non-blocking.

## 6. Documentation cross-references that go stale

**Finding**: Several existing documents assert, as current fact, claims this feature makes
false the moment `ci.yml` merges:

- `specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md`'s `ci-ok` row: "Blocks
  merge when: Any of the eight gating jobs failing, being cancelled, or being skipped" — no
  longer true (skipped is non-blocking), and its job count is stale twice over (nine after
  `changes`, ten after `repo-invariants`).
- `.github/skills/code-review/SKILL.md` §7a and `.github/skills/pr-review-loop/SKILL.md` §5:
  both describe `ci-ok` as passing "only when all eight individually succeed" (same two
  problems).
- `specs/013-tox-multi-python-testing/spec.md`'s FR-005/FR-007 and SC-003/SC-004: each asserts
  the full Python-version matrix runs, and is required, "on every pull request" — this
  feature's `test` category makes that conditional on path (a specs-only or non-packaging
  `*.md`-only pull request now skips `test` entirely). Missed in this document's first pass
  (Copilot's round-3 review of PR #89 caught the omission); qualified in place in specs/013's
  spec.md rather than rewritten, per the pattern below.

**Decision**: Update all of the above as part of this feature's tasks (not deferred), since
they are direct, checkable claims this feature makes false — the same "artifacts must match
the code" discipline slice 015 applied retroactively (specs/015-console-i18n-relocation,
`/speckit-converge` findings). The `ci-checks-contract.md`/`code-review`/`pr-review-loop` trio
gets its numbers and predicate description corrected outright, since they describe *current*
mechanics. specs/013's spec.md is historical record for an already-shipped feature, so its
FR-005/FR-007/SC-003/SC-004 keep their original text with a short "Qualified by
`specs/016-ci-path-based-selection`" note appended to each, rather than being rewritten to
describe this feature's behavior directly — the same treatment `ci-checks-contract.md`'s own
`test` row already gives a prior supersession ("~~`test`~~ — superseded by
`013-tox-multi-python-testing`"). `tests/static/test_ci_ok_aggregate_check.py`'s own docstring
on `test_ci_ok_only_excludes_scheduled_runs` needs the same treatment: its stated rationale
("the assertion step sees 'skipped' and fails") is no longer why `ci-ok` must exclude
scheduled runs — that exclusion is now justified purely by "no pull request exists to gate on
a schedule run," not by the assertion's predicate — but the assertion (`ci-ok` must still
exclude `schedule`) is unchanged and the test itself needs no new assertion, only a corrected
comment.

## 7. Matrix-job (`test`) granularity

**Decision**: Path selection applies to the `test` job as a whole (all four
Python-version matrix legs together), not per-leg.

**Rationale**: Matches spec.md FR-002's job-level framing and Key Entities (job-to-category
mapping is per named job, `test` is one job with a matrix strategy). Per-leg selection would
require the filter decision to flow into `strategy.matrix` itself, adding real complexity for
no benefit this spec asks for — a change to `src/**` needs every supported interpreter to run
regardless of which specific file changed.

## 8. `repo-invariants`: a job that is never filtered

**Decision**: Add a new, always-on `repo-invariants` job (`needs: []`, no category-based
`if:`) that reruns `tests/static/test_no_old_package_name.py` and `tests/static/
test_no_old_layout.py` on every non-scheduled trigger, in addition to their normal collection
inside `test`. Added to `ci-ok`'s `needs:` alongside `changes`.

**Rationale**: Both tests walk every git-tracked file's path and content looking for a stray
reference, rather than checking anything specific to `src/**`/`tests/**`. That means a
violation can appear under `specs/**`, `.github/skills/**`, a root `*.md` file, or `.claude/**`
— every path category `test`'s `&filtered_if` condition (decision #5) is allowed to skip for.
Skipping `test` on one of those paths would therefore silently skip these two checks too — a
real regression the `test` job's own path-based skip cannot see, since path selection has no
concept of "this specific test inside the job doesn't follow the job's general rule."

**Alternatives considered**:
- Widen `test`'s trigger condition to also run for `specs/**`/`.github/skills/**`/`*.md`/
  `.claude/**`: rejected — `test` collects roughly 1100 other, genuinely path-scoped tests, and
  this would mean `test` (and therefore its four-version matrix) runs on effectively every
  pull request, defeating SC-001 for the job that costs the most CI time to run.
- Move the two tests out of `test`'s collection entirely, so they only run inside
  `repo-invariants`: rejected — `test`'s own local/pre-push runs (`pytest` with no path
  filters, `tox`) would then never exercise them, silently narrowing local verification purely
  to make CI's split cleaner. Running them twice in CI is a duplicated few hundred milliseconds
  per invocation, not a real cost, and keeps every entry point (local `pytest`, `tox`, CI)
  exercising the same test collection.
- Give `repo-invariants` a category-based `if:` mirroring `other`'s exclusions in reverse (run
  only for the paths `test` skips): rejected as needless complexity — the two tests are cheap
  enough that "always run" costs less to build, review, and keep correct than a condition
  precisely inverse to six other conditions across two `paths-filter` steps.

Found in Copilot's round-2 review of PR #89 (the third of that round's HIGH findings) rather
than during planning — the "known-non-code paths never need the toolchain" assumption in
spec.md's original Assumptions section did not anticipate a test whose scope is the whole
repository rather than a path category.
