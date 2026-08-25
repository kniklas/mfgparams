# Feature Specification: Rename Package to mfgparams

**Feature Branch**: `012-rename-package-mfgparams`

**Created**: 2026-08-25

**Status**: Draft

**Input**: User description: "implement issue #62: rename package to shorter, generic name"

## Clarifications

### Session 2026-08-25

- Q: Should this feature also rename the git repository (GitHub repo `kniklas/machine-calc`) and/or the local clone directory itself? → A: No — out of scope for this feature. The repository and/or local directory rename will be performed manually by the user after this session ends; this feature only renames the Python package's own identifiers (distribution name, module name) and their in-repo references.
- Q: Should this feature rename, delete, or leave alone the local `my-project/` scaffold directory? → A: Raise a separate issue with recommendations and impact instead of deciding here. Filed as [#67](https://github.com/kniklas/machine-calc/issues/67); `my-project/` is out of scope for this feature and its disposition is tracked there.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and import under the new, generic name (Priority: P1)

As someone who installs or imports the library, I want its distribution and module name to be
short and generic — not implying metal-only machining — so it accurately reflects a
multi-material manufacturing calculation library and is easy to type, remember, and depend on.

**Why this priority**: This is the entire substance of issue #62 and the sole scope of this
feature; every other user story exists only to make this one safe and complete.

**Independent Test**: Can be fully tested by installing the package fresh and importing it under
the new name, then running the CLI — everything works identically to before the rename, just
under the new name.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** a user installs the package, **Then** the installed
   distribution is named `mfgparams` and `import mfgparams` succeeds.
2. **Given** the package installed under the new name, **When** a user runs the CLI entry point,
   **Then** it behaves identically to before the rename (same prompts, same calculations, same
   output, same exit codes).
3. **Given** the rename has shipped, **When** a user looks for the old distribution name
   (`machine-calc`) or old import name (`machine_calc`), **Then** neither is published or
   importable — there is no dual-name or alias period.

---

### User Story 2 - No stale references anywhere in the project (Priority: P2)

As a maintainer or contributor, when I search the codebase, tests, documentation, CI
configuration, and packaging metadata after the rename, I find no remaining functional
references to the old package name, so nobody is confused by mixed naming or hits a broken
reference.

**Why this priority**: A rename that only changes some references (e.g., `pyproject.toml` but
not imports, or code but not CI) would leave the project broken or inconsistent; catching every
reference is what makes the rename safe to ship.

**Independent Test**: Can be fully tested by running a repository-wide search for the old
package/module name and running the full automated test suite — both must come back clean
(zero functional references found; all tests passing) independent of User Story 1.

**Acceptance Scenarios**:

1. **Given** the completed rename, **When** searching source code, tests, docs, scripts, CI
   workflow files, and packaging files for the old module or distribution name, **Then** no
   functional references remain (only historical mentions such as a CHANGELOG entry that
   intentionally documents the rename).
2. **Given** the full automated test suite, **When** it is run after the rename, **Then** all
   tests pass with no change in calculation behavior, CLI behavior, or public API.

---

### User Story 3 - Rename is documented for future readers (Priority: P3)

As a maintainer, I want the project's change history to clearly record that the package was
renamed, from what, and why, so future contributors and users who remember the old name can
understand what happened.

**Why this priority**: Lowest priority because it doesn't affect functionality, but it's cheap
to do and prevents future confusion for anyone who encounters the old name in old issues,
forks, or search results.

**Independent Test**: Can be fully tested by reading the CHANGELOG after the rename ships and
confirming it documents the change independent of the other two stories.

**Acceptance Scenarios**:

1. **Given** the CHANGELOG, **When** reviewed after the rename ships, **Then** it includes an
   entry noting the package was renamed from `machine-calc`/`machine_calc` to `mfgparams` and
   the reason (a shorter, more generic name reflecting the library's multi-material scope).

---

### Edge Cases

- Previously published releases under the old name remain published as historical versions on
  the package index; they are not retracted or modified. Only new releases go out under the new
  name.
- Any file, directory, or config-file/section name that embeds the old name (for example,
  packaging metadata directories generated at build time, or config file names) must be
  addressed for consistency, not just Python import paths.
- Generated/build artifacts (build output, distribution caches, etc.) are regenerated fresh
  after the rename rather than manually edited — a rebuild must not leave stale output that
  still carries the old name.
- Contributor-facing or CI-facing tooling that hard-codes the old name (for example, in
  workflow step names or generated reports) must be updated so automation doesn't silently
  keep referring to the old name even though it is functionally unaffected.
- The GitHub repository itself (`kniklas/machine-calc`) and the local clone's directory name
  are not renamed as part of this feature (see Clarifications). URLs that point at the
  repository by its current slug (for example, CI/coverage badges or issue links in the
  README) therefore keep resolving correctly only while the repository keeps its current
  name — they are addressed separately, at the time the repository itself is renamed, not
  as part of this package-identifier rename.
- The local, gitignored `my-project/` scaffold directory is untouched by this feature; its
  fate (keep, delete, or repurpose) is tracked in
  [issue #67](https://github.com/kniklas/machine-calc/issues/67), not decided here.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package's distribution name (as installed and as it would be published) MUST
  change from `machine-calc` to `mfgparams`.
- **FR-002**: The importable module/package name MUST change from `machine_calc` to
  `mfgparams` everywhere it is imported, referenced, or configured.
- **FR-003**: Every reference to the old package/module name across the repository — source
  code, tests, documentation, CLI help/usage text, CI/CD workflow files, packaging metadata,
  scripts, and any agent/skill documentation — MUST be updated to the new name, with no
  functional behavior change beyond the name itself. This excludes URLs that point at the
  GitHub repository by its current slug (`kniklas/machine-calc`), such as CI/coverage badges
  and issue links — those keep their current, working value because the repository itself is
  not renamed by this feature (see Clarifications).
- **FR-004**: The rename MUST NOT alter any calculation logic, CLI behavior, public API
  signatures or return values, or configuration schema — the change is limited to identifiers
  and text tied to the package's name.
- **FR-005**: The full automated test suite MUST pass after the rename, exercising the library
  and CLI under the new package name, with no reduction in test coverage.
- **FR-006**: The project MUST NOT ship a backward-compatible alias or shim (for example, a
  stub `machine_calc` package that re-exports `mfgparams`) — this is a direct rename only, per
  the milestone's "keeping only changing name of the package" scope.
- **FR-007**: The CHANGELOG MUST record the rename, including the old and new names and the
  reason for the change.
- **FR-008**: The implementation MUST include a repo-wide verification step confirming no
  remaining functional references to the old name exist outside of intentional historical
  record-keeping (e.g., the CHANGELOG entry documenting the rename).

### Key Entities

*(Not applicable — this feature changes identifiers and text only; it introduces no new data
entities.)*

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An automated repository-wide search finds zero functional occurrences of the old
  package or module name outside of the CHANGELOG entry documenting the rename.
- **SC-002**: 100% of the pre-existing automated test suite passes after the rename, with no
  drop in pass rate or coverage attributable to the rename.
- **SC-003**: A fresh install of the library under the new name, followed by running its CLI,
  completes successfully and produces output identical to the pre-rename version.
- **SC-004**: Building distributable packages after the rename succeeds and every produced
  artifact is named after the new package, with none named after the old package.

## Assumptions

- The new package name is `mfgparams`, taken directly from issue #62's stated target name, and
  is understood to refer to the actual distributed Python package (currently
  `machine_calc` / `machine-calc`) — not the locally gitignored `my-project/` scaffold
  directory that happens to share a name with the issue's literal wording. That directory's
  disposition (keep, delete, or repurpose) is out of scope here and tracked separately in
  [issue #67](https://github.com/kniklas/machine-calc/issues/67).
- This feature is scoped strictly to the name change ("keeping only changing name of the
  package," per the milestone's own framing). Broader module restructuring implied by the
  parent milestone ("Refactor package and modules for multi-purpose") is explicitly out of
  scope here and will be handled, if at all, by separate future features.
- No backward-compatibility alias/shim is required or wanted; consumers of the old name must
  switch to the new name directly.
- Thoroughly checking that every reference has been updated, and the associated test
  verification, is expected to be carried out during the subsequent planning, task breakdown,
  and implementation phases — not finalized within this specification.
- Previously published releases under the old name are left untouched; only future releases use
  the new name.
