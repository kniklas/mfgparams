# Phase 1 Data Model: Process Namespaces and Installation Extras

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-08-30

This feature introduces no runtime data structures. Its "model" is the **namespace hierarchy** and
the **installation surface** — both of which are contracts users depend on, so they are modelled
here with the same rigour a data structure would get.

No dataclass, no schema, and no bundled reference-data value changes. `WorkpieceMaterial`,
`DrillingTool`, `MillingTool`, `CalculationResult`, `ErrorInfo`, `Configuration` and every TOML
schema are carried across unmodified (FR-003).

---

## Entities

### Process

A manufacturing process. Groups one or more operations and owns nothing itself.

| Attribute | Value |
|---|---|
| Identity | Package name under `mfgparams.processes` |
| Implemented | `machining` (only) |
| Deferred | turning, welding, joining, forming — slice 017, issue #63 |
| Owns | Nothing directly; a namespace with a module docstring only |
| Rule | A new process MUST be addable without editing any existing process (FR-006) |

### Operation

A specific operation within a process. The unit that owns calculation logic.

| Attribute | Value |
|---|---|
| Identity | Package name under a process, e.g. `…machining.drilling` |
| Implemented | `drilling`, `milling` |
| Owns | Formulas, tool definitions, bundled reference data, operation-specific validation |
| Rule | Operations MUST NOT import each other; shared behaviour lives at the package root (Principle VI) |

### Sub-operation

A variant within an operation that shares the operation's formula core but has its own tools,
labelling, and reference data. Retained per the resolved FR-002 clarification.

| Attribute | Value |
|---|---|
| Identity | Package name under an operation, e.g. `…machining.milling.end_milling` |
| Implemented | `end_milling`, `face_milling` (milling only) |
| Shares | `milling/_shared.py`, `_calculate.py`, `_tool_registry.py` |
| Rule | Drilling has no sub-operation level; the level exists only where variants share a formula core |

### Installation extra

A named optional dependency group requested at install time. Gates **dependencies only** — never
modules (research.md #2).

| Extra | Contents | Notes |
|---|---|---|
| *(none)* | `tomli` on Python < 3.11 | Default install; calculation API fully usable |
| `console` | *(empty on delivery)* | Declared now so populating it later is invisible to users |
| `all` | Every other runtime extra | Convenience alias required by issue #63 |
| `test`, `dev` | unchanged | Pre-existing development extras, untouched by this feature |

### Console entry point

The two invocation forms, both of which must keep working (FR-012).

| Form | Resolves to | Behaviour without console dependencies |
|---|---|---|
| `mfgparams` (console script) | `mfgparams.__main__:main` | Actionable message, non-zero exit (FR-011) |
| `python -m mfgparams` | `mfgparams/__main__.py` | Identical to the above |

---

## Namespace migration map

Every path below is a `git mv` **except the first row**, and contents change only where an import line names a moved module. The exception is footnote 1's: `operations/__init__.py` is a docstring-only registry placeholder whose text describes the grouping it is being moved out of, so it is rewritten rather than carried over — delivered as a delete plus an add, not a rename. `git log --follow` will not cross that boundary, and T008's "confirm `git status` shows the moves as renames" applies to every row but this one.

| Before | After |
|---|---|
| `mfgparams/operations/__init__.py` | `mfgparams/processes/machining/__init__.py` ¹ |
| `mfgparams/operations/drilling/` | `mfgparams/processes/machining/drilling/` |
| `mfgparams/operations/drilling/data/tools.toml` | `mfgparams/processes/machining/drilling/data/tools.toml` |
| `mfgparams/operations/milling/` | `mfgparams/processes/machining/milling/` |
| `mfgparams/operations/milling/end_milling/` | `mfgparams/processes/machining/milling/end_milling/` |
| `mfgparams/operations/milling/end_milling/data/tools.toml` | `…/machining/milling/end_milling/data/tools.toml` |
| `mfgparams/operations/milling/face_milling/` | `mfgparams/processes/machining/milling/face_milling/` |
| `mfgparams/operations/milling/face_milling/data/tools.toml` | `…/machining/milling/face_milling/data/tools.toml` |
| `mfgparams/cli.py` | `mfgparams/console/cli.py` |
| — | `mfgparams/processes/__init__.py` (new) |
| — | `mfgparams/console/__init__.py` (new) |
| — | `mfgparams/console/__main__.py` (new) |

¹ The existing `operations/__init__.py` is a docstring-only registry placeholder. Its text describes
the operation-first grouping it is being moved out of, so it is rewritten rather than carried
verbatim — the one file in the move whose content change is expected.

**Unmoved** (cross-cutting, stay at the package root per Principle VI): `models.py`, `units.py`,
`validation.py`, `registry.py`, `registry_config.py`, `config.py`, `logging_setup.py`, `i18n.py`,
`locales/`, `data/materials.toml`.

`i18n.py` and `locales/` stay in core **in this slice only**; slice 015 relocates them, subject to
the constraint in research.md #4.

---

## Test tree migration map (FR-014)

| Before | After |
|---|---|
| `tests/unit/operations/drilling/` | `tests/unit/processes/machining/drilling/` |
| `tests/unit/operations/milling/` | `tests/unit/processes/machining/milling/` |
| `tests/unit/operations/milling/end_milling/` | `tests/unit/processes/machining/milling/end_milling/` |
| `tests/unit/operations/milling/face_milling/` | `tests/unit/processes/machining/milling/face_milling/` |
| `tests/unit/shared/`, `tests/unit/performance/` | unchanged (cross-cutting) |
| `tests/contract/`, `tests/integration/` | unchanged locations; import lines only |

`tests/contract/` and `tests/integration/` are organised by user-facing contract rather than by
source module, so mirroring does not apply to them — FR-014's mirroring requirement is satisfied by
the unit tree, which is the one organised by module.

---

## Validation rules

| Rule | Source | Enforced by |
|---|---|---|
| No calculation result changes | FR-003 | Existing contract suite, moved unedited apart from imports |
| Public top-level names unchanged | FR-005 | Existing public-surface assertions in the contract suite |
| Core never imports console | FR-008 | New static AST test + `sys.modules` runtime assertion |
| Old paths unreachable and unreintroducible | FR-004, FR-017 | New static tracked-path-and-content test |
| Bundled data present in built wheel at new paths, absent at old | FR-015 | Extended `packaging`-marked build-and-inspect assertions |
| Console guard message is catalogued, and stays in core | FR-011, Principle VIII | [console-entry-contract.md](./contracts/console-entry-contract.md) |
