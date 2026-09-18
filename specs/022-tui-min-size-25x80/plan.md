# Implementation Plan: TUI Minimum Terminal Size 25x80

**Branch**: `022-tui-min-size-25x80` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-tui-min-size-25x80/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Lower `terminal_capability.MIN_LINES` from 30 to 25 (keeping `MIN_COLUMNS` at 80), restoring
the classic 80x25 terminal floor the 018-tui-splitpane-redesign feature raised away from.
`MIN_LINES`/`MIN_COLUMNS` are consumed by exactly one runtime call site
(`terminal_capability.check()`, gating `cli.py::main()`) and one parameterized, already-
locale-agnostic message template, so the numeric change itself is a one-line edit with no
further code required for FR-001–FR-004. The real risk, and the bulk of this plan, is FR-005/
FR-006: 018's own row-budget math put the Milling screen at 24-25 rows *before* this
feature's margin is removed, and Turning (added after 018) has never been measured at all.
Because this project's TUI tests assert state/rendered text, not layout fit or clipping
(Principle XIII), the only way to know whether any of the six menu-reachable screens
(Drilling, Milling, Turning, Configuration, About, Help) actually fits in 25 rows is to run
them on a real 80x25 terminal and, if a screen doesn't fit, compact its rendering until it
does. That manual pass — and any compaction work it turns up — is the actual deliverable
here, not just the constant edit.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python >=3.9 (existing project requirement, `pyproject.toml`)

**Primary Dependencies**: `prompt-toolkit>=3.0,<4.0` (existing `console` extra; this feature
touches only its consumers, not the dependency itself)

**Storage**: N/A

**Testing**: `pytest` — existing unit test (`tests/unit/console/tui/test_terminal_capability.py`)
and integration test (`tests/integration/test_tui_terminal_too_small.py`) both assert against
the *old* 80x30 floor and MUST be updated to the new 80x25 floor; plus a required manual
walkthrough per Principle XIII (see Constitution Check) that automated tests structurally
cannot substitute for.

**Target Platform**: Any terminal/console `mfgparams` already targets (Principle V's legacy/
low-power hardware profile), specifically now including terminals reporting exactly 80
columns x 25 lines.

**Project Type**: Single project (existing `src/mfgparams` console/TUI application) — no new
project or module boundary.

**Performance Goals**: N/A — no new computation; this is a threshold value and (if needed)
layout-density change, not a hot path.

**Constraints**: `MIN_COLUMNS` MUST remain 80 (unchanged); `MIN_LINES` MUST become 25; every
screen reachable from the main menu (Drilling, Milling, Turning, Configuration, About, Help)
MUST render without clipping/overlap at exactly 80x25, per FR-005/FR-006 — this is the
constraint that may require layout compaction, not just the constant edit.

**Scale/Scope**: One constant change (`terminal_capability.py`), two existing test files to
update to the new floor value, and up to six existing TUI screens to audit (and, only where
manual verification finds a shortfall, compact) for fit at 80x25. No new screens, entities,
or public interfaces.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| I. Code Quality | Yes | Scope is a one-line constant edit plus, only if manual verification finds a shortfall, targeted rendering-density tweaks to existing, already-reviewed screen modules. No new abstractions, no god-functions. PASS. |
| II. Testing Standards | Yes | `test_terminal_capability.py` and `test_tui_terminal_too_small.py` assert the *old* 80x30 boundary values and MUST be updated to 80x25 (regression-test-style: old-floor values become the new "should now succeed" case, new boundary values become the new "should still fail" case) so the floor change itself stays covered by CI. PASS, pending the task updates below. |
| III. Calculation Robustness | No | No calculation logic touched. N/A. |
| IV. Packaging & Versioning | No | No public API/package surface change. N/A. |
| V. Resource-Constrained Compatibility | Yes | This feature *is* the compatibility fix — aligning the floor to the terminal size most associated with legacy/low-power hardware. PASS, is the point of the change. |
| VI. Extensibility | No | No new operation/module. N/A. |
| VII. Documentation & Publishing | No | No new public-facing docs surface; existing docs already describe `MIN_COLUMNS`/`MIN_LINES` generically, not the literal value. N/A. |
| VIII. Internationalization | Yes | The unsupported-terminal message (`console.tui_unavailable.reason.too_small`) is already parameterized with `{min_columns}`/`{min_lines}` — no new user-facing string, no catalog edit needed, so the new floor value is automatically reflected in every locale (FR-004) without translation work. PASS. |
| IX. Automated Quality/Security Gates | Yes | Existing CI gates (lint, type-check, complexity, security, tests) apply unchanged; this change is far below any complexity/MI threshold. PASS. |
| X. Licensing | No | N/A. |
| XI. Multi-Agent Consistency | No | No skill/agent-instruction file touched. N/A. |
| XII. Long-Lived Feature Branches | No | Small enough for a single pull request; no long-lived integration branch needed. N/A. |
| XIII. Manual Verification (NON-NEGOTIABLE) | Yes | This is exactly the case this principle targets: an interactive TUI change whose correctness (does content fit/clip at the new floor) cannot be observed by this project's state/text-only TUI test strategy. `tasks.md` (Phase 2) MUST carry a distinct, named manual-verification task — walking every menu-reachable screen (Drilling, Milling, Turning, Configuration, About, Help) on a real 80x25 terminal per `quickstart.md` — separate from and in addition to the automated test-update tasks, and that task MUST be completed, with any compaction work it surfaces (FR-006) also completed, before the feature is considered done. GATE SATISFIED BY DESIGN — enforced at the tasks phase, not skippable here. |

No violations requiring justification. Complexity Tracking table below is not needed.

**Post-Phase-1 re-check**: Design work (research.md, data-model.md, contracts/,
quickstart.md) surfaced no new principle concerns and resolved the two open questions the
initial pass flagged: (a) Principle VIII is satisfied without any catalog edit, confirmed by
reading `locales/en.py` directly rather than assuming (research.md #1); (b) Principle XIII's
manual-verification task now has a concrete target (`quickstart.md`) and a scoped
FR-006 compaction boundary (research.md #3: only Drilling/Milling/Turning are actually at
clipping risk; Configuration/About/Help/the Machining tree already handle overflow via
existing scroll support, confirmed by reading `app.py`'s layout code directly). Gate
re-confirmed PASS.

**Post-implementation correction (Copilot review, PR #103)**: the Post-Phase-1 re-check
above, and this section's own row-only framing throughout, assessed only *vertical* fit risk
(row-clipping within an operation screen) — it never considered whether a dropdown's
*horizontal* position/width could overflow the 80-column floor. Manual verification (T008)
found exactly that: Help, the rightmost bar entry, underflowed its own width floor by one
column at 80 columns, unrelated to any operation screen's row budget and pre-existing rather
than introduced by this feature's `MIN_LINES` change (research.md #3's correction). Fixed in
`src/mfgparams/console/tui/app.py` (`_HELP_DROPDOWN_WIDTH`'s floor narrowed from 40 to 36),
not in a `screens/*.py` module as the Project Structure section below originally scoped all
layout work to. Principle XIII's gate is not weakened by this miss — the manual-verification
task is exactly the mechanism that caught what this plan's static analysis didn't — but the
Project Structure section's file list is corrected below to reflect where the fix actually
landed, and data-model.md is corrected the same way.

## Project Structure

### Documentation (this feature)

```text
specs/022-tui-min-size-25x80/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mfgparams/console/
├── cli.py                          # main() gate; consumes MIN_COLUMNS/MIN_LINES (unchanged)
├── tui/
│   ├── terminal_capability.py      # MIN_LINES: 30 -> 25 (the FR-001/FR-002 edit)
│   ├── app.py                      # SessionUI / menu bar / Machining tree wiring; ACTUAL FIX LANDED HERE:
│   │                                # _HELP_DROPDOWN_WIDTH narrowed (40->36) — a pre-existing column-width
│   │                                # underflow in the rightmost bar-entry dropdown, found by T008, not
│   │                                # anticipated by this plan's row-only risk analysis (post-implementation
│   │                                # correction above)
│   └── screens/
│       ├── drilling.py             # FR-005/FR-006 fit audit + possible compaction (no scroll fallback, research.md #3)
│       ├── milling.py              # FR-005/FR-006 fit audit + possible compaction (highest a-priori risk, research.md #4)
│       ├── turning.py              # FR-005/FR-006 fit audit + possible compaction (never measured before)
│       ├── configuration.py        # FR-005 open+scroll audit only — already scrollable, research.md #3
│       ├── about.py                # FR-005 open audit only — trivially short content
│       ├── help.py                 # FR-005 open audit only — content itself was fine; the bug found by T008
│       │                            # was in app.py's dropdown positioning, not this file
│       └── split_pane.py           # shared split-pane rendering the operation screens use
└── locales/en.py                    # console.tui_unavailable.* — already parameterized, no edit expected

tests/
├── unit/console/tui/test_terminal_capability.py   # update 80x30 boundary assertions to 80x25
├── unit/console/tui/test_dropdown_layout.py       # NEW (post-implementation correction above): regression
│                                                    # guard for the app.py dropdown-width underflow — not
│                                                    # anticipated by this plan, added after T008 found it
├── integration/test_tui_terminal_too_small.py     # update 80x30 boundary assertions to 80x25; also tightened
│                                                    # to assert the full detected-size/minimum message text,
│                                                    # not loose digit substrings (Copilot review, PR #103)
└── integration/test_console_repl_removed.py       # mentions terminal_capability in comments only; no edit expected
```

**Structure Decision**: Single project (existing layout, Option 1) — this feature adds no new
module, service, or directory. All changes land inside the existing
`src/mfgparams/console/tui/` package and its test counterparts above (one new unit test file,
added post-implementation per the correction noted in Constitution Check above).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — this table is intentionally empty.
