# Phase 0 Research: Turning Combined-Constraint Modes & Machining Menu Auto-Hide

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

No `[NEEDS CLARIFICATION]` markers were left by `/speckit-clarify` (spec.md's own
Clarifications section resolved the one open scope question — drilling/milling stay
out of scope). This document instead records the design decisions found by tracing
the actual, current (post-`020`-PR-#101) code, since both features build directly on
top of it.

## 1. Both new modes reuse `calculate_turning()`'s existing parameters — no new parameter needed

- **Decision**: `ROTATION_AND_FEED_CONSTRAINED` reuses the existing `target_rpm` and
  `target_feed_rate` parameters (from `FIXED_RPM` and `FEED_RATE_CONSTRAINED`
  respectively), both required simultaneously. `POWER_AND_FEED_CONSTRAINED` reuses the
  existing `available_power` (now a required hard constraint, exactly as
  `POWER_CONSTRAINED` already treats it) and `target_feed_rate` parameters, also both
  required simultaneously. `calculate_turning()`'s signature does not change at all.
- **Rationale**: Every input either mode needs already exists as a parameter with the
  exact intended meaning (a directly-supplied spindle speed, a hard power budget, a
  directly-supplied feed per rotation) — inventing new, differently-named parameters
  for the same quantities would duplicate meaning without adding any, and would break
  the "one field, one meaning" invariant `target_rpm`/`available_power` already have
  across `FIXED_RPM`/`POWER_CONSTRAINED`/`FEED_RATE_CONSTRAINED`. It also means
  `CalculationResult` needs no new field either: `spindle_speed_rpm`, `feed_per_rotation`,
  `machining_time`, `cutting_force`, `torque`, `power_required` are already populated
  identically for every mode.
- **Alternatives considered**: Distinct parameter names per new mode (e.g.
  `rotation_and_feed_target_rpm`) were rejected as pure duplication with no semantic
  gain — the caller is supplying the same physical quantity `target_rpm` already means,
  just alongside a different combination of other inputs than before.

## 2. `ROTATION_AND_FEED_CONSTRAINED` needs no new formula function at all

- **Decision**: Dispatch directly to the existing `calculate_turning_metrics_at_rpm()`,
  passing the caller's `target_rpm` as the explicit spindle speed and the caller's
  `target_feed_rate_mm` as the `feed_per_rev_mm` override — both parameters that
  function already accepts (the latter added by `020-turning-feed-per-rotation`
  specifically so `FEED_RATE_CONSTRAINED` could override the derived feed value).
- **Rationale**: `calculate_turning_metrics_at_rpm()` was already designed to take an
  explicit spindle speed and an optional explicit feed — this new mode simply supplies
  both instead of deriving either, which is exactly the function's existing contract.
  No new formula, no new file, zero duplicated arithmetic.
- **Alternatives considered**: A dedicated wrapper function (mirroring
  `calculate_turning_feed_rate_constrained_metrics`'s shape) was considered for
  naming/discoverability symmetry with the other three mode-specific wrapper
  functions, but rejected: it would add a function whose entire body is a single
  pass-through call with no logic of its own, which is not what those other wrappers
  do (each of them computes or derives something). `_compute_metrics()`'s own
  dispatch branch documents the mode/call-site mapping just as clearly without it.

## 3. `POWER_AND_FEED_CONSTRAINED` needs one new formula function, reusing the extracted spindle-speed helper

- **Decision**: Add `calculate_turning_power_and_feed_constrained_metrics()` to
  `formulas.py`, mirroring `calculate_turning_power_constrained_metrics()`'s existing
  shape exactly, with one difference: its "nominal" operating point is computed at the
  caller-supplied `target_feed_per_rev_mm` (via `calculate_turning_metrics_at_rpm(...,
  feed_per_rev_mm=target_feed_per_rev_mm)`), not at the material/tool-derived feed
  `calculate_turning_metrics()` would use. The nominal spindle speed itself still comes
  from `_derive_standard_spindle_speed_rpm()` (the helper `020`'s PR #101 review round 1
  extracted specifically to prevent this exact class of duplication). If the nominal
  power already fits the budget, return it as-is; otherwise scale the spindle speed
  down linearly (`n_adjusted = n0 * (Pavail / Pc0)`), identical algebra to
  `POWER_CONSTRAINED`'s existing derivation, since torque/cutting force are independent
  of spindle speed for a fixed feed/depth-of-cut/material/tool selection — a fact that
  holds regardless of whether the feed is derived or caller-supplied.
- **Rationale**: The physics is identical to `POWER_CONSTRAINED`'s; only the feed's
  *source* differs. Reusing `_derive_standard_spindle_speed_rpm()` rather than
  re-deriving the cutting-speed formula inline avoids reintroducing the exact
  duplication bug `020`'s first Copilot review round found and fixed
  (`formulas.py:277` in that PR — two independent copies of the same two-line
  derivation, silently divergeable by a future fix to one but not the other).
- **Alternatives considered**: Solving iteratively for the feasible spindle speed was
  rejected — the linear relationship between power and spindle speed at fixed feed
  makes the closed-form scaling exact and O(1), and iterating would be strictly worse
  on every axis (Principle V's legacy-hardware performance target, Principle I's
  no-unnecessary-complexity).

## 4. Validation: extend five existing `if` conditions rather than writing new branches

- **Decision**: In `validation.py`'s shared `validate_mode_arguments()`:
  - `POWER_AND_FEED_CONSTRAINED` joins `POWER_CONSTRAINED`'s existing branch
    (`if mode is CalculationMode.POWER_CONSTRAINED or mode is
    CalculationMode.POWER_AND_FEED_CONSTRAINED:`) — identical treatment: `target_rpm`
    supplied is `MODE_CONFLICT`, `available_power` missing is `MODE_CONFLICT`, invalid
    is `INFEASIBLE_POWER_BUDGET`.
  - `ROTATION_AND_FEED_CONSTRAINED` needs no new branch at all — it naturally reaches
    the existing catch-all fallback (currently commented `# mode is
    CalculationMode.FIXED_RPM`, to be re-commented to name both modes) which already
    does exactly what it needs: `target_rpm` is never a conflict (it is being supplied
    directly, not derived), `available_power` is advisory-only
    (`_validate_advisory_available_power`).
  - In turning's own `_validate_mode_inputs()` (`processes/machining/turning/__init__.py`):
    the reverse-direction conflict check (a stray `target_feed_rate` under the wrong
    mode) extends from `mode is not CalculationMode.FEED_RATE_CONSTRAINED` to exclude
    all three turning-only feed-accepting modes. The existing `if mode is
    CalculationMode.FIXED_RPM:` own-value-validity block (`validate_target_rpm`)
    extends to also cover `ROTATION_AND_FEED_CONSTRAINED`. The existing `if mode is
    CalculationMode.FEED_RATE_CONSTRAINED:` own-value-validity block
    (`validate_target_feed_rate`) extends to also cover both new modes.
- **Rationale**: This reuse is not just DRY — it automatically inherits the exact
  precedence order `020`'s PR #101 review round 1 fixed as a real bug (mode-conflict
  checks, including the shared `validate_mode_arguments()` call, run *before* any
  mode's own-value validity check, so a request supplying two conflicting mode-driving
  inputs at once is reported as `MODE_CONFLICT` even if one of those inputs also
  happens to be individually invalid). Writing new, separate branches for the two new
  modes would risk re-introducing that exact ordering bug from scratch; extending the
  existing conditions inherits the fix for free. It also resolves, without any new
  arbitrary rule, the "which of `target_rpm`/`target_feed_rate` is checked first when
  both are missing under `ROTATION_AND_FEED_CONSTRAINED`" question: since the
  `FIXED_RPM`-shared block runs before the `FEED_RATE_CONSTRAINED`-shared block
  (unchanged from today's code, both are independent `if`s not `elif`s), `target_rpm`'s
  own validity is always checked first, matching the parameter declaration order in
  `calculate_turning()`'s own signature — a deterministic, low-drama tie-break, not one
  this feature had to invent.
- **Alternatives considered**: Two brand-new, self-contained `if` branches (one per new
  mode) were considered for readability, but rejected: they would duplicate the exact
  logic already sitting in the shared/`FIXED_RPM`/`FEED_RATE_CONSTRAINED` branches, and
  duplicated validation logic is exactly what Principle I/VI ask reviewers to catch.

## 5. `_compute_metrics()` dispatch: two new branches, same shape as the existing four

- **Decision**: Add `if mode is CalculationMode.ROTATION_AND_FEED_CONSTRAINED:` (calls
  `calculate_turning_metrics_at_rpm()` per Decision #2, `CALCULATION_OVERFLOW` on
  `_reject_if_invalid` failure) and `if mode is
  CalculationMode.POWER_AND_FEED_CONSTRAINED:` (the existing `available_power_kw <= 0`
  →`INFEASIBLE_POWER_BUDGET` guard, then the new formula function from Decision #3,
  `INFEASIBLE_POWER_BUDGET` on `_reject_if_invalid` failure) — both mirroring
  `FIXED_RPM`'s and `POWER_CONSTRAINED`'s existing branch shapes exactly.
- **Rationale**: Consistent dispatch shape across all six modes; no new error code
  needed since both new modes' failure semantics exactly match an existing mode's
  (`FIXED_RPM`'s / `POWER_CONSTRAINED`'s respectively).

## 6. `_build_result()`'s feasibility-warning exclusion extends to the new hard-constraint mode

- **Decision**: The existing `if available_power_kw is not None and mode is not
  CalculationMode.POWER_CONSTRAINED:` feasibility-warning gate extends to also exclude
  `POWER_AND_FEED_CONSTRAINED` (`and mode is not
  CalculationMode.POWER_AND_FEED_CONSTRAINED`). `ROTATION_AND_FEED_CONSTRAINED` needs
  no change — it is already included in the advisory-warning path (per spec.md FR-006),
  exactly like `STANDARD`/`FIXED_RPM`/`FEED_RATE_CONSTRAINED` already are, since the
  existing condition is an exclusion list, not an inclusion list.
- **Rationale**: `POWER_AND_FEED_CONSTRAINED`'s `available_power` is a hard constraint
  the returned metrics already satisfy by construction (the solved spindle speed keeps
  `power_kw <= available_power_kw`), exactly like `POWER_CONSTRAINED`'s — an advisory
  "exceeds available power" warning would be spurious (and, on a floating-point
  boundary case, actively misleading) for a mode whose entire purpose is to already fit
  within that budget. This is the kind of one-line detail a review round would likely
  catch if missed (as multiple similar details were, across `020`'s own review rounds)
  — caught here during planning instead.

## 7. Drilling/milling gain the `UNSUPPORTED_MODE` guard for both new modes, proactively

- **Decision**: Both `drilling/__init__.py`'s and `milling/_calculate.py`'s existing
  `if mode is CalculationMode.FEED_RATE_CONSTRAINED:` → `UNSUPPORTED_MODE` rejection
  (added during `020`'s PR #101 review, round 1) extends to also reject
  `ROTATION_AND_FEED_CONSTRAINED` and `POWER_AND_FEED_CONSTRAINED`, in this feature's
  own initial implementation — not deferred to a follow-up review fix.
- **Rationale**: `020`'s PR #101 review found, the hard way, that a shared
  `CalculationMode` enum member is reachable through `calculate()`/
  `calculate_end_milling()`/`calculate_face_milling()`'s own public signatures
  regardless of which modes the console's own restricted mode list offers, and that an
  unhandled member silently falls through to a mislabeled standard-mode result rather
  than a structured error. Both new modes reach the exact same shared enum and the
  exact same unguarded fallthrough if this guard is not extended; doing so now, while
  the two existing precedent lines are already being read and understood for this
  feature, costs one boolean condition each and avoids repeating a finding that already
  cost a full review round once.
- **Alternatives considered**: Leaving it for a review round to catch again, matching
  `020`'s original (accidental) sequence — rejected as a known, avoidable repeat of a
  finding already on record in this very repository's history.

## 8. TUI: reuse every existing field-row closure and nudge step; two new mode-selector labels only

- **Decision**: `power_and_rpm_rows()` (`split_pane.py`) gains two new defaulted
  keyword parameters, `rotation_and_feed_constrained: bool = False` and
  `power_and_feed_constrained: bool = False`, with two new branches:
  `[rpm_row(), feed_rate_row(), power_row("tui.label.power", False)]` for the first
  (three rows — spindle speed and feed both required, power optional/advisory per
  FR-006) and `[feed_rate_row(), power_row("tui.label.power_required", True)]` for the
  second (two rows — feed required, power required). `turning.py`'s `rows_for()`
  passes these two new booleans through to `power_and_rpm_rows()`, reusing its
  existing `_rpm_row()`, `_feed_rate_row()`, and `_power_row()` closures completely
  unchanged — no new field, no new nudge-step decision (`_rpm_row()`'s default
  1.0 RPM step and `_feed_rate_row()`'s existing 0.1 mm/rev / 0.005 in/rev step, both
  from `020`, already apply). `turning.py`'s `_MODE_OPTION_KEYS` gains the two new
  mode-to-label-key mappings; `_set_mode()`'s existing clear-on-mode-switch logic
  (clearing `available_power`/`target_rpm`/`target_feed_rate` when the mode actually
  changes) needs no change, since it already applies uniformly to every mode
  transition, not per-mode-specific logic.
- **Rationale**: Every field these two modes need is a field the screen already knows
  how to render, validate-on-commit, and nudge; only the *combination* being offered is
  new. Reusing the closures verbatim is the direct continuation of `020`'s own
  `power_and_rpm_rows()` extension pattern (`feed_rate_constrained`/`feed_rate_row`),
  not a new pattern.
- **`_SPINDLE_SPEED_MODE_LABEL_KEYS` (`forms.py`) — required, not optional**: this dict
  lookup is a hard `KeyError` source for any unhandled mode, exactly as `020`'s own
  research.md #9 documented for `FEED_RATE_CONSTRAINED`'s addition. Both new modes MUST
  get an entry before this feature ships, or every result in either mode crashes the
  console's result rendering. `ROTATION_AND_FEED_CONSTRAINED` reuses `FIXED_RPM`'s
  existing catalog value ("user-specified" — the spindle speed genuinely is
  user-specified here too, not derived). `POWER_AND_FEED_CONSTRAINED` reuses
  `POWER_CONSTRAINED`'s existing catalog value ("adjusted to fit available power" — the
  spindle speed's derivation nature, being solved to a power budget, is identical even
  though the feed it is solved at is fixed rather than derived). Both reuses need only
  a new dict *key*, not a new catalog *value* (Constitution Principle VIII: reuse
  mode-generic wording rather than duplicating near-identical strings — the exact
  guidance `020`'s own FR-013 already established for this codebase).

## 9. Machining menu auto-hide: a one-line fix, not new state

- **Decision**: `app.py`'s `_activate_tree_row()` — the single call site for all three
  `_open_milling()`/`_open_drilling()`/`_open_turning()` invocations (confirmed: no
  other call site exists in the file) — gains one line immediately after opening the
  operation: `view.body_mode = None`. No new field on `SessionUI`/`_ViewState`, no
  change to `_open_milling`/`_open_drilling`/`_open_turning`'s own signatures.
- **Rationale, traced from the actual code**: the Machining tree's own floating
  dropdown is shown by a `ConditionalContainer` filtered on `view.body_mode == "tree"`
  (`_dropdown_float`, `app.py`), a condition entirely independent of
  `ui.open_operation`. `on_pane()`'s own docstring says this explicitly: *"`_ViewState.
  body_mode` can independently be `"tree"` *while* an operation is open (the float
  doesn't touch it, revision)"* — a deliberate prior decoupling, for a different reason
  (so `on_pane()` could distinguish "focus is on the operation" from "focus is on the
  tree" once both could coexist). That prior decoupling is exactly what leaves the
  Machining menu visible (rendered, positioned under the bar) at the same time as an
  operation's own floating window today — the bug this feature's User Story 3 reports.
  Setting `body_mode = None` on open reverses only the *visibility* side of that
  decoupling, not the state-tracking side `on_pane()` still needs
  (`ui.open_operation is not None` stays the source of truth for whether an operation
  is open).

  Critically, **the restore-on-exit behavior already exists** and needs no new code:
  both existing Escape handlers (`_escape_bar`'s defensive fallback and `_escape_body`'s
  primary path, the only two places `ui.open_operation` is ever set back to `None`)
  already contain `view.body_mode = "tree" if ui.tree.expanded else None` — written for
  Acceptance Scenario 5 of `018-tui-splitpane-redesign` ("land back at the menu bar/tree,
  not a blank body"), a different acceptance criterion from this feature's, but one
  whose logic happens to be exactly what FR-012 needs. Since `ui.tree.expanded` is never
  toggled while an operation is open (the only writes to it are in the bar-entry
  toggle handler and the tree-dropdown-close branch, neither reachable while
  `ui.open_operation is not None`), and an operation can only ever be opened while the
  tree is expanded (the user had to open it to select a row), `ui.tree.expanded` is
  always `True` at the moment either Escape handler runs after this change — so both
  already restore `body_mode = "tree"` correctly, with zero further changes.
  `view.tree_selected` (the tree's own highlighted-row position) is likewise never
  touched by opening or closing an operation, so FR-012's "in the same state" (per
  spec.md's Assumptions: same selection position) is already preserved by the existing
  code, not something this feature has to add.
- **Test impact**: `tests/integration/test_tui_navigation.py`'s
  `test_escaping_the_operation_pane_closes_it_and_reveals_the_tree_underneath` already
  exercises this exact open→escape sequence but does not currently assert
  `body_mode`'s value *while* the operation is open (only after closing it) — safe to
  extend with a new assertion at that point (`body_mode is None`) without touching any
  existing assertion. No other test in that file asserts `body_mode == "tree"`
  simultaneously with `open_operation is not None`, so no existing test needs to change
  meaning, only gain new coverage.
- **Alternatives considered**: Adding `ui.open_operation is None` to the
  `ConditionalContainer`'s own filter (`_dropdown_float`) instead of setting
  `body_mode = None` on open — rejected: it would make the tree's visibility depend on
  two independent pieces of state read in two different places (the filter and every
  `body_mode`-consuming binding elsewhere in the file), where the one-line fix keeps
  `body_mode` as the single source of truth for "is the Machining dropdown visible"
  that every other piece of this file already assumes it is.
