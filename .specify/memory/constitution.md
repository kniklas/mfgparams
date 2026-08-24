<!--
Sync Impact Report
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
- Test suites MUST run in CI on every pull request (e.g., via `pytest`); a failing test
  suite blocks merge.
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
- Cyclomatic complexity MUST be measured per function (e.g., `ruff`'s `C90`/mccabe rule
  with a configured `max-complexity`, or `radon cc`); any function exceeding the
  configured threshold MUST be refactored or have the exception explicitly justified in
  the pull request description.
- Maintainability Index MUST be measured per module (e.g., `radon mi` enforced via
  `xenon` with a minimum grade threshold); modules dropping below the threshold MUST be
  flagged for refactoring before merge rather than accumulated as unmanaged technical debt.
- Static security analysis (e.g., `bandit`) MUST run in CI on every pull request; no
  high- or medium-severity finding MAY be merged without an explicit, documented
  suppression rationale in the pull request description.
- Dependency vulnerability scanning (e.g., `pip-audit`) MUST run in CI on every pull
  request and on a recurring schedule; known CVEs in direct or transitive dependencies
  MUST be resolved or explicitly risk-accepted before merge.
- Continuous static application security testing (SAST) (e.g., GitHub CodeQL) MUST be
  enabled for the repository; new high-confidence alerts MUST be triaged before the
  pull request that introduced them is merged.
- These checks MUST be configured as required status checks on the `main` branch so no
  pull request — including the repository owner's own — merges without them passing;
  bypassing required checks (e.g., via administrator override) MUST be limited to the
  review-approval gate alone, never to these automated quality/security gates.
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

## Additional Constraints (Quality Gates)

- CI MUST run linting, the full automated test suite, and a package build check on every
  pull request; all three MUST pass before merge.
- Dependencies introducing calculation logic (e.g., math/statistics libraries) MUST be
  vetted for correctness and actively maintained status before adoption.
- Performance MUST be measured, not assumed: any calculation expected to run on large
  datasets or in tight loops MUST have a benchmark or profiling note before optimization,
  and MUST be evaluated against the legacy-hardware runtime target in Principle V.
- GitHub Actions MUST automate, for every push/pull request: linting, static type
  checking, the full test suite (with coverage reporting), a package build check, and a
  Sphinx documentation build; all MUST pass before merge.
- GitHub Actions MUST automate, for every pull request, the Principle IX gates: cyclomatic
  complexity/Maintainability Index checks (radon/xenon or equivalent), static security
  analysis (bandit or equivalent), and dependency vulnerability scanning (pip-audit or
  equivalent); GitHub CodeQL MUST run continuously as repository-level SAST. All MUST
  pass before merge, and all MUST be configured as required status checks on `main`.
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
  (4) packaging/version metadata is consistent with Principle IV.
- Automated Principle IX gates (complexity, maintainability, type-checking, static
  security analysis, dependency scanning, CodeQL) MUST pass as required status checks
  before merge; reviewers are not required to manually re-derive metrics already computed
  by these gates, but MUST review and approve any documented exception/suppression raised
  against them.
- The `/speckit.analyze` and `/speckit.checklist` workflows SHOULD be used before
  `/speckit.implement` on any feature touching calculation logic, to catch spec/plan gaps
  early rather than during code review.

## Governance

This constitution supersedes all other informal practices for this repository. Amendments
require: (1) a documented rationale for the change, (2) a version bump per the policy below,
and (3) propagation of any dependent changes to `.specify/templates/*` and agent guidance
files, verified as an explicit follow-up step rather than assumed to happen automatically
within the amending change itself. Spec Kit's own `/speckit-constitution` command
deliberately limits its own scope to this file alone (its "Scope Guard") and does not
propagate changes into dependent templates or agent guidance — those remain generated
artifacts of the Spec Kit integration mechanism, never hand-patched directly (Principle XI).
Concretely: after amending this constitution, run `/speckit-analyze` (or an equivalent
cross-artifact consistency check) against any affected or representative spec before
considering the amendment complete, and reconcile `.specify/templates/*`/agent guidance
content manually if it no longer matches.

Versioning policy (semantic versioning applied to governance):
- MAJOR: Backward-incompatible removal or redefinition of a principle.
- MINOR: A new principle or materially expanded guidance is added.
- PATCH: Wording clarifications, typo fixes, non-semantic refinements.

All pull requests and code reviews MUST verify compliance with the principles above.
Any deviation MUST be justified in the pull request description and, if it becomes a
recurring pattern, MUST trigger a proposed constitution amendment rather than repeated
ad-hoc exceptions. Use `.specify/memory/constitution.md` as the authoritative source for
runtime development guidance until a dedicated guidance file is introduced.

**Version**: 1.9.1 | **Ratified**: 2026-07-08 | **Last Amended**: 2026-08-22
