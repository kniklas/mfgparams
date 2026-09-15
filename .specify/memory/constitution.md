<!--
Sync Impact Report
==================
Version change: 1.11.0 -> 1.12.0
Modified principles: none redefined.
Added sections:
  - Principle XIII (Manual Verification for Interactive & Reference-Fidelity Features,
    NON-NEGOTIABLE) — new principle. First bullet: a feature whose correctness depends on
    how it looks/behaves to a human (an interactive console/TUI or GUI surface) MUST NOT be
    marked complete on automated tests alone — `tasks.md` MUST carry a distinct, named
    manual-walkthrough item (developer/reviewer-performed when the agent has no real
    terminal/display access), e.g. walking `quickstart.md` against a real terminal/display,
    separate from test tasks; a passing
    test suite MUST NOT be treated as evidence a rendering/interaction detail (color,
    position, focus highlighting, shading, layout) is correct. Second bullet: a claim that
    reference material a feature must match (a prototype, mockup, screenshot, prior
    discarded code) is unavailable/lost/superseded MUST be verified against the actual
    current filesystem/repository state when written, not carried forward from a prior
    session's memory; if the artifact does exist, its literal content MUST be read and
    cited before any prose paraphrase of its behavior is written into a spec.
Expanded sections: Development Workflow (Review Process) — reviewer checklist gains item (5),
  requiring confirmation that a Principle XIII manual-verification task was actually completed
  (see Correction 5 below for why this item exists but was missing from this line originally).
Removed sections: none
Rationale: specs/018-tui-splitpane-redesign needed two full implementation passes rejected
  outright by the user before a third, prototype-fidelity rewrite finally matched, plus 8
  further user-reported correction rounds after that rewrite was itself marked "done" — all
  invisible to a fully green CI run throughout. Root causes, per the retrospective posted to
  PR #96 (https://github.com/kniklas/mfgparams/pull/96#issuecomment-5637032822): (a) the
  spec's own Carried-Over Items section asserted the pre-plan prototype scripts were
  "discarded", a claim never checked against the filesystem — the scripts were on disk the
  whole time, at a known path, and two implementation passes were built from prose
  descriptions of them instead of their actual source; (b) this codebase's TUI test
  strategy (`DummyOutput`-based, state/text-only assertions) structurally cannot detect a
  color, layout, shading, or focus-highlight regression, so "tests pass" repeatedly gave
  false confidence that a feature depending on exactly those properties was done; (c) the
  one gate that could have caught most of this — a human looking at the running app — never
  ran before the feature was first declared complete, only afterward, one round at a time,
  in direct user feedback. This principle makes both failure modes structurally checkable
  (a required, named tasks.md item; a required verification step) rather than relying on
  an agent's memory or assumption holding true across a long, possibly-compacted session.
MINOR rather than PATCH: this is new, materially expanded guidance — an explicit manual-
  verification gate and a reference-material-verification requirement did not exist in any
  prior version — not a wording clarification of existing guidance.
Templates requiring updates:
  OK .specify/templates/tasks-template.md (gained a named, REQUIRED manual-verification task
     slot in the Polish phase for interactive/rendering features, distinct from test tasks.
     `/speckit-constitution`'s own Scope Guard did not do this — its automated scope stays
     limited to this file — so it was done as a separate, explicit hand-edit alongside the
     constitution edit in this same PR. That is the Governance section's "explicit follow-up
     step" (deliberate, verified action) rather than the "assumed to happen automatically"
     case that sentence rules out; it is not one of the generated per-agent artifacts
     Principle XI forbids hand-patching (`.claude/skills/*`, `.github/agents/*`, etc.) —
     tasks-template.md is a hand-authored Spec Kit customization point)
  OK .specify/templates/plan-template.md (no changes needed — Constitution Check section
     already surfaces any principle by name during `/speckit-plan`)
  OK .specify/templates/spec-template.md (no changes needed)
  OK .github/copilot-instructions.md (no changes needed — does not enumerate principles)
Propagation: tasks-template.md updated in this same change (see above). Still deferred, as a
  separate future decision (not tracked as a Next Action of this amendment specifically): a
  possible `/speckit-clarify`/`/speckit-plan` checklist item for reference-material
  verification, and a possible design-before-build step for net-new UI surfaces with no
  existing exact reference — both flagged as options by the PR-96 retrospective and left
  open.
Follow-up TODOs: none — see Correction 3 below (the representative-spec check the Governance
  section requires when there is no directly affected spec, run and passed before merge).
Correction 1 (same PR, before merge - not a separate version bump): the Templates requiring
  updates / Propagation text above originally (as first pushed on this PR) said the
  tasks-template.md slot was not yet applied and was tracked as a future Next Action; it was
  in fact applied in the same commit, and the report was inaccurate about its own change. A
  local code-review pass caught the mismatch before merge; corrected in place per the same
  precedent as the v1.11.0 amendment's own correction note above, since this is still the
  v1.12.0 draft landing, not a change to an already-released version.
Correction 2 (same PR, before merge - not a separate version bump): the Governance section's
  paragraph on propagating amendments (pre-existing text, not otherwise touched by this
  amendment) stated that both `.specify/templates/*` and generated per-agent instruction
  files "remain generated artifacts of the Spec Kit integration mechanism, never hand-patched
  directly (Principle XI)", then two sentences later instructed reconciling
  `.specify/templates/*` content manually — a direct self-contradiction, and also a
  misstatement of Principle XI itself, which (see its own text above) designates
  `.specify/templates/*` as a customization point meant to be hand-patched and restricts only
  generated per-agent files. A local code-review pass on this PR caught it while reviewing
  this same paragraph's applicability to the tasks-template.md edit above; corrected in place
  to match Principle XI, under the same before-merge precedent as Correction 1.
Correction 3 (same PR, before merge - not a separate version bump): the Follow-up TODOs above
  originally deferred the Governance section's required `/speckit-analyze`-or-equivalent
  check entirely, reasoning this amendment has no directly affected spec of its own — but the
  Governance section explicitly anticipates exactly that case by offering a *representative*
  spec as the alternative, so skipping the check was wrong; Copilot review on this PR caught
  it. `specs/018-tui-splitpane-redesign` — the spec this principle's own rationale cites as
  the motivating incident, and the more recent of the two — has only `spec.md` (no
  `plan.md`/`tasks.md`), so the required `tasks.md` check is not possible against it. Run
  instead before merge against `specs/017-console-text-gui` (the next most recent spec
  sharing Principle XIII's subject matter, an interactive TUI feature, with a complete
  spec/plan/tasks triplet): its `tasks.md` T037 ("Run every scenario in quickstart.md
  manually, end-to-end, on a real terminal") already is a distinct, named manual-verification
  task separate from its automated test tasks — no conflict with Principle XIII's wording
  found, and no remediation needed on that spec.
Correction 4 (same PR, before merge - not a separate version bump): the required
  tasks-template.md task added by this amendment (see the diff above) named only the
  interactive-console/TUI/GUI case, omitting Principle XIII's other, equally-required case —
  a change claiming to match an external reference exactly (constitution.md's own Principle
  XIII text above covers both from its first sentence). A feature generated from the
  pre-correction template that was reference-fidelity but non-interactive could therefore
  satisfy the letter of the template while skipping the principle's actual requirement.
  Copilot review on this PR caught it; the task now names both cases with a verification
  method for each.
Correction 5 (same PR, before merge - not a separate version bump): this amendment added
  item (5) to the Development Workflow reviewer checklist (requiring reviewers to confirm a
  Principle XIII task was actually completed, not just present) but the Sync Impact Report
  above originally said "Expanded sections: none" — the same class of self-referential
  reporting gap Correction 1 already caught once in this PR. A local code-review pass caught
  it; the "Expanded sections" line now names the checklist change.
Correction 6 (same PR, before merge - not a separate version bump): the required
  tasks-template.md task (see Correction 4) was written as a multi-line checklist item with
  nested sub-bullets for its two cases, and its own trailing prose referenced a specific
  illustrative sample task ("Run quickstart.md validation") by name — but
  `.github/agents/speckit.tasks.agent.md`'s Checklist Format (REQUIRED) section mandates every
  generated task be a single line, and that sample task is itself one `/speckit.tasks` is
  instructed to discard, so neither would have survived generation intact: the two-case split
  would be collapsed away and the cross-reference would dangle. A local code-review pass
  caught both; the task is now a single compliant checklist line, with the two-case detail
  moved into an adjacent NOTE (not itself a checklist item, so not subject to the single-line
  rule) that the EXCEPTION carve-out above now also names explicitly as required to keep.
-->

<!--
Sync Impact Report (previous amendment)
==================
Version change: 1.10.1 -> 1.11.0
Modified principles: Principle IX gains a new bullet (path-based job selection exception),
  inserted immediately after its intro sentence. Its bandit bullet is amended to qualify
  "every pull request" by that exception. Additional Constraints' two bullets naming
  lint/typecheck/test/build/docs directly, plus the bullet naming the Principle IX gates
  (complexity/MI/security/dependency-scan/CodeQL), are amended the same way for the gates
  this exception actually covers. Principle II's "Test suites MUST run in CI on every pull
  request" bullet is qualified the same way (Copilot round-8 CRITICAL finding on PR #89:
  `test` is one of the seven path-filtered jobs, so this bullet's unqualified "every pull
  request" was left in direct conflict with the exception this same amendment introduces -
  missed in the original pass because Principle IX's own gates, not Principle II, were what
  /speckit-analyze flagged).
Rationale: /speckit-analyze on feature 016-ci-path-based-selection (specs/016-ci-path-based-
  selection/) found this constitution's literal, repeated "every pull request" language in
  direct textual conflict with that feature's entire purpose - conditionally skipping
  `lint`/`complexity`/`typecheck`/`security`/`test`/`build`/`docs` for pull requests touching
  no path any of those gates could plausibly affect (e.g. a specs-only or docs-only PR). The
  new exception is written to require exactly the safeguards that feature's own design
  already includes - default-run whenever a changed path isn't recognized by the mapping,
  fail-open if the path-selection mechanism itself breaks, and automated enforcement of both
  plus the mapping's composition - so this codifies an existing, carefully-scoped design
  rather than inventing new requirements or loosening anything for a pull request that does
  touch in-scope files. `dependency-scan`/`pip-audit` and CodeQL are deliberately NOT
  qualified: 016 does not filter either job (FR-006), so their literal "every pull request"/
  "continuously" wording remains true and unqualified in every bullet that names them,
  including the Additional Constraints bullet that groups them with complexity/MI/security -
  only the complexity/MI/security portion of that bullet is qualified, verified deliberately
  (not assumed) while drafting this amendment.
MINOR rather than PATCH: this is new, materially expanded guidance - a conditional-execution
  exception with its own four-part safeguard requirement did not exist in any prior version -
  not a wording clarification of existing guidance.
Templates requiring updates:
  OK .specify/templates/plan-template.md (no changes needed)
  OK .specify/templates/tasks-template.md (no changes needed)
  OK .specify/templates/spec-template.md (no changes needed)
  OK .github/copilot-instructions.md (no changes needed - does not enumerate CI job names)
Propagation: specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md's `ci-ok` row,
  .github/skills/code-review/SKILL.md §7a, and .github/skills/pr-review-loop/SKILL.md §5 all
  currently describe pre-016 `ci-ok` semantics; already tracked as tasks T022-T024 in
  specs/016-ci-path-based-selection/tasks.md - not duplicated as a follow-up here.
Follow-up TODOs:
  - Run /speckit-analyze again against specs/016-ci-path-based-selection once this amendment
    is committed, to confirm the constitution-conflict finding (C1) is resolved and no new
    conflict was introduced by this wording.
Correction (same PR, before merge - not a separate version bump): the path-based job
  selection bullet above originally said a gate "MAY be limited to pull requests," but
  specs/016-ci-path-based-selection's actual design applies the exception to `push` runs too
  (main's post-merge CI), matching Additional Constraints' pre-existing "every push/pull
  request" scope. A local code-review pass on PR #89 caught the mismatch before merge; fixed
  in place by saying "pull requests or pushes" throughout the bullet, since this is still the
  v1.11.0 draft landing, not a change to an already-released version.
-->

<!--
Sync Impact Report (previous amendment)
==================
Version change: 1.10.0 -> 1.10.1
Modified principles: none redefined. Principle IX's required-status-check clause, the
  Additional Constraints echo of it, and the Development Workflow echo of it are
  clarified to say the gates MUST *gate* `main`, directly or through a conforming
  aggregate check - rather than each appearing in the ruleset under its own name.
Rationale: PR #79 (issue #75 P2.4) migrated `main`'s ruleset from 13 individually-named
  contexts to three (`ci-ok`, `Analyze (python)`, `CodeQL`). Every Principle IX gate
  still blocks a merge - `ci-ok` depends on all eight and asserts each result - but the
  three clauses above, read literally, said the individual checks must each be configured
  as required status checks, which is no longer true. Left unamended, a future
  contributor reading the constitution as authoritative would "restore" the per-job
  ruleset and reintroduce exactly the churn #79 removed (#71's rename cost three commits
  and still missed a file until review round 5 of 10).
PATCH rather than MINOR: what is required is unchanged - every gate must still block a
  merge, and bypass is still limited to the review-approval gate. Only the permitted
  *mechanism* for wiring them to the branch is stated more precisely. The new
  MUST NOT clauses (an aggregate may neither enlarge nor shrink the gate, and its
  composition must be automatically enforced) restate constraints Principle IX already
  implied; they are written down because #79 showed both failure modes are silent.
Templates requiring updates:
  OK .specify/templates/plan-template.md (no changes needed)
  OK .specify/templates/tasks-template.md (no changes needed)
  OK .specify/templates/spec-template.md (no changes needed)
  OK .github/copilot-instructions.md (no changes needed - does not enumerate check names)
Propagation done in the same change (PR #79): README.md, .github/pull_request_template.md,
  specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md,
  .github/skills/code-review/SKILL.md §7a, .github/skills/pr-review-loop/SKILL.md §5.
  Enforcement of the aggregate's composition: tests/static/test_ci_ok_aggregate_check.py.
Follow-up TODOs:
  - Run /speckit-analyze against a representative in-flight spec per the Governance
    section's amendment-propagation requirement. Not run here: this is a wording
    clarification with no affected feature spec/plan/tasks of its own.
-->

<!--
Sync Impact Report (previous amendment)
==================
Version change: 1.9.1 → 1.10.0
Modified principles: none (all existing principles unchanged)
Added sections:
  - Principle XII (Long-Lived Feature Branches for Multi-PR Work) — new principle defining
    how to develop a feature too large/risky for one pull request: use a long-lived
    integration branch (a numbered feature branch, explicitly created — since
    `/speckit-specify`'s branch-creation hook is optional and not guaranteed to run) rather
    than `main`, target sub-PRs at that branch under the same two separate branch-protection
    rulesets `main` uses (status-checks, no-bypass; PR-review, owner-only bypass) and
    identical CI/review gates, reconcile with `main` incrementally (merge `main` in, or
    rebase the integration branch onto `main` — never the reverse), and only merge to
    `main` once the full feature's tasks are complete, tests pass, and `/speckit-converge`
    confirms the implementation matches spec/plan/tasks, followed by branch cleanup.
Expanded sections: none
Removed sections: none
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (no changes needed)
  ✅ .specify/templates/tasks-template.md (no changes needed)
  ✅ .specify/templates/spec-template.md (no changes needed)
  ⚠️ .github/copilot-instructions.md (needs reconciliation — its "Spec Kit workflow"
     section currently describes `speckit.specify` as creating feature branches
     automatically; Principle XII now states branch creation is optional/hook-gated and
     MUST be done explicitly. Per Principle XI this file is a generated integration
     artifact and MUST NOT be hand-patched here; regenerate/reconcile it via the normal
     Spec Kit integration mechanism as a follow-up, not within this constitution-only PR.)
Follow-up TODOs:
  - Reconcile `.github/copilot-instructions.md`'s branch-creation description with
    Principle XII (see ⚠️ row above).
  - Run `/speckit-analyze` (or an equivalent cross-artifact consistency check) against a
    representative in-flight spec per the Governance section's amendment-propagation
    requirement; not run as part of this amendment since it introduces a new governance
    principle with no directly affected feature spec/plan/tasks of its own.
-->

<!--
Sync Impact Report (previous amendment)
==================
Version change: 1.9.0 → 1.9.1
Modified principles: Principle XI (Multi-Agent Coding-Tool Consistency) — wording-only
  clarification within the v1.9.0 "genuinely shared, hand-authored skills" exception
  bullet; no normative change.
Added sections: none
Expanded sections: none
Wording clarifications:
  - Principle XI's exception bullet and rationale sentence said the shared skill is a
    single canonical "file" referenced via a symlink "to the canonical file", and that it
    "remains one physical file with no possibility of drift". The actual mechanism (and
    this repo's own `scripts/setup_skill_symlinks.py` implementation, merged on the same
    branch) symlinks the whole skill *directory* (`.github/skills/<name>/`, holding
    `SKILL.md` plus any supporting files) — a file-level symlink at `.claude/skills/<name>`
    would not even be discoverable, since Claude Code looks for
    `.claude/skills/<name>/SKILL.md`. Reworded the three occurrences of "file"/"canonical
    file" to "directory"/"canonical directory" so the text accurately describes what is
    shared, and so a future contributor doesn't read "one physical file" as meaning only
    `SKILL.md` is shared while supporting files under the directory are not. What is
    permitted/required/forbidden is unchanged.
Removed sections: none
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (no changes needed)
  ✅ .specify/templates/tasks-template.md (no changes needed)
  ✅ .specify/templates/spec-template.md (no changes needed)
  ✅ .github/copilot-instructions.md (no changes needed)
Follow-up TODOs: none
-->

<!--
Sync Impact Report (previous amendment)
==================
Version change: 1.8.0 → 1.9.0
Modified principles: Principle XI (Multi-Agent Coding-Tool Consistency) — added a scoped
  exception bullet; the principle's core anti-duplication MUST clauses are otherwise
  unchanged.
Added sections: none
Expanded sections:
  - Principle XI: added an "Exception — genuinely shared, hand-authored skills" bullet.
    A repo-specific skill that is hand-authored outside the Spec Kit integration mechanism
    (i.e., not produced by `specify integration install`/`specify integration upgrade`) but
    genuinely useful to more than one coding agent MAY live as one canonical file in a
    single agent's own skill directory; every other agent's directory MAY reference it only
    via a symlink to that canonical file, never a hand-copied/independently-edited
    duplicate. Motivated by this repo's own `.github/skills/*` (Copilot-facing, hand-
    authored skills such as `pr-review-loop`, `code-review`, `pypi-package-builder`,
    `skill-authoring`) becoming reusable from Claude Code via `.claude/skills/*` symlinks —
    the principle's literal prior wording forbade this even though a symlink cannot
    independently diverge from its target and so cannot produce the drift the principle
    exists to prevent. Rationale paragraph expanded with one sentence explaining why the
    exception preserves the principle's guarantee rather than weakening it. (The "file" vs
    "directory" wording in this summary is corrected by the v1.9.1 report above; the
    original v1.9.0 amendment text below is left as historical record.)
Removed sections: none
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (no changes needed)
  ✅ .specify/templates/tasks-template.md (no changes needed)
  ✅ .specify/templates/spec-template.md (no changes needed)
  ✅ .github/copilot-instructions.md (no changes needed)
Follow-up TODOs: none
-->

# machine-calc Constitution

## Core Principles

### I. Code Quality
All code merged into this repository MUST be readable, maintainable, and consistent.
- Every module, function, and calculation routine MUST have a single, clear responsibility;
  no god-functions mixing input parsing, calculation, and presentation logic.
- Public functions and calculation entry points MUST be documented with inputs, outputs,
  units of measurement, and valid ranges.
- Linting/formatting tools MUST be configured (e.g., ruff/flake8 + black or an equivalent
  formatter) and MUST pass in CI before merge; style violations are not acceptable
  trade-offs for speed.
- Static type checking (e.g., `mypy`) MUST be configured and MUST pass in CI; new or
  changed code MUST NOT introduce additional type errors.
- Code reviews MUST verify naming clarity, absence of duplicated logic, and that magic
  numbers/constants tied to physical or mathematical meaning are named and explained.
- Rationale: calculation software is trusted for correctness; unreadable code hides defects
  and makes verification by reviewers or future maintainers effectively impossible.

### II. Testing Standards (NON-NEGOTIABLE)
Automated tests are mandatory for all calculation logic and MUST be written before or
alongside implementation, never deferred to "later".
- Every calculation function MUST have unit tests covering: nominal inputs, boundary values,
  zero/negative/empty inputs, and known reference results (hand-computed or from an
  authoritative source).
- Bug fixes MUST include a regression test that fails before the fix and passes after.
- Integration tests MUST cover any multi-step calculation pipeline (e.g., chained formulas,
  unit conversions) to confirm end-to-end correctness, not just isolated functions.
- Test suites MUST run in CI on every pull request whose changed paths are in scope for them
  (e.g., via `pytest`; subject to Principle IX's path-based job selection exception); a
  failing test suite blocks merge.
- Target minimum coverage for calculation modules is 90% line coverage; any exclusion MUST
  be justified in the pull request description.
- Rationale: calculation errors are silent and costly; only systematic, repeatable testing
  catches regressions before they reach users making real decisions from the output.

### III. Calculation Robustness & Accuracy
Numerical results MUST be correct, stable, and safe across the full range of realistic inputs.
- Floating-point operations MUST use appropriate precision for the domain; equality checks
  on floating-point results MUST use explicit tolerances (e.g., `math.isclose`), never exact
  `==` comparison.
- All calculation inputs MUST be validated (type, range, unit) before use; invalid input
  MUST produce a clear, actionable error rather than a silently wrong number or a crash.
- Edge cases (division by zero, overflow, negative square roots, empty datasets, unit
  mismatches) MUST be explicitly handled and covered by tests per Principle II.
- Any formula or constant sourced from an external standard/reference MUST cite that source
  in code comments so correctness can be independently verified.
- Rationale: this project exists to produce trustworthy machine/engineering calculations;
  an incorrect result is worse than no result, so correctness and predictable failure modes
  take priority over convenience or premature optimization.

### IV. Python Packaging & Versioning Standards
The project is implemented as a Python module and MUST follow established Python packaging
and versioning conventions, not ad-hoc scripts.
- The package MUST be structured per current packaging standards (`pyproject.toml` as the
  single source of build/project metadata, PEP 517/518-compliant build backend, `src/`
  layout for the importable package) rather than legacy `setup.py`-only distribution.
- Public releases MUST follow Semantic Versioning (MAJOR.MINOR.PATCH) per PEP 440-compatible
  version strings; the version MUST be defined in exactly one place and referenced elsewhere
  (e.g., via the build backend's dynamic version support), never hard-coded in multiple files.
- Dependencies MUST be declared explicitly with sensible version constraints in
  `pyproject.toml`; no undeclared/implicit dependencies on packages imported at runtime.
- Public APIs MUST follow PEP 8 naming and PEP 257 docstring conventions so the module is
  usable as a library, not just an application.
- Breaking changes to the public API MUST bump the MAJOR version and MUST be documented in
  a changelog before release.
- Rationale: treating machine-calc as a properly packaged, versioned Python module (rather
  than a loose collection of scripts) enables reliable installs, reproducible environments,
  and safe upgrades for anyone depending on it.

### V. Resource-Constrained Compatibility
machine-calc MUST remain usable on old, low-power hardware and MUST NOT assume access to
modern desktop/server resources.
- The application MUST run within approximately 64-128 MB of RAM and on a single-threaded
  CPU (no multi-core/multi-threading requirement) at minimal clock speeds; features MUST
  degrade gracefully rather than fail outright on such hardware.
- The codebase MUST remain compatible with older or long-term-stable operating system
  releases (e.g., Debian stable) and MUST NOT depend on bleeding-edge OS features, kernel
  versions, or system libraries.
- Dependencies MUST be chosen or configured to avoid heavy runtime footprints (e.g., avoid
  large numerical/data-science stacks when a lightweight alternative or the standard library
  suffices); any dependency with a non-trivial memory footprint MUST be justified in the
  pull request description.
- Each individual calculation SHOULD ideally complete within 0.5-1.0 seconds when run on
  the target legacy/low-power hardware profile described above; calculations that cannot
  reasonably meet this target MUST document the expected runtime and rationale in the
  pull request description, and SHOULD be profiled/benchmarked per the Additional
  Constraints performance gate.
- Any feature that cannot reasonably meet these constraints MUST be flagged during planning
  (`/speckit.plan`) with an explicit trade-off note, not silently merged.
- Rationale: this project targets environments (embedded, legacy, or minimal machines) where
  modern hardware assumptions do not hold; correctness on paper is worthless if the tool
  cannot actually run — and respond in reasonable time — where it is needed.

### VI. Extensibility by Design
Code MUST be structured so new calculations, units, or output formats can be added without
rewriting existing logic.
- Calculation logic MUST be organized behind clear, stable interfaces (e.g., functions/classes
  with well-defined inputs and outputs) so new implementations can be added by extension
  (new module/class/plugin) rather than by modifying unrelated existing code.
- Shared behavior (validation, unit conversion, error handling) MUST be factored into
  reusable components rather than duplicated per calculation.
- Hard-coded assumptions that would block adding a new calculation type, unit system, or
  input/output format MUST be called out in code review and avoided where a reasonable
  abstraction exists.
- The module's architecture MUST anticipate growth beyond drilling into other metal
  machining operations (e.g., turning, milling, and others to be identified later).
  Concretely: operation-specific logic (e.g., drilling's spindle speed/feed/torque/power
  formulas) MUST live behind a per-operation module/interface rather than being hard-coded
  into shared infrastructure (CLI, configuration loading, unit conversion, material/tool
  registries), so a future operation can be added as a new module implementing the same
  kind of interface without modifying unrelated existing operations' code.
- Cross-cutting concerns that are not operation-specific (workpiece material properties,
  unit conversion, configuration loading, structured error/result reporting) MUST be shared
  across current and future operations rather than duplicated per operation, while
  operation-specific reference data (e.g., drilling tool cutting/feed factors) MAY remain
  distinct per operation where the underlying physics differs.
- Rationale: the set of machine calculations this project supports is expected to grow —
  starting with drilling and extending to other metal machining operations such as turning
  and milling — so extensibility keeps that growth cheap and low-risk instead of requiring
  disruptive rewrites of shared infrastructure for every new operation.
- Rationale: the set of machine calculations this project supports is expected to grow;
  extensibility keeps that growth cheap and low-risk instead of requiring disruptive
  rewrites for every new feature.

### VII. Documentation & Publishing
Every build MUST produce up-to-date documentation serving both end users and developers,
and that documentation MUST be published automatically.
- Documentation MUST be generated using Sphinx (or a directly compatible successor) from
  in-repo sources (docstrings, `.rst`/`.md` content) so it stays synchronized with the code.
- Documentation MUST include distinct, clearly labeled content for: (a) end users (how to
  install and use the tool/library to get results) and (b) developers (architecture, public
  API reference, extension points per Principle VI).
- Generated documentation MUST be published automatically to GitHub Pages as part of the
  automated build process (see Additional Constraints); manual/local-only doc builds are
  not sufficient for release documentation.
- The `README.md` MUST report the current unit test coverage level (target: high or very
  high, per Principle II's minimum) so users and contributors can see test health at a
  glance without digging into CI logs.
- The `README.md` MUST display, near the top of the file, a build-status badge/icon
  reflecting the current state of the CI workflow's required checks (pass/fail) and a
  test-coverage badge/icon reflecting the current coverage percentage, both generated or
  updated automatically (e.g., via a CI-hosted badge service, a coverage-reporting
  service, or an equivalent auto-updating badge mechanism) rather than a manually-edited,
  static image or number that can silently go stale.
- Rationale: undocumented or inconsistently published documentation is effectively
  unusable documentation; automating generation and publishing removes the risk of docs
  silently going stale relative to the code. At-a-glance build-status and coverage badges
  give users and contributors an immediate, unmissable, always-current signal of project
  health directly on the landing page, without requiring them to open CI logs or run
  coverage tools locally.

### VIII. Internationalization of User-Facing Messages
All user-facing text (REPL prompts/output, CLI help, and error messages) MUST be
translatable, while internal application logging MUST always remain in English.
- User-facing strings (REPL/CLI prompts, output labels, help text, and error/validation
  messages surfaced to the user) MUST NOT be hard-coded inline in calculation or
  presentation logic; they MUST be sourced from a language/message file or configuration
  (e.g., a resource/catalog per locale, gettext `.po`/`.mo` files, or an equivalent
  key-based lookup mechanism) so a new language can be added by providing a new file/config
  rather than editing code.
- Message keys MUST be stable identifiers independent of any specific language's wording,
  so translations can be added, corrected, or replaced without touching calculation logic.
- A default language (English) MUST always be bundled and MUST be used as the fallback
  when a requested locale or a specific message key is missing, so the application never
  fails or shows a blank message solely due to an incomplete translation.
- Application/diagnostic logging (log lines intended for developers/operators, not shown
  to the end user as REPL/CLI output) MUST always be written in English, regardless of the
  active user-facing locale, so logs remain consistently searchable and diagnosable.
- New user-facing strings introduced in any change MUST be added to the message
  file/config (not inlined) and MUST have at least an English entry; missing translations
  for other supported languages MUST fall back per the rule above rather than block merge.
- Rationale: separating translatable user-facing messages from code enables adding new
  languages without touching or risking calculation logic, while keeping logs in a single
  language ensures maintainers can consistently search, correlate, and debug issues
  regardless of which locale a user runs the application in.

### IX. Automated Code Quality, Complexity & Security Gates (NON-NEGOTIABLE)
Every pull request MUST be automatically measured against objective complexity,
maintainability, and security metrics in CI; these gates complement, and do not replace,
human review.
- A gate MAY be limited to pull requests or pushes whose changed paths fall within files that
  gate is capable of evaluating ("path-based job selection"), provided: (a) the path-to-gate mapping
  is version-controlled and auditable, and defaults to running the gate whenever a changed
  path is not recognized by the mapping; (b) a failure of the path-selection mechanism itself
  defaults to running the gate rather than skipping it (fail open); (c) an automated test
  enforces both defaults and the mapping's composition, mirroring the aggregate-composition
  enforcement this principle already requires for `ci-ok`; and (d) a gate that does run is
  held to the same pass/fail standard as always — path-based selection MUST NOT alter a
  gate's own pass/fail outcome, only whether it runs. This exists so a change touching no
  file a gate could plausibly affect (e.g., specification or documentation text) is not
  required to run a gate with nothing to measure; it does not relax the requirement for any
  pull request or push that does touch in-scope files.
- Cyclomatic complexity MUST be measured per function (e.g., `ruff`'s `C90`/mccabe rule
  with a configured `max-complexity`, or `radon cc`); any function exceeding the
  configured threshold MUST be refactored or have the exception explicitly justified in
  the pull request description.
- Maintainability Index MUST be measured per module (e.g., `radon mi` enforced via
  `xenon` with a minimum grade threshold); modules dropping below the threshold MUST be
  flagged for refactoring before merge rather than accumulated as unmanaged technical debt.
- Static security analysis (e.g., `bandit`) MUST run in CI on every pull request whose
  changed paths are in scope for it (subject to the path-based job selection exception
  above); no high- or medium-severity finding MAY be merged without an explicit, documented
  suppression rationale in the pull request description.
- Dependency vulnerability scanning (e.g., `pip-audit`) MUST run in CI on every pull
  request and on a recurring schedule; known CVEs in direct or transitive dependencies
  MUST be resolved or explicitly risk-accepted before merge.
- Continuous static application security testing (SAST) (e.g., GitHub CodeQL) MUST be
  enabled for the repository; new high-confidence alerts MUST be triaged before the
  pull request that introduced them is merged.
- These checks MUST gate the `main` branch as required status checks so no pull request
  — including the repository owner's own — merges without them passing; bypassing
  required checks (e.g., via administrator override) MUST be limited to the
  review-approval gate alone, never to these automated quality/security gates. The
  requirement is that every gate blocks a merge, not that each one appears in the ruleset
  under its own name: an aggregate check that depends on every gate, runs even when one
  fails, and asserts each result explicitly satisfies this clause, and is the
  preferred form once the enumerated names become a maintenance burden of their own
  (issue #75). Aggregating MUST NOT quietly enlarge the gate — a supporting,
  non-blocking job pulled into the aggregate becomes a merge blocker — nor shrink it,
  and the aggregate's own composition MUST be enforced by an automated check.
- Rationale: subjective code review alone cannot consistently catch complexity growth,
  latent security defects, or vulnerable dependencies at scale; objective, automated
  metrics computed identically on every pull request make code quality and security
  measurable, comparable over time, and enforceable without depending on reviewer
  availability, expertise, or memory.

### X. Licensing & Author Rights
This project is distributed under a dual-license model: free for noncommercial use, with
commercial use requiring a separate paid license from the copyright holder.
- The repository MUST include a `LICENSE.md` at the root containing the full text of the
  [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)
  plus a "Required Notice" copyright line and a commercial-use addendum; any change to the
  licensing terms MUST update `LICENSE.md` as the single source of truth (no license text
  duplicated or paraphrased elsewhere in a way that could drift out of sync).
- "Noncommercial use" (personal, hobby, research, education, evaluation, and other
  non-revenue-generating use per the PolyForm Noncommercial definitions) MUST remain free
  and unrestricted; any use inside a for-profit business, in a paid product/service, or
  any other revenue-generating context is commercial use and is NOT licensed under
  `LICENSE.md` — it requires a separate, explicitly negotiated paid commercial license
  from the copyright holder.
- All rights not expressly granted to noncommercial users — including all commercial
  rights — are reserved by the copyright holder; no contribution, dependency, or generated
  artifact MAY be merged if it would relicense, sublicense, or otherwise weaken this
  reservation without an explicit constitution amendment.
- Package metadata (`pyproject.toml`'s `license`/`license-files`) and any user-facing
  documentation (README, generated Sphinx docs) MUST accurately reflect the current
  licensing terms and MUST NOT claim an OSI-approved or fully open-source license while
  this noncommercial restriction is in effect.
- A visible path for commercial-license inquiries (e.g., a GitHub issue link) MUST be
  documented in `LICENSE.md` and the README so prospective commercial users have a clear,
  low-friction way to request a paid license.
- Rationale: stating licensing terms as a constitutional principle — not just as inert
  legal text — ensures every future spec/plan/tasks cycle and code review treats the
  licensing model as a binding project constraint, preventing accidental relicensing,
  silent scope creep into permissive terms, or documentation drift between the legal
  text and what the project publicly claims.

### XI. Multi-Agent Coding-Tool Consistency
This project MUST support development via multiple AI coding agents (currently GitHub
Copilot and Claude Code, with others such as Cursor anticipated) without maintaining
hand-duplicated, independently-diverging instruction sets per agent.
- Per-agent instruction/skill/prompt files (e.g., Copilot's `.github/agents/` and
  `.github/prompts/`, Claude Code's `.claude/skills/`, and any future integration's
  equivalent directory) MUST be treated as generated artifacts of the Spec Kit integration
  mechanism, not as hand-authored, independently-maintained content.
- Exception — genuinely shared, hand-authored skills: a skill that predates or otherwise
  falls outside the Spec Kit integration mechanism, and that is genuinely useful to more
  than one coding agent (e.g., a repo-specific review or workflow skill under
  `.github/skills/<name>/`), MAY be hand-authored as a single canonical directory (holding
  `SKILL.md` and any supporting files) living in one agent's own skill directory. Every
  other agent's directory MAY reference that skill only via a symlink to the canonical
  directory — never a hand-copied, paraphrased, or independently-edited duplicate — so the
  skill remains one physical directory with no possibility of drift. This exception does
  NOT extend to any file actually produced by `specify integration install`/`specify
  integration upgrade`: those remain governed exactly as the bullet above requires, and
  hand-patching them (symlinked or otherwise) is still forbidden.
- Contributors MUST NOT manually copy, paraphrase, or hand-sync one agent's instruction
  file into another agent's format. A new coding-agent integration MUST be added via
  `specify integration install <name>`, and existing integrations MUST be refreshed via
  `specify integration upgrade <name>` against Spec Kit's upstream template source, so
  every installed agent's instructions remain derived from one canonical upstream source.
- Project-specific workflow customization MUST live only in Spec Kit's designated
  customization points (this constitution, `.specify/templates/*`, `.specify/extensions.yml`
  hooks) — never patched directly into a generated per-agent file — since such edits are
  silently lost or diverge on the next `specify integration upgrade`.
- Installed integrations SHOULD be kept up to date on a recurring cadence (manually, or via
  an automated recurring job that runs `specify integration upgrade` for each installed
  agent and opens a pull request when generated files change) so agent instructions do not
  silently drift from the upstream source over time.
- Rationale: each coding agent requires its own instruction-file format (Copilot's
  `.github/agents`/`.github/prompts` pair vs. Claude Code's self-contained
  `.claude/skills/*/SKILL.md`); without a single canonical upstream source and a mechanical
  regeneration step, these files inevitably duplicate and drift, producing inconsistent
  agent behavior and an unreviewable, ever-growing maintenance burden (issue #46). The
  symlink exception preserves this same guarantee for repo-specific skills that are not
  themselves Spec Kit template output: a symlink is definitionally a single directory, not
  a copy, so it cannot independently diverge from its target the way a hand-duplicated
  directory can — the drift this principle exists to prevent is structurally impossible
  for it.

### XII. Long-Lived Feature Branches for Multi-PR Work
A feature whose spec/plan/tasks are too large or risky to implement, test, and review in a
single pull request MUST use a long-lived integration branch rather than being force-fit
into one PR or merged to `main` in a partially-built state.
- The feature MUST still be created via the standard `/speckit-specify` flow, and a numbered
  feature branch (e.g., `NNN-short-name`) off `main` MUST be explicitly created for it —
  either via that flow's `before_specify` branch-creation hook where one is configured, or
  manually using the same naming convention otherwise, since branch creation is optional
  and independent of the spec directory in the standard flow and MUST NOT be assumed to
  happen automatically. This branch, not `main`, becomes the integration branch for the
  feature's full lifetime.
- Sub-units of work MUST be delivered as separate pull requests targeting the integration
  branch, not `main`, until the feature is complete; `main` MUST NOT receive a pull request
  for a partially-built slice of the feature.
- Every pull request into the integration branch MUST pass the identical CI gates required
  for a pull request into `main` (Principles II, III, and IX: tests, type-checking,
  linting, complexity/security/dependency scanning) and MUST receive review per
  Development Workflow — the quality bar for an intermediate PR is not lower merely
  because its target is not `main`. Because this repository's required-status-check
  ruleset and CodeQL default-setup scanning are currently scoped to `main` (see
  Additional Constraints/README), the integration branch MUST be brought under the same two
  separate rulesets `main` uses (a status-checks ruleset with no bypass for anyone, and a
  distinct PR-review ruleset whose bypass is scoped only to the repository owner) before
  its first sub-PR is opened, so this gate is actually enforced and not merely documented.
  These MUST remain two separate rulesets, not combined into one: combining them would let
  the owner's review bypass also bypass required status checks. If CodeQL default setup
  does not scan the integration branch, an explicit CodeQL advanced-setup workflow covering
  it MUST be added (not merely may be) to satisfy the identical-gates requirement above —
  but because CodeQL default and advanced setup cannot both run for the same language at
  once (enabling advanced setup replaces default setup entirely, repo-wide), that workflow
  MUST trigger on both `main` and the integration branch so introducing it cannot silently
  drop `main`'s existing CodeQL coverage; it MUST NOT be used as a substitute for either
  ruleset above.
- The integration branch MUST be reconciled with `main` (merging `main` into the integration
  branch, or rebasing the integration branch onto `main`) before each new sub-PR is opened
  against it, and again immediately before the final merge to `main`, so divergence is
  resolved incrementally rather than compounding into an unreviewable final diff. Rebasing
  `main` onto the integration branch MUST NOT be done, since that would rewrite `main`.
- The feature MUST NOT be merged into `main` until: all of its `tasks.md` items other than
  ones explicitly designated as post-merge validation/cleanup are complete (a post-merge
  item, e.g. confirming a scheduled workflow trigger fires, MAY remain open at merge time
  but MUST be tracked to completion afterward rather than dropped), the full test suite
  passes on the integration branch with `main`'s latest changes reconciled in, and
  `/speckit-converge` (or an equivalent implementation-vs-artifact completeness check) has
  been run against the final state, with any tasks it appends completed —
  `/speckit-analyze` alone is insufficient here since it only cross-checks `spec.md`,
  `plan.md`, and `tasks.md` against each other pre-implementation and cannot detect
  implementation work that never happened.
- The final merge to `main` MUST happen through a pull request like any other change; once
  merged, the integration branch and any of its now-obsolete sub-branches MUST be deleted
  to avoid stale, confusing branch state.
- Rationale: forcing a large feature into one pull request either blocks review until an
  unreviewably large diff is ready, or pressures merging partially-built/untested work into
  `main`, violating Principles II and III; a long-lived integration branch lets the same
  PR-sized review and CI discipline apply throughout, while keeping `main` always
  releasable per the Principle VII/Additional Constraints continuous-publish requirement.

### XIII. Manual Verification for Interactive & Reference-Fidelity Features (NON-NEGOTIABLE)
A feature whose correctness depends on how it looks or behaves to a human — an interactive
console/TUI or GUI surface, or any change claiming to match an external reference exactly —
MUST NOT be marked complete on the strength of automated tests alone.
- `tasks.md` MUST carry at least one distinct, explicitly-named manual-verification task for
  such a feature (e.g., "manually walk `quickstart.md` Scenario N against a real terminal/
  display"), separate from and in addition to its automated test tasks; that task MUST be
  completed — performed by the developer or a reviewer, since a coding agent without access
  to a real terminal/display cannot perform it itself — before the feature's implementation
  phase is considered done. A fully passing automated test suite MUST NOT be treated as
  evidence that a rendering or interaction detail (color, position, focus highlighting,
  shading, spacing/layout, or any other property the project's test strategy does not
  directly assert against) is correct, when that test strategy cannot observe it.
- When a spec, plan, or clarification session asserts that reference material a feature must
  match (a prototype, a mockup, a screenshot, prior discarded code) is unavailable, lost, or
  superseded, that claim MUST be verified against the actual current filesystem/repository
  state at the time it is written, not carried forward from a prior session's memory or an
  earlier artifact's own unverified claim. If the reference artifact does in fact exist, its
  literal content MUST be read and directly cited (or linked/embedded in the spec) before any
  prose paraphrase of its behavior is written; a description re-derived without reading the
  actual artifact MUST NOT be treated as an equivalent substitute for having read it.
- Rationale: specs/018-tui-splitpane-redesign needed two full implementation passes rejected
  outright before a prototype-fidelity rewrite finally matched, and a further 8 user-reported
  correction rounds after that rewrite was itself marked "done" — none of it caught by CI,
  because this project's TUI test strategy asserts against state and rendered text, not
  color/position/shading, and because a spec's own claim that the reference prototype was
  "discarded" was carried forward for two full implementation passes without ever being
  checked against the filesystem, where the prototype had been the entire time. Automated
  tests and human visual review catch structurally different classes of defect; treating the
  former as satisfying the latter is exactly the gap this principle closes.

## Additional Constraints (Quality Gates)

- CI MUST run linting, the full automated test suite, and a package build check on every
  pull request whose changed paths are in scope for each (subject to Principle IX's
  path-based job selection exception); all three MUST pass before merge when they run.
- Dependencies introducing calculation logic (e.g., math/statistics libraries) MUST be
  vetted for correctness and actively maintained status before adoption.
- Performance MUST be measured, not assumed: any calculation expected to run on large
  datasets or in tight loops MUST have a benchmark or profiling note before optimization,
  and MUST be evaluated against the legacy-hardware runtime target in Principle V.
- GitHub Actions MUST automate, for every push/pull request, linting, static type
  checking, the full test suite (with coverage reporting), a package build check, and a
  Sphinx documentation build, each subject to Principle IX's path-based job selection
  exception; all MUST pass before merge when they run.
- GitHub Actions MUST automate the Principle IX gates: cyclomatic complexity/Maintainability
  Index checks (radon/xenon or equivalent) and static security analysis (bandit or
  equivalent) for every pull request whose changed paths are in scope for each (subject to
  Principle IX's path-based job selection exception), and dependency vulnerability scanning
  (pip-audit or equivalent) for every pull request unconditionally — that job is not subject
  to the exception; GitHub CodeQL MUST run continuously as repository-level SAST,
  independent of any pull request's changed paths. All MUST pass before merge when they run,
  and all MUST gate `main` as required status checks — directly or through an aggregate
  check meeting Principle IX's conditions.
- GitHub Actions MUST automatically publish the generated Sphinx documentation to GitHub
  Pages on every successful build of the default branch, keeping user- and developer-facing
  docs continuously up to date.
- Every merge to the `main` (default) branch MUST trigger an automated GitHub Actions
  workflow that builds and publishes a new package release to PyPI, so `main` always
  reflects an installable, published version.

## Development Workflow (Review Process)

- Every pull request MUST be reviewed by at least one other contributor (or, for solo work,
  self-reviewed against this constitution's checklist) before merge.
- Reviewers MUST explicitly confirm: (1) tests exist and cover edge cases, (2) calculation
  logic is documented with units/sources, (3) no floating-point exact-equality bugs,
  (4) packaging/version metadata is consistent with Principle IV, (5) for a feature Principle
  XIII applies to, its named manual-verification task in `tasks.md` was actually completed
  (not merely present) — a green CI run MUST NOT be accepted as a substitute confirmation.
- Automated Principle IX gates (complexity, maintainability, type-checking, static
  security analysis, dependency scanning, CodeQL) MUST pass before merge, gating `main`
  either directly or through an aggregate check per Principle IX; reviewers are not
  required to manually re-derive metrics already computed by these gates, but MUST review
  and approve any documented exception/suppression raised against them.
- The `/speckit.analyze` and `/speckit.checklist` workflows SHOULD be used before
  `/speckit.implement` on any feature touching calculation logic, to catch spec/plan gaps
  early rather than during code review.

## Governance

This constitution supersedes all other informal practices for this repository. Amendments
require: (1) a documented rationale for the change, (2) a version bump per the policy below,
and (3) propagation of any dependent changes to `.specify/templates/*` and agent guidance
files, verified as an explicit follow-up step rather than assumed to happen automatically
within the amending change itself. Spec Kit's own `/speckit-constitution` command
deliberately limits its own scope to this file alone (its "Scope Guard") and does not itself
propagate changes into either kind of dependent file — and the two kinds are not equivalent,
per Principle XI: `.specify/templates/*` (and `.specify/extensions.yml` hooks) are designated
customization points, read directly by the Spec Kit commands that use them (e.g.
`/speckit-tasks` reads `tasks-template.md`), so a hand-authored edit here takes effect on its
own, the same way this file does. Generated per-agent instruction files (`.github/agents/`,
`.claude/skills/`, and any future integration's equivalent) are a separate mechanism entirely:
they are never hand-patched directly, but they are also NOT regenerated from this repo's own
`.specify/templates/*` — `specify integration upgrade` instead reproduces whatever template
pack is bundled inside the currently-installed, pinned `specify-cli` version (verified in
specs/011-multi-agent-skill-sync/research.md's addendum), which is independent of any local
customization made here. Concretely, propagating an amendment therefore means: after amending
this constitution, run `/speckit-analyze` (or an equivalent cross-artifact consistency check)
against any affected or representative spec before considering the amendment complete;
hand-edit `.specify/templates/*` content that no longer matches (that edit alone is sufficient
for it to take effect). Generated per-agent instruction files almost never need a change for
this at all: the Spec Kit commands they define (`/speckit-plan`, `/speckit-analyze`, etc.)
read `.specify/memory/constitution.md` live at invocation time rather than embedding its
content (e.g. `/speckit-analyze`'s own "Load constitution.md for principle validation" step),
so an amendment here is already visible to them on their next run, with no propagation step
required. The rare case where a generated file's own *structure* — not the constitution
content it reads — would need to change to fully support a new principle (for example, a
command needing a new step, not just a new fact to read) is an upstream Spec Kit template
concern: propose it against the spec-kit project, not as a local hand-edit, since Principle
XI forbids hand-patching these files and, per the previous paragraph, `specify integration
upgrade` cannot pick up a local change even if one were made.

Versioning policy (semantic versioning applied to governance):
- MAJOR: Backward-incompatible removal or redefinition of a principle.
- MINOR: A new principle or materially expanded guidance is added.
- PATCH: Wording clarifications, typo fixes, non-semantic refinements.

All pull requests and code reviews MUST verify compliance with the principles above.
Any deviation MUST be justified in the pull request description and, if it becomes a
recurring pattern, MUST trigger a proposed constitution amendment rather than repeated
ad-hoc exceptions. Use `.specify/memory/constitution.md` as the authoritative source for
runtime development guidance until a dedicated guidance file is introduced.

**Version**: 1.12.0 | **Ratified**: 2026-07-08 | **Last Amended**: 2026-09-11
