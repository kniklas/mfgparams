# Phase 1 Data Model: Turning Combined-Constraint Modes & Machining Menu Auto-Hide

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This document extends `specs/019-turning-calculations/data-model.md` and
`specs/020-turning-feed-per-rotation/data-model.md` (the `CalculationMode` model this
feature adds two more, turning-only members to). Entities not mentioned here
(`WorkpieceMaterial`, `TurningTool`, `MaterialToolCompatibility`, `Configuration`,
`CalculationResult`'s existing fields, `ErrorInfo`'s existing codes) are unchanged and
not repeated — critically, **`CalculationResult` gains no new field** (research.md #1).

## CalculationMode (enum) — two new members

| Member | Value | Notes |
|---|---|---|
| `STANDARD` | `"standard"` | Unchanged. |
| `POWER_CONSTRAINED` | `"power-constrained"` | Unchanged. |
| `FIXED_RPM` | `"fixed-rpm"` | Unchanged. |
| `FEED_RATE_CONSTRAINED` | `"feed-rate-constrained"` | Unchanged. |
| `ROTATION_AND_FEED_CONSTRAINED` | `"rotation-and-feed-constrained"` | **NEW.** Spindle speed AND feed per workpiece rotation are both supplied directly by the caller (`target_rpm`, `target_feed_rate`), neither derived from the material's/tool's reference values (spec.md FR-001/FR-002). Turning-only. |
| `POWER_AND_FEED_CONSTRAINED` | `"power-and-feed-constrained"` | **NEW.** Available power AND feed per workpiece rotation are both supplied directly by the caller (`available_power`, `target_feed_rate`); spindle speed is solved to the highest value feasible within that power at that feed (spec.md FR-003/FR-004/FR-005). Turning-only. |

Drilling's and milling's own dispatch never construct either new member, and both
explicitly reject them with `UNSUPPORTED_MODE` if a caller supplies one directly
(research.md #7) — the same treatment `FEED_RATE_CONSTRAINED` already has.

## TurningOperation (request) — no new field

Extends `019-turning-calculations`/`020-turning-feed-per-rotation`'s
`TurningOperation`. The two new modes' required inputs are **all pre-existing
fields**, reused as-is (research.md #1):

| Field | Type | New usage |
|---|---|---|
| `target_rpm` | float \| None | Required (and used directly, never derived) when `mode == ROTATION_AND_FEED_CONSTRAINED` — same field `FIXED_RPM` already uses. Rejected as `MODE_CONFLICT` if supplied together with `POWER_CONSTRAINED`, `FEED_RATE_CONSTRAINED`, or `POWER_AND_FEED_CONSTRAINED` (unchanged mutual-exclusivity rule, `validate_mode_arguments`). |
| `available_power` | float \| None | Required, as a **hard constraint** (not advisory), when `mode == POWER_AND_FEED_CONSTRAINED` — same field `POWER_CONSTRAINED` already treats as a hard constraint. Optional/advisory when `mode == ROTATION_AND_FEED_CONSTRAINED` (spec.md FR-006), matching `STANDARD`/`FIXED_RPM`/`FEED_RATE_CONSTRAINED`'s existing treatment. |
| `target_feed_rate` | float \| None | Required when `mode == ROTATION_AND_FEED_CONSTRAINED` **or** `mode == POWER_AND_FEED_CONSTRAINED` — same field `FEED_RATE_CONSTRAINED` already uses; the reverse-conflict check (rejecting a stray `target_feed_rate` under any *other* mode) extends to cover both. Same unit handling as `020` (mm/rev METRIC, in/rev IMPERIAL, not unit-system-independent). |

**Validation** (extends `020-turning-feed-per-rotation/data-model.md`'s ordering — the
existing nine-step material/tool/geometry validation still runs first, unchanged;
mode-argument validation still runs after, mode-conflict checks before any mode's own
value-validity check — research.md #4):

- `ROTATION_AND_FEED_CONSTRAINED` requires **both** `target_rpm` and `target_feed_rate`;
  either missing or individually invalid (zero, negative, non-numeric, `NaN`,
  `Infinity`) is rejected under the existing `INVALID_TARGET_RPM`/
  `INVALID_TARGET_FEED_RATE` codes respectively — `target_rpm`'s own validity is
  checked first (research.md #4's deterministic ordering, inherited from parameter
  declaration order, not a new rule this feature invented).
- `POWER_AND_FEED_CONSTRAINED` requires **both** `available_power` and
  `target_feed_rate`; a missing `available_power` is `MODE_CONFLICT` (mirroring
  `POWER_CONSTRAINED`'s identical requirement), an invalid one is
  `INFEASIBLE_POWER_BUDGET`, and a missing/invalid `target_feed_rate` is
  `INVALID_TARGET_FEED_RATE` — the shared `available_power` check (via
  `validate_mode_arguments`) runs before the turning-local `target_feed_rate` check,
  same precedence rule.
- No new error code is introduced by this feature. Every failure path reuses an
  existing code: `INVALID_TARGET_RPM`, `INVALID_TARGET_FEED_RATE`, `MODE_CONFLICT`,
  `INFEASIBLE_POWER_BUDGET`, `CALCULATION_OVERFLOW`.

## TurningMetrics (internal calculation output) — no new field

Both new modes populate every existing `TurningMetrics` field
(`spindle_speed_rpm`, `feed_rate_mm_min`, `feed_per_rev_mm`, `machining_time_min`,
`cutting_force_n`, `torque_nm`, `power_kw`) exactly as every existing mode already
does — no new field, no new computed quantity.

## CalculationResult (public result) — no new field

Both new modes return the existing `CalculationResult` shape unchanged, including the
already-existing `feed_per_rotation` field (`020`). `mode` echoes
`ROTATION_AND_FEED_CONSTRAINED`/`POWER_AND_FEED_CONSTRAINED` as appropriate.

## Machining Menu (console TUI, internal) — visibility rule, not a new field

`SessionUI`/`_ViewState`'s existing `body_mode: Literal["tree", "configuration",
"about", "help"] | None` field gains no new value and no new field — only a new
*write site* (research.md #9): `view.body_mode = None` is set the moment an operation
is opened (`app.py`'s `_activate_tree_row()`), hiding the Machining tree dropdown
(whose own visibility is already gated on `body_mode == "tree"`). The existing
restore-on-exit logic (`view.body_mode = "tree" if ui.tree.expanded else None`, present
in both of the file's Escape handlers since `018-tui-splitpane-redesign`) needs no
change — `ui.tree.expanded` is never toggled while an operation is open, so it is
always `True` at the moment either handler runs after this change, correctly restoring
`body_mode = "tree"`. `view.tree_selected` (the "same state" selection position, per
spec.md's Assumptions) is likewise untouched by opening/closing an operation, already
preserved.

## `TurningSessionState` (console TUI, internal) — no new field

`screens/turning.py`'s `TurningSessionState` needs no new field: `target_rpm`,
`available_power`, and `target_feed_rate` already exist (from `019`/`020`) and are
reused directly for both new modes. `_set_mode()`'s existing clear-on-mode-switch
logic (clearing all three when the mode actually changes) applies unchanged — it is
already mode-generic, not per-mode-specific.
