# Contract: Package Layout

**Feature**: [../spec.md](../spec.md) | **Requirements**: FR-001, FR-002, FR-004, FR-005, FR-006, FR-008, FR-017

The importable layout is a public contract: FR-004 forbids aliases, so every path here is the *only*
way to reach what it names, and changing one is a breaking change.

## Public surface (unchanged by this feature — FR-005)

`mfgparams` continues to export exactly these names, with unchanged signatures and semantics:

```
calculate                 calculate_end_milling      calculate_face_milling
list_tools                list_end_mill_tools        list_face_mill_tools
list_materials            list_material_types
UnitSystem                CalculationMode            CalculationResult
ErrorInfo                 MachiningOperation         MillingSubOperation
```

Code importing only from `mfgparams` is unaffected by this feature. This is the surface most users
depend on, and holding it steady is what keeps a namespace reorganisation from being a user-visible
break.

## Process-qualified paths (new — FR-001, FR-002)

```
mfgparams.processes
mfgparams.processes.machining
mfgparams.processes.machining.drilling
mfgparams.processes.machining.drilling.formulas
mfgparams.processes.machining.drilling.tools
mfgparams.processes.machining.milling
mfgparams.processes.machining.milling.end_milling
mfgparams.processes.machining.milling.end_milling.formulas
mfgparams.processes.machining.milling.end_milling.tools
mfgparams.processes.machining.milling.face_milling
mfgparams.processes.machining.milling.face_milling.formulas
mfgparams.processes.machining.milling.face_milling.tools
```

Modules prefixed `_` (`milling/_shared.py`, `_calculate.py`, `_tool_registry.py`) are internal and
carry no compatibility promise.

## Withdrawn paths (FR-004)

Every `mfgparams.operations.*` path is withdrawn with no alias, shim, or deprecation period. Nothing
in the repository may reference one, and FR-017's static check enforces this against both file
contents and tracked file paths.

## Layering rules

| Rule | Direction | Enforcement |
|---|---|---|
| Console may import core | `console` → root, `processes` | Unrestricted |
| Core must not import console | `processes`, root ↛ `console` | Static AST test + `sys.modules` assertion (FR-008) |
| Operations must not import each other | `drilling` ↛ `milling` | Review; no automated check added by this feature |
| Cross-cutting code stays at the root | — | `models`, `units`, `validation`, `registry`, `registry_config`, `config`, `logging_setup`, `i18n`, `locales` |

**Sole exemption to the core→console rule**: `mfgparams/__main__.py`, because `python -m mfgparams`
requires that exact location. Its console import MUST be inside the function body, never at module
scope, so importing `mfgparams` still does not import the console. The `sys.modules` assertion is
what makes this exemption safe rather than a hole.

## Extension rule (FR-006)

A new process is added as `mfgparams/processes/<name>/` with its own operations. Adding one MUST NOT
require editing `machining` or any of its descendants. Adding an operation to an existing process
MUST NOT require editing its sibling operations.
