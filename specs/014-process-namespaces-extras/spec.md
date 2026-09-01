# Feature Specification: Process Namespaces and Installation Extras

**Feature Branch**: `014-process-namespaces-extras`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "implement issue #63 part1: restructure mfgparams as recommended earlier"

## Context

This feature is **slice 1 of 4** of [issue #63](https://github.com/kniklas/mfgparams/issues/63)
("change repository and package structure"), per the agreed decomposition in
[the plan comment on #63](https://github.com/kniklas/mfgparams/issues/63#issuecomment-5470725460).
It covers the *structural* half of #63: where code lives and what gets installed.

Deliberately **not** in this slice:

| Slice | Scope | Why separate |
|---|---|---|
| 015 | Relocating message catalogs out of core; core returns error codes rather than translated text | Changes the meaning of an existing result field and requires its own clarifications; isolating it keeps this slice mechanically verifiable |
| 016 | Path-based CI job selection | Cannot be designed until this slice's directory layout exists |
| 017 | Placeholder namespaces for not-yet-implemented processes (turning, welding, joining, forming) | Trivial and independent |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reach a calculation by process and operation (Priority: P1)

As someone using the library programmatically, I want to reach a calculation through a path that
names the manufacturing **process** and then the **operation** within it, so that the import path
tells me where a calculation sits in the manufacturing domain, and so that adding a future process
(turning, welding, forming) is an addition rather than a reorganisation.

**Why this priority**: This is the substance of issue #63's "Manufacturing processes and
operations" section and the reason the slice exists. Every other story here exists to make this one
safe, installable, and documented.

**Independent Test**: Import a drilling and a milling calculation through the process-qualified path
in a fresh environment and compute a result; compare it against the value the same inputs produced
before the restructure.

**Acceptance Scenarios**:

1. **Given** the library is installed, **When** a caller imports the drilling calculation through
   the process-qualified path, **Then** the import succeeds and the calculation returns results
   identical to those produced before this feature.
2. **Given** the library is installed, **When** a caller imports the end-milling and face-milling
   calculations through their process-qualified paths, **Then** both succeed and return identical
   results to before this feature.
3. **Given** the library is installed, **When** a caller imports the names published at the
   top-level package (the documented public surface), **Then** every name that was importable
   before this feature is still importable under the same top-level name.
4. **Given** the restructure has shipped, **When** anyone searches the codebase for the previous
   operation-first module path, **Then** no functional reference to it remains — there is no
   dual-path or alias period.

---

### User Story 2 - Install only what is needed (Priority: P1)

As someone embedding this library in another application, I want a default installation to bring in
only what the calculations themselves require — not the interactive console's dependencies — so my
application does not inherit dependencies it never uses.

**Why this priority**: Equal to Story 1. It is the second half of issue #63's stated goal, it is the
reason the console code has to move at all, and it must be decided *before* the package is first
published (issue #40), because the installable surface is a compatibility contract from the first
release onward.

**Independent Test**: Install the package without extras in a clean environment, confirm the
calculation API works and the console's dependencies are absent; then install with the console
extra and confirm the interactive console starts.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the package is installed without extras, **Then** the
   calculation API is fully usable and no console-only dependency is present.
2. **Given** a clean environment, **When** the package is installed with the console extra, **Then**
   the interactive console starts and behaves identically to before this feature — same prompts,
   same calculations, same output, same exit codes.
3. **Given** a clean environment, **When** the package is installed with the "everything" extra,
   **Then** every optional capability the project currently ships is available.
4. **Given** a dependency the console needs is unavailable — the `console` extra was never
   installed, or an install is incomplete — **When** a user invokes the console entry point,
   **Then** they get a short actionable message naming the exact install command that fixes it,
   and a non-zero exit status — never a raw stack trace.

   The Given clause is keyed on a *dependency* rather than on the extra because an extra gates
   dependencies, not modules (FR-011): the console module ships in every wheel, so "installed
   without the console extra" alone does not stop the entry point from working — and with the
   extra empty on delivery, it succeeds.

---

### User Story 3 - Find the code and the docs where the structure says they are (Priority: P2)

As a maintainer or contributor, I want the test suite, documentation, packaging metadata, and CI
configuration to mirror the new structure, so that nothing points at the old layout and the
structure is discoverable without reading git history.

**Why this priority**: Does not change what a user can do, but an unmirrored test tree or a stale
documentation path is exactly the drift that makes the next slice more expensive. It is also a
precondition for slice 016, which selects CI work by path.

**Independent Test**: Search the repository for references to the previous layout and find none;
confirm the built distribution contains every bundled data file at its new location.

**Acceptance Scenarios**:

1. **Given** the restructure has shipped, **When** the distribution is built and inspected, **Then**
   every bundled reference-data file is present at its new path inside the built artifact.
2. **Given** the restructure has shipped, **When** a contributor looks for the tests covering a
   given process and operation, **Then** the test layout mirrors the source layout.
3. **Given** the restructure has shipped, **When** the published documentation is built, **Then** it
   documents the new import paths and the installation options, with no reference to the previous
   layout.

---

### Edge Cases

- **Console entry point with a console dependency unavailable**: covered by Story 2 scenario 4 —
  actionable message and non-zero exit, never a traceback. Note this is not the same as "installed
  without the extra": the extra gates dependencies, not the module.
- **A partially-installed console**: the guard must key on whether the console's *dependencies*
  resolve, not on a recorded installation choice and not on whether `mfgparams.console` itself
  imports — the module ships in every wheel, so the latter test can never fail. A broken or
  partially-removed console dependency must produce the same actionable message rather than a
  traceback from deep inside a submodule, whether it surfaces while the console is being imported
  or later, while it is running.
- **Bundled data files silently dropped from the distribution**: moving source directories moves the
  data directories with them; if packaging metadata is not updated in step, the library installs but
  fails at first use in a way no source-tree test would catch. Must be caught by a build-and-inspect
  assertion, not by importing from a source checkout.
- **A stale reference that is documentation-only**: harmless at runtime but must still be found, or
  it silently teaches the wrong path.
- **Reference-data files whose names encode the old operation-first layout**: must move with their
  module and keep their contents byte-identical, so no calculation input changes as a side effect.

## Requirements *(mandatory)*

### Functional Requirements

#### Structure

- **FR-001**: Calculation modules MUST be organised so that a manufacturing **process** contains its
  **operations**, replacing the current operation-first grouping. The grouping level MUST be named
  in the plural (`processes`), consistent with the plural level it replaces.
- **FR-002**: Drilling and milling MUST both be reachable as operations of the machining process,
  and milling MUST retain its sub-operation level, so that end milling and face milling remain
  distinct operations *within* milling rather than siblings of drilling.
- **FR-003**: The reorganisation MUST NOT change any calculation input, output, formula, or bundled
  reference-data value. Results before and after MUST be identical for identical inputs.
- **FR-004**: The previous operation-first import paths MUST NOT remain available in any form — no
  alias, shim, or deprecation period. There is exactly one path to each calculation.
- **FR-005**: The set of names published at the top-level package MUST be unchanged by this feature,
  so that code importing only the documented public surface is unaffected.
- **FR-006**: Adding a future process MUST NOT require modifying any existing process's modules;
  the structure MUST make a new process an addition, not an edit.

#### Console separation and extras

- **FR-007**: The interactive console MUST live in its own sub-package, separate from the
  calculation core.
- **FR-008**: The calculation core MUST NOT import the console sub-package, at module import time or
  otherwise. This MUST be enforced automatically, not by convention.
- **FR-009**: Installing the package without extras MUST install only what the calculation core
  requires.
- **FR-010**: An extra MUST be defined that adds the console's dependencies, and an "everything"
  extra MUST be defined that includes all other extras the project ships.
- **FR-011**: Invoking the console when its dependencies are unavailable MUST produce a single
  actionable message naming the exact command that fixes it, and exit with a non-zero status,
  without a stack trace.
- **FR-012**: The console entry point MUST remain invocable under both of its current forms, with
  unchanged behaviour when its dependencies are present.
- **FR-013**: Any dependency that only the console needs MUST NOT be required by a default install.

#### Mirroring

- **FR-014**: The test tree MUST mirror the new source structure.
- **FR-015**: Packaging metadata MUST include every bundled data file at its new path, and this MUST
  be verified against a built distribution rather than a source checkout.
- **FR-016**: User-facing documentation MUST describe the new import paths and the installation
  options.
- **FR-017**: The repository MUST NOT retain functional references to the previous layout after this
  feature, and this MUST be enforced automatically so a later change cannot silently reintroduce one.

#### Release handling

- **FR-018**: This feature MUST NOT trigger its own version release. Its changes MUST accumulate in
  the project's unreleased changelog section, so that issue #63's slices are published as a single
  major release once the last slice lands.

### Key Entities

- **Process**: A manufacturing process (machining; later turning, welding, joining, forming). Groups
  one or more operations. Only machining has implemented operations in this feature.
- **Operation**: A specific operation within a process (drilling, milling). Owns its formulas, its
  tool definitions, and its reference data. Milling additionally has sub-operations (end milling,
  face milling).
- **Installation extra**: A named, optional dependency group a user may request at install time.
  This feature defines one for the console and one meaning "everything".

Applying FR-001 and FR-002, the resulting reachable shape is:

```
mfgparams                                  core calculation API (public surface unchanged)
mfgparams.processes.machining.drilling
mfgparams.processes.machining.milling.end_milling
mfgparams.processes.machining.milling.face_milling
mfgparams.console                          interactive console, behind the console extra
```

Future processes (turning, welding, joining, forming) attach as siblings of `machining` without
touching it, satisfying FR-006.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every calculation the library exposes, results for identical inputs are identical
  before and after this feature — verified by the existing contract tests, unchanged in substance.
- **SC-002**: A default installation pulls in zero console-only dependencies.
- **SC-003**: A user who invokes the console while one of its dependencies is unavailable is told,
  in one message, the exact command that fixes it; no stack trace reaches them. Stated in terms of
  a dependency, not of the extra, for the reason given under Story 2 scenario 4.
- **SC-004**: Zero functional references to the previous layout remain anywhere in the repository,
  enforced by an automated check that fails if one is reintroduced.
- **SC-005**: 100% of bundled reference-data files are present in the built distribution, verified
  by inspecting a built artifact.
- **SC-006**: The full test suite passes on every supported Python version, with total coverage at or
  above the project's existing threshold.
- **SC-007**: A contributor can locate the tests for any given process and operation from the source
  path alone, without searching.

## Assumptions

- **No published releases exist.** Verified 2026-08-30: neither the current nor the former
  distribution name is present on the public index. This feature therefore takes the clean break
  permitted by FR-004 instead of a deprecation cycle, and MUST land before issue #40 publishes
  anything.
- **The console currently has no dependencies of its own** beyond the standard library, so the
  console extra is declared but initially empty. It is declared now rather than when a dependency
  first appears, because adding an extra later is a packaging change users must react to, whereas
  populating an already-declared extra is invisible to them. FR-011's guard is specified and tested
  now for the same reason; it is exercised by simulating the dependency's absence.
- **Message catalogs and locale handling stay in the core package for this feature.** Moving them is
  slice 015. This feature moves the console's own modules only, so the two slices do not overlap.
- **The gitignored `my-project/` scaffold directory is out of scope.** It holds no tracked files, so
  its removal is a local cleanup rather than a repository change; issues #62 and #67 are resolved
  outside the spec-driven flow. (This corrects the earlier plan comment on #63, which listed it
  as part of this slice.)
- **Reference-data file contents are moved verbatim.** Any change to a reference value would be a
  separate, individually reviewable change, since Constitution Principle III requires cited sources
  for such values.
- **The repository name, the console's user-visible text, and the CLI's behaviour are unchanged.**

## Out of Scope

- Relocating message catalogs or changing how errors carry their text (slice 015).
- Path-based CI job selection or test-selection tooling (slice 016).
- Creating placeholder namespaces for unimplemented processes (slice 017).
- Implementing any new process or operation (turning, welding, joining, forming).
- Publishing to a package index (issue #40).
- Any REST/HTTP interface (issue #63 defers this explicitly).
- The gitignored `my-project/` scaffold directory (issues #62/#67).

## Dependencies

- Constitution Principle IV (packaging and versioning), Principle VI (extensibility by design), and
  Principle VII (documentation and publishing) all constrain this feature directly.
- Slices 015, 016 and 017 of issue #63 depend on this feature's layout and MUST follow it.
- Issue #40 (publish) is blocked by this feature per the Assumptions above.

## Clarifications

### Session 2026-08-30

- Q: Should the process namespace be singular or plural? → **A: plural (`processes`)**. Issue #63
  writes it singular, but the level it replaces (`operations`) and the project's other collection
  packages are plural; FR-004 forbids an alias period, so the name is chosen for long-term
  consistency rather than fidelity to the issue's shorthand. Recorded in FR-001.
- Q: How should milling's sub-operations nest under the new structure? → **A: keep the
  sub-operation level** — end milling and face milling stay within milling. Flattening them to
  siblings of drilling would misrepresent the domain (both are milling) and would evict the helpers
  the two sub-operations share, which is churn this slice has no reason to take on. Recorded in
  FR-002.
- Q: Should the installation extras ship in this slice or be deferred? → **RESOLVED**: ship them in
  this slice, with the console extra declared but initially empty. Declaring an extra later is a
  packaging change users must react to; populating an already-declared one is invisible to them.
  Recorded in Assumptions rather than left open.
