---
name: code-review
description: Repo-specific context for GitHub Copilot code review on mfgparams pull requests. Bands every finding CRITICAL/HIGH/MEDIUM/LOW by reachability x blast radius, then applies constitution-derived checks around calculation correctness, resource-constrained hardware limits, packaging conventions, and lint/type/test gates whenever reviewing changes in this repository.
---

# Code Review Skill (mfgparams)

Use this skill whenever reviewing a pull request in this repository. It
gives Copilot code review repo-specific context beyond generic best
practices: this project's constitution
(`.specify/memory/constitution.md`), CI gates, and conventions in
`.github/instructions/python.instructions.md`.

## 0. Severity rubric — band every finding (do this first)

Every finding MUST carry exactly one of four severity bands, stated as
the first token of the finding (`CRITICAL:` / `HIGH:` / `MEDIUM:` /
`LOW:`). The test is **reachability × blast radius** — how a real user or
agent hits it and what it costs when they do — **not** how hard the
finding is to fix, and not how confident you are that it is real.

`pr-review-loop` §1 sets a severity floor per review intensity and uses
these bands to decide what gets fixed inside the review loop and what is
deferred. A finding reported without a band cannot be triaged, so it is
treated as sitting **at the floor** — it gets fixed. Never default an
unbanded finding to LOW: a forgotten prefix on a real defect must not
silently discard it.

### CRITICAL

The change is fundamentally broken in its own stated purpose, or breaks
existing callers/users on an ordinary path.

- Wrong calculation output on nominal, documented inputs.
- A gate/check that cannot fail when it should (the guard is decorative).
- Silent breaking change to a public signature or CLI contract — no
  error, just different behavior.
- Data loss, or destruction of a user's existing file.

> **#42:** milling mode args inserted before `materials_config_path` —
> every existing 0.3 positional caller now passes a config path as
> `mode`, silently.
> **#24:** the performance step stays `continue-on-error` and is excluded
> from `quality-summary`, so the invalid-memory verdict the PR was built
> to enforce blocks nothing.

### HIGH

The code does not satisfy a stated requirement (a spec FR, a contract, an
issue acceptance criterion), reachable by a normal user or agent without
contrivance.

- Documented behavior contradicted by the implementation.
- Validation bypassed, or applied in the wrong order, on a reachable path.
- An error or unmeasurable state fabricated into a plausible-looking
  value (the recurring §2a pattern).
- Destructive behavior on a plausible but non-default path.

> **#42:** imperial conversion runs before validation, so `True` becomes
> `25.4` and is accepted.
> **#42:** `_prompt_mode()` accepts Enter as the current mode; FR-001a
> requires a re-prompt.
> **#30:** derived display labels collide, making a material category
> unreachable.

### MEDIUM

Rare-but-real border cases, or documentation/spec inaccuracy that will
misdirect a future agent or contributor.

- Bad input reachable only via a hand-edited config or an unusual
  platform.
- A guard that works today but is not scoped to survive a plausible
  future edit.
- **Spec-kit artifact drift** where `plan.md` / `data-model.md` /
  `tasks.md` describes a superseded mechanism — an agent reading it will
  build the wrong thing (see §6b).

> **#42:** `nan` / `inf` accepted for `cutting_speed_factor` from a
> hand-edited TOML.
> **#71:** `plan.md` and `data-model.md` still describe the discarded
> 3.11-gated `coverage_pct` design.
> **#71:** the version-consistency guard is not scoped to `jobs.test`, so
> a matrix added above it defeats FR-008.

### LOW

Cosmetic, or a border case so remote it needs a hostile constructed
input. No effect on any user, and no effect on how an agent builds.

- Comment or prose inaccuracy with no behavioral or directive content.
- Stale counts in a PR description.
- Denormal/overflow edge cases at the arithmetic limits.

> **#42:** `target_rpm=5e-324` underflows the feed rate.
> **#42:** a comment in `tools.toml` says carbide-first while HSS is
> listed first.
> **#50:** `"Use 'for' rather than 'or'"`; a PR body claiming 17 tests
> where the file has 21.

### What a band does — the floor decides, not this section

A band never states its own intensity threshold. `pr-review-loop` §1
declares a **severity floor** per review intensity, and that table is the
single authority on what is fixed inside the loop:

- **CRITICAL** is always fixed, at every intensity, and overrides an
  exhausted budget (`pr-review-loop` §4).
- **HIGH**, **MEDIUM** and **LOW** are fixed in-loop when the band sits at
  or above the declared floor, and are otherwise deferred.

Do not restate a threshold here. One concept defined in two places is how
the two definitions drift apart.

A below-floor finding is **deferred**, not dropped: `pr-review-loop` §3a
is the exit, and it has obligations — a row in the PR's deferred-findings
comment, a tracked issue if the finding was MEDIUM, and a reply-and-
resolve on the thread. The thread obligation applies only to findings
that have one: a finding from a local review round does not, and §3a
lets a trivial one simply be fixed instead. Band accurately — the band
decides who pays for a finding and when, so a wrong band is not a
cosmetic error.

### Test policy by band

| Band | Regression test for the fix |
|---|---|
| CRITICAL | Required wherever the fix changes observable behavior — must fail before the fix, pass after. |
| HIGH | Required wherever the fix changes observable behavior — must fail before the fix, pass after. |
| MEDIUM | Required if the fix is a bug fix to calculation logic; otherwise only if cheap. |
| LOW | Not required. Below `very high` a LOW is deferred, except a trivial one found in a local round (`pr-review-loop` §3a). |

**Constitution Principle II is never overridden by this table.**
Principle II is NON-NEGOTIABLE and requires that *every* bug fix ship a
regression test that fails before the fix and passes after, and that all
calculation logic be tested. So where a finding's fix is a bug fix to
calculation logic (`src/mfgparams/**`), a failing-first regression test is
mandatory **whatever the band**. The allowances in the table exist only
for fixes that are not calculation bug fixes. When unsure which side a
fix falls on, write the test.

**"Observable behavior" is the limit on CRITICAL/HIGH, not an escape
hatch.** Some CRITICAL and HIGH findings have no surface a test can
observe — a comment or a doc contradicting the implementation, a stale
spec-kit artifact, a prose fix. Those ship without a test, and the commit
message says so explicitly. But *this repo tests more than
`src/mfgparams/**`*: `tests/static/` covers CI and workflow wiring, which
is exactly how §0's own CRITICAL exemplar (#24's `continue-on-error`
performance gate) is testable. "It's only CI config" is not a reason to
skip the test — check `tests/static/` before claiming no test can exist.

A LOW fix needs no test at any intensity — and that is a consistency
check on the banding, not an exemption carved out of Principle II: LOW
means no effect on any user and no effect on how an agent builds, so a
LOW fix has nothing a regression test could assert. If you find yourself
wanting a test for something you banded LOW, the band is wrong. Re-band
it and the row above it applies.

The band changes *whether and when* a finding is fixed. It never changes
what Principle II demands once you do fix it.

## 1. Priorities, in order — the tiebreak *within* a severity band

This list orders findings that share a band; it does not substitute for
§0's banding. Two findings both classified HIGH are addressed
calculation-correctness-first. A style nit does not outrank a
resource-limit bug because it appears lower here — it is outranked
already by being LOW. Apply §0 first, then this list inside each band.

1. **Calculation correctness** — this is a metal-machining calculation
   library; a wrong number is worse than a crash or a missing feature.
2. **Resource-constrained compatibility** — the tool must run on old,
   low-power hardware (single core, ~64-128 MB RAM).
3. **Test coverage and regression safety.**
4. **Extensibility** — new operations/units must not require rewriting
   shared infrastructure.
5. Style/lint/type issues (already enforced by CI; flag only if CI would
   miss them, e.g. logic hidden inside a string or comment).

Before this list, §0 has already answered the question this ordering
cannot express on its own: *is this finding worth a review round at all?*

## 2. Calculation correctness (Constitution Principles I & III)

Flag any of the following in changed calculation code
(`src/mfgparams/**`, especially `operations/*/formulas.py`):

- Floating-point equality checks using `==` instead of `math.isclose` (or
  an explicit tolerance).
- Missing input validation (type/range/unit) before a value is used in a
  formula — invalid input must raise a clear, actionable error, never
  silently produce a wrong number.
- Unhandled edge cases: division by zero, negative square roots, zero/empty
  inputs, unit mismatches.
- A formula or constant taken from an external standard/reference without a
  code comment citing that source.
- A public calculation function without a docstring documenting inputs,
  outputs, units of measurement, and valid ranges.
- Magic numbers with physical/mathematical meaning that aren't named or
  explained.

## 2a. Error/unmeasurable-state handling (generalized from issue #23)

This pattern has recurred repeatedly (PRs #19, #21, #24) beyond just the
performance harness — flag it anywhere a value can fail to be
determined, not only in `tests/performance/harness.py`:

- Any function that measures, reads, or parses a value that can fail,
  time out, be unsupported on a platform, or be unavailable in the
  current environment MUST represent that as an explicit sentinel (e.g.
  `None`, a dedicated `Unmeasured`/`Invalid` enum member, or a
  `measured: bool` flag) — never a fabricated `0`, `0.0`, or negative
  number standing in for "couldn't determine this."
- That sentinel MUST survive every layer it passes through (raw
  reading → report/result object → aggregation → CI script output →
  displayed summary). Flag any point where the sentinel gets coerced
  back into a real-looking number (e.g. `None` normalized to `0` for a
  numeric field, then treated as a measured zero downstream).
- A platform/environment limitation (Windows lacking `resource`, a
  container without CPU affinity support, etc.) affecting an *optional*
  measurement dimension MUST degrade to "unavailable/skipped for this
  dimension," never to an artificial pass *or* an artificial fail. This
  does not relax §3's stricter rule for *required* measurements (e.g.
  the performance suite's memory reading): if a dimension is contractually
  required to gate the result, an invalid/unavailable reading for it
  MUST still fail the case, not merely skip it — only genuinely optional
  dimensions get the skip treatment.
- When combining a partial result and an error/failure signal (e.g. "N
  cases produced a report" AND "the test step itself errored"), the
  failure signal MUST take precedence — a partial success must not mask
  a real failure.

## 3. Resource-constrained compatibility (Constitution Principle V)

This project must run within ~64-128 MB RAM on a single-threaded, low-clock
CPU, and each calculation should ideally complete within 0.5-1.0 seconds on
that hardware profile (enforced by the opt-in suite under
`tests/performance/`, budgets in `tests/performance/budgets.py`).

- New dependencies with a non-trivial runtime memory footprint (e.g. a
  numerical/data-science stack) MUST be justified in the PR description —
  flag if it's a heavy dependency (e.g. `numpy`, `pandas`, `scipy`) added
  without justification, when the standard library or a lighter dependency
  would do.
- New calculation logic that clearly can't meet the time/memory budget MUST
  document the expected runtime/rationale in the PR description.
- Any change to `tests/performance/harness.py`'s measurement/validation
  logic (child-process isolation, `ru_maxrss` handling, budget comparisons)
  is high-risk: a `0`/`None`/negative memory reading MUST always be treated
  as an invalid measurement and fail the case — never silently reported as
  a passing "0 bytes used" result. Flag any change that could reintroduce
  that class of bug (see issue #23's original symptom: `0.00s / 0MB` yet
  `pass=True`). See §2a for the generalized version of this rule.
- Any code that temporarily tightens/relaxes an OS-level resource limit
  (`resource.setrlimit`, CPU affinity masks, etc.) MUST only ever narrow
  the caller's existing constraint, never widen it (e.g. don't raise an
  already-lower soft limit to reach a requested ceiling), and MUST restore
  exactly the previous state afterward — not a hardcoded default. This
  recurred 3× across PRs #19/#21 in `harness.py`'s `RLIMIT_AS`/affinity
  handling.

## 4. Testing standards (Constitution Principle II, non-negotiable)

- Every new/changed calculation function needs unit tests covering nominal
  inputs, boundary values, zero/negative/empty inputs, and a known
  reference result.
- Bug fixes MUST include a regression test that would fail before the fix.
- Multi-step calculation pipelines (chained formulas, unit conversions)
  need integration-level coverage, not just isolated unit tests.
- Target coverage is 90% (`pyproject.toml`'s `--cov-fail-under=90`); flag
  PRs that drop coverage without justification.
- New test files under `tests/performance/` are auto-skipped by default
  (see `tests/performance/conftest.py`) — any test meant to run in the
  default/blocking suite belongs under `tests/unit/`, `tests/integration/`,
  or `tests/contract/` instead, not `tests/performance/`.

## 5. Extensibility (Constitution Principle VI)

- Operation-specific logic (e.g. drilling's spindle speed/feed/torque/power
  formulas) must live behind a per-operation module/interface
  (`operations/<name>/`), not be hard-coded into shared infrastructure
  (CLI, config loading, unit conversion, material/tool registries).
- Shared cross-cutting concerns (validation, unit conversion, error
  reporting) belong in shared components, not duplicated per operation.

## 6. Packaging & versioning (Constitution Principle IV)

- `pyproject.toml` is the single source of build/project metadata (no
  `setup.py`-only distribution); dependencies must be declared there.
- Public API changes must follow PEP 8 naming / PEP 257 docstrings.
- Breaking changes to the public API require a MAJOR version bump and a
  changelog entry.

## 6a. Derived-key/label collision and injection safety

Recurred 4-5× in one PR (#30, material-type categorization) — flag
whenever code builds a lookup/reverse-map key, or a prompt/display label,
from user-supplied or free-form config data:

- If a reverse lookup (label → canonical ID) is built from a *derived*
  display value (e.g. title-cased or translated), prove the derivation is
  collision-free or explicitly disambiguate collisions (e.g. append the
  canonical ID) — don't let a later entry silently overwrite an earlier
  one and make a category unreachable.
- Validate free-form identifiers reject line separators and C0/C1 control
  characters, not just `str.isspace()` — a TOML multiline string or an
  embedded control character can produce a prompt option that can never
  be typed back by the user (infinite re-prompt).
- Any user-supplied identifier passed through a `str.format()`-based
  translation/templating call MUST be checked for format-spec metacharacters
  (`{`, `}`) first — an ID like `"al{o}y"` or `"{{alloy}}"` can raise
  `KeyError` inside the formatting call or be silently reinterpreted,
  rather than treated as a literal fallback string.

## 6b. Spec-Kit artifact drift

Recurred across PRs #19 and #30 — when a PR changes an implementation
decision mid-development (not just what was originally planned), flag
any design/spec artifact that still describes the earlier mechanism:

- Check `research.md`, `plan.md`, `data-model.md`, `tasks.md`,
  `quickstart.md`, and the PR description itself against the final
  implementation — not just against the original plan. A changed
  mechanism (e.g. how a fallback/miss is detected) needs every artifact
  that documents *how* it works updated, not only the code and its tests.
- Stale counts/figures (test counts, file counts) repeated across
  multiple docs and the PR description are a signal the PR was edited
  after those figures were written — verify at least one against the
  actual diff/test run before trusting it.

## 7. Style conventions (`.github/instructions/python.instructions.md`)

- `black` formatting, `ruff`/`flake8` linting, `snake_case`/`PascalCase`/
  `UPPER_SNAKE_CASE` naming, grouped+alphabetized imports, f-strings over
  `%`/`.format()`.
- No bare `except:`, no mutable default arguments, no wildcard imports, no
  silent exception swallowing (`except Exception: pass`).
- Prefer `dataclasses` over manual `__init__` boilerplate for simple data
  containers.

## 7a. CI/gating logic changes (`.github/workflows/ci.yml`, `pr-review-loop`)

Recurred across PRs #19, #21, #24 (CI workflow) and #31, #35
(`pr-review-loop` skill polling its own gates) — flag any change to logic
that combines multiple signals into a single pass/fail/skip verdict:

- `continue-on-error: true` on a step MUST NOT let that step's genuine
  failure get silently reported as `skipped` or folded into an unrelated
  "no measurements" case — distinguish "didn't run" from "ran and failed."
- When a partial success (e.g. some test cases recorded a passing result)
  coexists with a harder failure signal (the test step itself erroring,
  a required job failing), the failure signal MUST take precedence in the
  combined verdict.
- A supporting/non-required job must never become a de facto blocker
  through an aggregate/wrapper check that can't complete until it does.

  **This repo now has such an aggregate.** Since #79, `main` requires only
  `ci-ok`, `Analyze (python)` and `CodeQL`; `ci-ok` expands to the eight
  gating jobs (`lint`, `complexity`, `typecheck`, `security`,
  `dependency-scan`, `test`, `build`, `docs`). Review any change to it
  against two properties, both of which fail silently — the PR just goes
  green:

  - It must `needs:` **only** those eight. `performance` is
    `continue-on-error` by design, and `quality-summary`, `deploy-docs`
    and `sync-agent-integrations` are reporting/conditional; any of them
    in `needs:` is promoted to a merge blocker.
  - It must assert each result **explicitly**. `if: always()` makes the
    job run when a dependency failed, and GitHub does not then fail it
    implicitly — an aggregate without the assertion reports success while
    `lint` is red, which is a CRITICAL-band decorative guard (§0).

  `tests/static/test_ci_ok_aggregate_check.py` locks both, and forces any
  newly-added `ci.yml` job to be classified as gating or supporting rather
  than silently neither. A change to `ci-ok` that also edits that test to
  suit itself deserves particular scrutiny.

## 8. Cross-referencing issues

If the PR description references a GitHub issue (e.g. `Fixes #23`),
confirm the diff actually satisfies that issue's stated acceptance
criteria/suggested fix — not just a partial or superficial mitigation.
