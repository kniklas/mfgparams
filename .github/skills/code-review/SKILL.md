---
name: code-review
description: Repo-specific context for GitHub Copilot code review on mfgparams pull requests. Applies constitution-derived checks around calculation correctness, resource-constrained hardware limits, packaging conventions, and lint/type/test gates whenever reviewing changes in this repository.
---

# Code Review Skill (mfgparams)

Use this skill whenever reviewing a pull request in this repository. It
gives Copilot code review repo-specific context beyond generic best
practices: this project's constitution
(`.specify/memory/constitution.md`), CI gates, and conventions in
`.github/instructions/python.instructions.md`.

## 1. Priorities, in order

1. **Calculation correctness** — this is a metal-machining calculation
   library; a wrong number is worse than a crash or a missing feature.
2. **Resource-constrained compatibility** — the tool must run on old,
   low-power hardware (single core, ~64-128 MB RAM).
3. **Test coverage and regression safety.**
4. **Extensibility** — new operations/units must not require rewriting
   shared infrastructure.
5. Style/lint/type issues (already enforced by CI; flag only if CI would
   miss them, e.g. logic hidden inside a string or comment).

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
- A supporting/non-required job (see this repo's required-jobs list:
  `lint`, `complexity`, `typecheck`, `security`, `dependency-scan`,
  `test`, `build`, `docs`, CodeQL) must never become a de facto blocker
  through an aggregate/wrapper check that can't complete until it does.

## 8. Cross-referencing issues

If the PR description references a GitHub issue (e.g. `Fixes #23`),
confirm the diff actually satisfies that issue's stated acceptance
criteria/suggested fix — not just a partial or superficial mitigation.
