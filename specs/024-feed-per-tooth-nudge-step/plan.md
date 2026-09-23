# Implementation Plan: Milling Feed-Per-Tooth Nudge Step

**Branch**: `024-feed-per-tooth-nudge-step` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/024-feed-per-tooth-nudge-step/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Give milling's existing `feed_per_tooth` `NumberRow` its own arrow-key
nudge `step` — 0.1 mm/tooth under METRIC, 0.001 in/tooth under IMPERIAL
(research.md #1) — instead of the shared `NUDGE_STEP` default (1.0
display unit) it currently falls back to. This reuses the per-row `step`
mechanism `020-turning-feed-per-rotation` already added to
`split_pane.NumberRow` for exactly this purpose; no new interaction
capability, field, entity, or `FieldId` is introduced. Unlike
`screens/turning.py` (which builds its custom-step field through its own
dedicated `_feed_rate_row()` factory), every milling row — including
`feed_per_tooth` — currently goes through one shared `_number_row()`
helper with no `step` parameter at all. The source change is adding an
optional `step` parameter to that helper (defaulting to the existing
`NUDGE_STEP`, so every other call site is unaffected) and passing a
unit-system-dependent value only at the `feed_per_tooth` call site.

## Technical Context

**Language/Version**: Python (>=3.9, unchanged — no new version requirement).

**Primary Dependencies**: None new. Reuses `split_pane.NumberRow`'s
existing `step` field (`020-turning-feed-per-rotation`), `mfgparams.console.i18n`
(existing `tui.label.feed_per_tooth` catalog entry, unchanged), and the
console's existing `prompt-toolkit`-based split-pane TUI.

**Storage**: N/A (stateless per-render UI constant, unchanged).

**Testing**: `pytest`, extending milling's existing TUI test suite
(`tests/unit/console/tui/`, `tests/integration/`) with a nudge-step
assertion for `feed_per_tooth` under both unit systems, mirroring the
equivalent test `020-turning-feed-per-rotation` added for
`target_feed_rate`.

**Target Platform**: Cross-platform CLI/TUI (unchanged), including
resource-constrained legacy hardware per Constitution Principle V.

**Project Type**: Single Python package (library + console front-end),
`src/` layout — no new project/subsystem; touches one existing file
(`screens/milling.py`).

**Performance Goals**: N/A — a constant-value change with no new
computation; negligible overhead, same as `020-turning-feed-per-rotation`'s
equivalent change.

**Constraints**: Same resource envelope as the rest of the console TUI
(Constitution Principle V); this is an interactive-TUI behavior change, so
Constitution Principle XIII (manual verification) applies — see
Constitution Check below.

**Scale/Scope**: One field (`feed_per_tooth`) in one screen
(`screens/milling.py`). No new `FieldId`, `CalculationMode`, entity, or
message-catalog key. Contrast with `020-turning-feed-per-rotation`, which
introduced a new mode and field alongside its nudge-step change — this
feature only supplies a value to an already-generic, already-shipped
mechanism.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Code Quality)**: The change is a `step=` keyword argument
  on an existing `NumberRow` construction, computed with the same
  `if state.unit_system is UnitSystem.METRIC else ...` shape
  `screens/turning.py::_feed_rate_row()` already uses — no new
  abstraction, no duplicated logic. PASS.
- **Principle II (Testing Standards)**: New unit/integration test(s)
  asserting `feed_per_tooth`'s row carries the correct `step` under each
  unit system and that `nudge_selected` moves its buffer by that step,
  mirroring the existing `target_feed_rate` step test; ≥90% coverage
  maintained. PASS (planned — `/speckit-tasks` enumerates test tasks
  before implementation tasks).
- **Principle III (Calculation Robustness & Accuracy)**: No calculation
  formula is touched — `feed_per_tooth`'s value, validation, and use in
  `calculate_end_milling()`/`calculate_face_milling()` are unchanged; only
  the UI nudge increment changes. The existing `Decimal`-safe nudge
  arithmetic in `nudge_selected()` (added for `020-turning-feed-per-rotation`
  specifically to handle sub-1.0 steps without binary-float drift) already
  covers this feature's step values with no further change needed. PASS.
- **Principle IV (Python Packaging & Versioning)**: No public API surface
  changes — `NumberRow.step` is an existing, already-optional field; this
  feature only supplies a non-default value for one internal row
  construction. No version bump beyond the standard PATCH-level UI-only
  change. PASS.
- **Principle V (Resource-Constrained Compatibility)**: No new dependency;
  O(1) constant, identical cost profile to every other row. PASS.
- **Principle VI (Extensibility by Design)**: Uses the already-shared,
  already-generic `step` mechanism exactly as designed — no
  operation-specific branching added to `split_pane.py`. PASS.
- **Principle VII (Documentation & Publishing)**: `docs/source/milling.rst`
  is checked for any prose describing the default nudge step and updated
  if it names one explicitly; tracked as a task. PASS (planned).
- **Principle VIII (Internationalization)**: No new user-facing text —
  the `feed_per_tooth` label already exists in the message catalog and is
  unchanged; only a numeric constant changes. N/A.
- **Principle IX (Automated Quality/Complexity/Security Gates)**: No CI
  gate configuration change; the changed function stays well within
  existing complexity thresholds (a two-branch step computation, same
  shape as the existing turning equivalent). PASS.
- **Principle X (Licensing & Author Rights)**: No change. N/A.
- **Principle XI (Multi-Agent Coding-Tool Consistency)**: No skill files
  (`.github/skills/**`) are touched by this feature. N/A.
- **Principle XII (Long-Lived Feature Branches for Multi-PR Work)**: This
  feature's scope (one row's `step` value in one file) is far smaller than
  `020-turning-feed-per-rotation`, which itself shipped as a single PR.
  Planned as a single PR. PASS.
- **Principle XIII (Manual Verification for Interactive & Reference-Fidelity
  Features, NON-NEGOTIABLE)**: This is an interactive-TUI behavior change
  (how the feed-per-tooth field responds to Left/Right arrow presses) —
  the constitution's manual-verification requirement applies regardless of
  whether the step arithmetic itself is also covered by an automated test
  (it is; Principle XIII does not treat that as a substitute). `tasks.md`
  MUST carry a distinct manual-verification task — a real-terminal walk of
  `quickstart.md`'s scenario, pressing the arrow keys and confirming the
  on-screen value moves by 0.1 mm/tooth (METRIC) and the researched
  IMPERIAL step — performed by the developer or a reviewer, not the
  implementing agent alone, per the principle's interactive-TUI case.
  PASS (planned — tracked as a task, to be confirmed complete by the user
  before this feature is considered done, per the standing
  confirm-manual-verification-scope practice from `022-tui-min-size-25x80`).

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/024-feed-per-tooth-nudge-step/
├── plan.md               # This file (/speckit.plan command output)
├── research.md           # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md         # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   └── cli-repl-feed-per-tooth-nudge-step-delta.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mfgparams/console/tui/screens/milling.py    # feed_per_tooth row factory gains step=
tests/unit/console/tui/                          # new/extended nudge-step assertion
tests/integration/                               # new/extended arrow-key integration assertion
docs/source/milling.rst                          # checked/updated if it names the old default step
```

**Structure Decision**: Single Python package (`src/mfgparams/`), `src/`
layout, unchanged. This feature touches one existing screen module and
its tests — no new module, package, or directory beyond this feature's
own `specs/024-feed-per-tooth-nudge-step/` documentation.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations. Table omitted.
