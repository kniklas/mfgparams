# Phase 0 Research: Turning Feed Rate Per Rotation & Constrained Mode

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-12

This document resolves the technical unknowns needed before Phase 1 design. It
builds directly on `specs/019-turning-calculations` (turning's existing
formulas, validation, TUI screen) and `specs/002-constrained-calculation-modes`/
`specs/010-milling-calculation-modes` (the shared `CalculationMode`
infrastructure this feature extends with a fourth, turning-only member).
Settled topics from those features (Python version, dependencies, i18n
mechanism, formula citation, message-catalog split between
`mfgparams.locales.en` and `mfgparams.console.locales.en`) are not revisited.

## 1. Surfacing feed-per-rotation: extend `TurningMetrics`, don't recompute it

- **Decision**: `turning/formulas.py::calculate_turning_metrics_at_rpm()`
  already computes `feed_per_rev_mm = material.reference_feed_per_rev_mm *
  tool.feed_factor` as a local variable on every call, in every mode — it is
  simply never returned. Add a `feed_per_rev_mm: float` field to the
  `TurningMetrics` dataclass and return the already-computed local variable
  in it, at zero additional computation cost.
- **Rationale**: Per the resolved Clarification (spec.md), the new
  feed-per-rotation value is additive, not a redefinition of the existing
  `feed_rate_mm_min`/`feed_rate` field. Since the per-rotation value is
  already computed internally for every mode (it is the very quantity
  `feed_rate_mm_min` is derived from: `feed_rate_mm_min = spindle_speed_rpm *
  feed_per_rev_mm`), surfacing it is a matter of not discarding a value
  already in hand, not a new formula.
- **Alternatives considered**: Recomputing `feed_per_rotation` at the
  orchestration layer (`turning/__init__.py`) from `feed_rate` and
  `spindle_speed_rpm` (`feed_rate / spindle_speed_rpm`) was rejected — it
  would reintroduce a division (and its zero-spindle-speed edge case) for a
  value the formula layer already has exactly, and would duplicate unit
  conversion logic that `_build_result()` already applies uniformly to every
  other metric.

## 2. Feed-rate-constrained mode: one new parameter on the existing at-RPM helper, one new thin wrapper

- **Decision**: Give `calculate_turning_metrics_at_rpm()` one new optional
  parameter, `feed_per_rev_mm: float | None = None`. When `None` (every
  existing call site, unchanged), it derives `feed_per_rev_mm` from
  `material`/`tool` exactly as today. When supplied, it uses that value
  directly instead. Add one new thin wrapper,
  `calculate_turning_feed_rate_constrained_metrics(diameter_mm,
  depth_of_cut_mm, length_of_cut_mm, material, tool,
  target_feed_per_rev_mm)`, which derives spindle speed exactly as
  `calculate_turning_metrics()` (standard mode) does — from the material's
  and tool's reference cutting speed and the diameter — and then delegates to
  `calculate_turning_metrics_at_rpm(..., feed_per_rev_mm=target_feed_per_rev_mm)`.
- **Rationale**: spec.md FR-005 requires feed-rate-constrained mode to derive
  spindle speed "exactly as standard mode does" and to compute every other
  metric from that spindle speed combined with the supplied feed rate. The
  existing `calculate_turning_metrics_at_rpm()` is already the single place
  every mode's shared arithmetic (feed rate → machining time → cutting force
  → torque → power) lives; giving it an optional feed-per-rotation override
  reuses that arithmetic verbatim rather than duplicating it a fourth time,
  consistent with Constitution Principle I (no duplicated logic) and the
  precedent `019-turning-calculations` itself set for `POWER_CONSTRAINED`/
  `FIXED_RPM` (both are also thin callers of the same at-RPM helper).
- **Alternatives considered**: A fourth, fully independent formula function
  duplicating the feed-rate→time→force→torque→power chain was rejected as
  exactly the kind of duplicated cross-cutting arithmetic Constitution
  Principle I and VI exist to prevent. Overloading `calculate_turning_metrics()`
  (standard mode's own function) with an optional feed override, instead of
  adding a new named wrapper, was rejected as confusing — "standard mode with
  an override" is a different concept from feed-rate-constrained mode and
  deserves its own name for callers and tests to key off of.

## 3. `CalculationMode` gains a fourth member, scoped to turning by convention, not by type

- **Decision**: Add `FEED_RATE_CONSTRAINED = "feed-rate-constrained"` to the
  shared `CalculationMode` enum (`src/mfgparams/models.py`). Extend the
  shared `validate_mode_arguments()` (`src/mfgparams/validation.py`) with an
  explicit branch for it: a supplied `target_rpm` is rejected as
  `MODE_CONFLICT` (mirroring `POWER_CONSTRAINED`'s rejection of a
  simultaneously-supplied `target_rpm`), and `available_power` is
  type/finiteness-checked as an advisory value via the existing
  `_validate_advisory_available_power()` helper (mirroring `STANDARD`/
  `FIXED_RPM`). Neither operation's own dispatch (`drilling/__init__.py::
  _compute_metrics`, `milling/_calculate.py`) gains a `FEED_RATE_CONSTRAINED`
  calculation branch, so neither can actually produce a feed-rate-constrained
  result (FR-014's scoping) — but each *does* gain a small, explicit
  rejection of the mode in its own `_validate_mode_inputs()` (see the
  "Consequence found by review, then fixed" note below): the enum member
  being merely unhandled, rather than actively rejected, left drilling and
  milling free to silently compute a mislabeled standard-mode result
  instead, which a Copilot review on this PR correctly treated as a real
  defect rather than out-of-scope polish. This guard is operation-local
  (each function's own `_validate_mode_inputs()`), not a further edit to
  the shared `validate_mode_arguments()` above, so it does not reopen the
  cross-cutting-concern question this decision addresses.
- **Rationale**: `CalculationMode` and `validate_mode_arguments()` are
  already explicitly operation-agnostic, shared infrastructure — exactly the
  kind of "cross-cutting concern" Constitution Principle VI requires to live
  in one place rather than per-operation. Extending the enum and its one
  shared validator is the same pattern `010-milling-calculation-modes` used
  to extend mode support to milling without touching drilling's own files;
  here the new member is turning-only, so only turning's own dispatch
  (`turning/__init__.py`) gains a branch that constructs/consumes it.
  Leaving `validate_mode_arguments()` un-updated for the new member was
  rejected outright: its existing `if/elif/else` structure treats "anything
  that isn't `STANDARD` or `POWER_CONSTRAINED`" as `FIXED_RPM`, so an
  unhandled `FEED_RATE_CONSTRAINED` value would silently be validated as if
  it were `FIXED_RPM` — wrong (it would never check the new
  `target_feed_rate` parameter this validator doesn't know about) and unsafe
  to leave un-covered.
- **Consequence found by review, then fixed**: `calculate()` (drilling) and
  `calculate_end_milling()`/`calculate_face_milling()` (milling) are shipped
  public library functions accepting the shared `CalculationMode` enum
  directly — not gated by the console, which only ever offers each
  operation's own mode list. A caller passing
  `mode=CalculationMode.FEED_RATE_CONSTRAINED` to any of them is therefore a
  reachable call shape, not a hypothetical one: an initial draft of this
  feature assumed otherwise (see below) and left it unhandled, which a
  Copilot review on this PR correctly flagged — `validate_mode_arguments()`
  would validate the request as described above, but neither operation's
  own dispatch had a matching branch, so it silently fell through to that
  operation's `else: standard` branch and computed a **standard**-mode
  result while still echoing `mode=FEED_RATE_CONSTRAINED` back to the
  caller, mislabeling the result. Fixed by adding an explicit
  `FEED_RATE_CONSTRAINED` rejection (`UNSUPPORTED_MODE`) as the first check
  in drilling's and milling's own `_validate_mode_inputs()` — a small,
  operation-local addition, not the shared `validate_mode_arguments()`
  edit Constitution Principle VI and this feature's Assumptions still rule
  out, since the rejection is specific to each unsupporting operation
  rather than a cross-cutting concern.

## 4. `CalculationResult` gains `feed_per_rotation`, appended last (positional-construction precedent)

- **Decision**: Add `feed_per_rotation: float | None = None` to
  `CalculationResult` (`src/mfgparams/models.py`), declared after the
  existing `cutting_force` field — the same "declared last, with a default,
  after every pre-existing field" placement `material_removal_rate` and
  `cutting_force` themselves already established, so any existing
  positional construction (drilling/milling code, tests) keeps working
  unchanged.
- **Rationale**: Per the resolved Clarification, this is an additive,
  turning-specific field, not a redefinition of `feed_rate`. Mirroring the
  exact placement convention `019-turning-calculations` used for
  `cutting_force` (itself mirroring `009-milling-calculations`'s
  `material_removal_rate`) keeps the pattern consistent: `None` for
  drilling and milling, populated for turning on success, `None` for
  turning on error — identical shape to `cutting_force`.
- **Alternatives considered**: A separate, turning-only result type instead
  of extending the shared `CalculationResult` was rejected — it would break
  FR-016-style identical-shape guarantees and the console's
  operation-agnostic result-rendering code path, for no benefit over
  reusing the established additive-field pattern.

## 5. New error code: `INVALID_TARGET_FEED_RATE`

- **Decision**: Add one genuinely new validator,
  `validate_target_feed_rate(target_feed_rate, locale)`
  (`src/mfgparams/validation.py`), byte-for-byte mirroring
  `validate_target_rpm()`'s shape: a supplied value must be a positive,
  finite number (`_is_positive_finite_number()`, reused unchanged); zero,
  negative, non-numeric, `NaN`, or `Infinity` values are rejected under a
  new `INVALID_TARGET_FEED_RATE` code with a new
  `error.invalid_target_feed_rate` catalog entry
  (`src/mfgparams/locales/en.py`); `None` is not itself an error here (a
  missing value in feed-rate-constrained mode is reported by the caller,
  mirroring `validate_target_rpm()`'s own documented division of
  responsibility). No additional maximum/minimum bound or config override is
  introduced — mirroring `target_rpm`'s explicit "no additional range
  validation beyond finiteness and positivity" decision
  (`002-constrained-calculation-modes`), since a feed rate per rotation, like
  a spindle speed, has no natural realistic ceiling this codebase already
  models.
- **Rationale**: `target_feed_rate` is validated in its as-supplied
  (display-unit) form, exactly like `target_rpm` — sign and finiteness are
  invariant under the linear mm↔in conversion, so validating before
  conversion is equivalent to validating after, and mirrors `target_rpm`'s
  existing precedent of never needing metric conversion for validation
  (RPM has none at all; feed rate's conversion is deferred to immediately
  before the metric-only formula layer is called, in
  `turning/__init__.py::_validate_and_prepare`, alongside diameter/depth/
  length's own `to_metric_length()` conversions).
- **Alternatives considered**: Reusing an existing length-shaped error code
  (e.g. `INVALID_DEPTH_OF_CUT`) was rejected — `ErrorInfo.code`'s own
  documented contract is "one code may cover multiple message templates for
  the *same underlying quantity*", not an unrelated quantity; a feed rate
  per rotation is neither a depth of cut nor a diameter, so it needs its own
  code, matching how `target_rpm` itself got its own `INVALID_TARGET_RPM`
  rather than reusing `INVALID_DIAMETER`.

## 6. `_reject_if_invalid()` must also guard `feed_per_rev_mm`

- **Decision**: `turning/__init__.py::_reject_if_invalid()`'s finiteness/
  positivity guard tuple — currently `(spindle_speed_rpm, feed_rate_mm_min,
  machining_time_min, cutting_force_n, torque_nm, power_kw)` — gains
  `feed_per_rev_mm` as a seventh guarded field.
- **Rationale**: `_reject_if_invalid()`'s own docstring (added on PR #100
  after a Copilot review finding) explains exactly why every field needs
  this guard: an extreme-but-individually-valid input can make one field
  underflow to `0.0` or overflow to `inf`/`nan` while others stay finite,
  silently returning a "successful" result with a meaningless value. Adding
  a new field to `TurningMetrics` without adding it to this guard would
  reintroduce precisely that already-fixed bug class for the one field this
  feature adds.
- **Alternatives considered**: Leaving `feed_per_rev_mm` unguarded on the
  premise that it is "just an echo of an already-validated input" was
  rejected — in `STANDARD`/`POWER_CONSTRAINED`/`FIXED_RPM` modes it is
  *derived* from `material.reference_feed_per_rev_mm * tool.feed_factor`
  (a product of two registry-sourced floats, not a direct user input), so
  it is exactly as exposed to underflow/overflow as `cutting_force_n`
  already is.

## 7. TUI: a per-row nudge step, not a second global constant

- **Decision**: `split_pane.NumberRow` gains one new field, `step: float =
  NUDGE_STEP` (the existing module-level `1.0` constant becomes the
  *default*, unchanged for every existing field). `nudge_selected()`'s one
  line `new_value = current + direction * NUDGE_STEP` becomes `... *
  row.step`. Turning's own `screens/turning.py` sets `step=0.1` (metric) or
  `step=0.005` (imperial) on the new feed-per-rotation row only; every other
  row across drilling, milling, and turning keeps the default `1.0` by not
  passing `step` at all.
- **Rationale**: FR-011 requires a 0.1 mm/rev step for exactly one field,
  distinct from every other field's existing 1-display-unit step. A
  per-row field is the minimal change that achieves this without
  introducing a second, differently-scoped global constant or an
  if/else keyed on `FieldId` inside the shared, operation-agnostic
  `nudge_selected()` (which would make that function silently aware of a
  single turning-specific field, the opposite of the layering
  `split_pane.py`'s own module docstring establishes).
- **Imperial step value — 0.005 in**: A literal 0.1 mm converted to inches
  (≈0.00394 in) is not a value a machinist would ever dial in by habit and
  reads as an arbitrary, non-round number in the field. 0.005 in/rev is
  itself a standard, commonly published turning feed-rate value in
  imperial shop practice (the same order of fineness as 0.1 mm/rev, ≈0.127
  mm), so it was chosen as the imperial step instead of a proportiona
  conversion of the metric constant. Per spec.md's Assumptions, this is
  documented here as the concrete implementation choice; it is not itself
  user-facing scope.
- **Alternatives considered**: A `step` keyed by `FieldId` inside
  `nudge_selected()` itself was rejected for the layering reason above. A
  proportional imperial step (0.1 mm exactly converted, ≈0.00394 in) was
  rejected as producing a non-round, unfamiliar number with no shop-practice
  meaning, for no gain over a standard round imperial feed value.

## 8. Unit conversion for `target_feed_rate` and the new result field: reuse `to_metric_length`/`mm_to_in`

- **Decision**: `target_feed_rate` (a length-per-rotation quantity, like
  `feed_per_tooth` in milling) converts exactly like diameter/depth-of-cut/
  length-of-cut: `to_metric_length(target_feed_rate, unit_system)` at the
  orchestration layer before the metric-only formula layer runs, and
  `mm_to_in(metrics.feed_per_rev_mm)` in `_build_result()` when
  `unit_system is UnitSystem.IMPERIAL` (else used as-is), mirroring
  `cutting_force`'s own `n_to_lbf()` conditional exactly. The TUI's
  `TurningSessionState.target_feed_rate` converts on a mid-session
  unit-system switch via the existing `forms.convert_length()` helper,
  exactly as milling's `feed_per_tooth` field already does.
- **Rationale**: A feed rate per rotation is dimensionally a length (the
  "per rotation" divisor does not change under a metric/imperial
  conversion, exactly as "per tooth" does not for milling's
  `feed_per_tooth`) — no new conversion function is needed; the existing
  `to_metric_length`/`mm_to_in`/`forms.convert_length` trio already handles
  every other length-shaped quantity in this codebase identically.
- **Alternatives considered**: A dedicated `feed_per_rotation`-specific
  conversion helper was rejected as pure duplication of `to_metric_length`/
  `mm_to_in` for a quantity that converts by the same linear factor as
  every other length in the module.

## 9. `_SPINDLE_SPEED_MODE_LABEL_KEYS` must gain a `FEED_RATE_CONSTRAINED` entry, or every feed-rate-constrained result crashes on display

- **Decision**: `console/tui/forms.py::format_result()` looks up the
  spindle-speed mode suffix via `_SPINDLE_SPEED_MODE_LABEL_KEYS[result.mode]`
  — a plain dict, not an `if`/`elif` chain, currently defined only for
  `STANDARD`/`POWER_CONSTRAINED`/`FIXED_RPM`. Add a fourth entry,
  `CalculationMode.FEED_RATE_CONSTRAINED:
  "tui.result.spindle_speed.mode.feed_rate_constrained"`, with a new
  catalog value (`"derived from cutting speed"` — spindle speed is
  *derived*, exactly as standard mode's, from cutting speed and diameter,
  not from the supplied feed rate, so the label names the actual
  derivation input rather than the mode's own defining input, to avoid
  implying feed determines spindle speed — a Copilot review finding on
  this PR caught an earlier draft's `"derived from specified feed rate"`,
  which said the opposite of this same paragraph's own reasoning).
- **Rationale**: This dict is a hard lookup — an unhandled key raises
  `KeyError`, which would crash the console's result rendering (not return
  a graceful error) for every single feed-rate-constrained-mode result,
  the moment `format_result()` is reached. This is not optional polish; it
  is a correctness requirement discovered by tracing every place
  `CalculationMode` is pattern-matched exhaustively, the same class of gap
  `019-turning-calculations`' own `_reject_if_invalid()` guard (research.md
  #6) exists to catch for numeric fields.
- **Alternatives considered**: `.get(result.mode, fallback)` with a generic
  fallback label was rejected — it would silently produce a technically-
  non-crashing but wrong/uninformative label instead of a correct,
  mode-specific one, for no benefit over just adding the one missing entry
  the same way the three existing entries were each added by their own
  introducing feature.

## 10. `format_result()` also gains the new `feed_per_rotation` display line

- **Decision**: `console/tui/forms.py::format_result()` appends a new line,
  conditional on `result.feed_per_rotation is not None`, immediately after
  the existing `tui.result.feed_rate` line — mirroring exactly how the
  existing `if result.material_removal_rate is not None` /
  `if result.cutting_force is not None` conditional lines are already
  appended for operations that populate them.
- **Rationale**: `format_result()` is already the single shared,
  operation-agnostic renderer used by drilling, milling, and turning; every
  optional field it supports today follows this same "populated → append a
  line, `None` → skip it silently" pattern, so turning's new field follows
  the identical, already-established convention rather than introducing a
  new rendering mechanism.
- **Alternatives considered**: An unconditional line (always appended, showing
  a blank/placeholder for drilling and milling) was rejected — it would
  show a meaningless line for every non-turning result, breaking the
  existing convention every other optional field already follows.
