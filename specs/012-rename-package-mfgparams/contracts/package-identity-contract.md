# Contract: Package Identity

This project's external interface is the library's importable API and its CLI entry point —
there is no network/service API. This contract states what a consumer (a `pip install` user, a
script importing the library, or CI tooling) can rely on before and after this rename.

## Before this feature ships

| Surface | Value |
|---|---|
| `pip install <x>` | `pip install machine-calc` |
| `import <x>` | `import machine_calc` |
| CLI command | `machine-calc` |
| Version accessor | `machine_calc.__version__` |

## After this feature ships

| Surface | Value |
|---|---|
| `pip install <x>` | `pip install mfgparams` |
| `import <x>` | `import mfgparams` |
| CLI command | `mfgparams` |
| Version accessor | `mfgparams.__version__` |

## Guarantees

- **G1 — No dual availability**: `machine-calc`/`machine_calc` MUST NOT remain installable or
  importable once this feature ships (FR-006: no alias/shim). A consumer either uses the old
  name (pre-rename releases only) or the new name (this release forward) — never both from the
  same release.
- **G2 — Behavior-identical surface**: every public symbol importable from the top-level package
  today (see `src/machine_calc/__init__.py`'s exports: `calculate`, `list_tools`,
  `list_material_types`, `list_materials`, the milling entry points, and the model types) MUST
  remain importable, with identical signatures and return values, from `mfgparams` after the
  rename (FR-004). Only the package name they're imported through changes.
- **G3 — CLI behavior-identical**: running the renamed CLI command MUST produce identical
  prompts, calculations, and output to running `machine-calc` today, for the same inputs
  (FR-004, spec User Story 1 Acceptance Scenario 2).
- **G4 — One version source**: `mfgparams.__version__` remains the single source of truth for
  the package version (Constitution Principle IV); no version string is duplicated elsewhere.
- **G5 — Historical releases untouched**: previously published `machine-calc` releases on PyPI
  are left exactly as they are; this contract governs new releases only (spec Edge Cases).

## Non-goals of this contract

- It does **not** cover the GitHub repository's own name/URL (`kniklas/machine-calc`) — that is
  explicitly out of scope for this feature (spec Clarifications) and is a separate, future
  contract change if/when the repository itself is renamed.
- It does **not** cover the local `my-project/` scaffold directory — tracked separately in
  [issue #67](https://github.com/kniklas/machine-calc/issues/67).

## Verification

Satisfied by:
- `tests/contract/*` (existing contract suite) passing unmodified in substance — only their
  `import mfgparams` statements change — proving G2/G3.
- The new static reference-check test (`research.md` item 4) proving G1 and the absence of
  stray old-name references anywhere in scope.
- A local `pip install .` + `mfgparams --help` (or equivalent smoke invocation) proving the CLI
  entry point (G3) and version accessor (G4) work end-to-end (see `quickstart.md`).
