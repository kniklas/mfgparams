# Research: Milling Feed-Per-Tooth Nudge Step

**Feature**: `024-feed-per-tooth-nudge-step` | **Date**: 2026-09-23

## #1: Imperial-unit arrow-key nudge step for feed per tooth

**Decision**: 0.001 in/tooth (one-thousandth of an inch per Left/Right
arrow press) under the IMPERIAL unit system, alongside the requested
0.1 mm/tooth under METRIC.

**Rationale**: Feed-per-tooth (chip load) values are conventionally
published and dialed in to the nearest thousandth of an inch in
machining shop-practice references (feeds-and-speeds charts, tooling
manufacturer catalogs), and typical chip-load values for common milling
cutters span roughly 0.001–0.010 in/tooth — an order of magnitude
smaller than turning's feed-per-revolution values (typically
0.005–0.030 in/rev), which is why `020-turning-feed-per-rotation`'s own
research (its research.md #7) settled on the coarser 0.005 in/rev step
for that field. 0.001 in/tooth is a standard, independently-recognizable
shop increment — not a literal conversion of 0.1 mm (which would be
≈0.0039 in, an arbitrary-looking number with no shop-practice meaning of
its own) — mirroring the spirit of `020-turning-feed-per-rotation`'s own
choice: round in the unit system actually used at the machine, not a
carried-over decimal from the other system.

**Alternatives considered**:

- **A literal conversion of 0.1 mm → ≈0.004 in**: Rejected per the
  feature's own explicit requirement (spec.md FR-002) and the precedent
  `020-turning-feed-per-rotation` set — a coarse literal conversion
  produces a number with no independent shop-practice meaning and would
  not read as a "round" value to a machinist working in inches.
- **Reusing turning's exact 0.005 in/rev step**: Rejected — that value
  was calibrated for feed-per-revolution, a quantity that is typically
  several times larger than feed-per-tooth for common cutters. Reusing it
  verbatim would make many realistic chip-load values (especially for
  smaller-diameter finishing cutters, often well under 0.005 in/tooth)
  unreachable by arrow-key alone, reproducing the same "step too coarse
  to be usable" problem this feature exists to fix for the metric case
  today.
- **A finer 0.0005 in/tooth step**: Rejected — finer than any published
  chip-load table's own granularity, and would require roughly twice as
  many keypresses as 0.001 in/tooth to reach a typical adjustment with no
  corresponding gain in real-world precision (chip-load recommendations
  themselves are not commonly specified to that resolution).

## #2: Reuse of the existing per-row nudge-step mechanism

**Decision**: Reuse `split_pane.NumberRow.step` and its existing
`nudge_selected()` handling (including the `Decimal`-safe arithmetic
already added for sub-1.0 steps) exactly as `020-turning-feed-per-rotation`
shipped it. No new field, parameter, or code path.

**Rationale**: This is the same problem `020-turning-feed-per-rotation`
already solved generically — a `NumberRow` MAY override the shared
`NUDGE_STEP` default with a smaller, unit-system-dependent value, computed
in the screen's own row factory and passed through at construction time.
`screens/turning.py::_feed_rate_row()` is the exact pattern to mirror for
`screens/milling.py`'s feed-per-tooth row factory: a two-branch
`step = 0.1 if state.unit_system is UnitSystem.METRIC else 0.001`
expression, passed as `step=step` to the existing `NumberRow` call.

**Alternatives considered**:

- **Adding a new, feed-per-tooth-specific nudge mechanism**: Rejected —
  would duplicate `020-turning-feed-per-rotation`'s already-generic
  solution to the identical problem (Constitution Principle VI,
  Extensibility by Design).
