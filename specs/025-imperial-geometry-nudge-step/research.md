# Research: Imperial Arrow-Key Nudge Step for Geometry Fields

**Feature**: `025-imperial-geometry-nudge-step` | **Date**: 2026-09-23

## #1: Imperial-unit arrow-key nudge step for the nine geometry fields

**Decision**: 0.1 in per Left/Right arrow press under the IMPERIAL unit
system, applied uniformly to all nine fields (milling's cutter diameter,
axial depth of cut, radial engagement, length of cut; drilling's drill
diameter, hole depth; turning's workpiece diameter, depth of cut, length
of cut). METRIC is unchanged — each field keeps `split_pane.NUDGE_STEP`
(1.0, i.e. 1 mm).

**Rationale**: Unlike the `020-turning-feed-per-rotation` and
`024-feed-per-tooth-nudge-step` precedents, no shop-practice-value
research question exists here: the feature request specifies 0.1
literally, for every one of the nine fields, with no metric value to
derive an imperial equivalent from (these are whole geometry dimensions —
diameters, depths, lengths — not a per-tooth/per-rotation rate where a
"round" shop value had to be independently chosen). 0.1 in is also
independently reasonable on its own terms: these fields commonly take
fractional-inch or decimal-inch values (e.g. a 0.375 in drill, a 0.25 in
depth of cut), and the existing 1-display-unit default (1 in under
imperial) is too coarse to reach most realistic values without falling
back to typing — the same "arrow-key nudge is effectively unusable"
problem 024 identified for metric feed-per-tooth, but here specifically
for imperial geometry values.

**Alternatives considered**:

- **Leaving METRIC's step unspecified/also changed**: Rejected — the
  feature request only describes the imperial case; METRIC's existing
  1 mm default is already fine-grained enough for these fields' typical
  metric values (whole or half millimeters are common), and Principle VI/
  scope discipline argues against changing behavior nothing asked to
  change (FR-004, edge case in spec.md).
- **A different step per field (e.g. finer for diameter, coarser for
  length of cut)**: Rejected — the feature request specifies one uniform
  value (0.1) for all nine fields; no basis in the request or in
  shop-practice convention favors differentiating among them, and a single
  value is simpler to implement, test, and document (Principle I).

## #2: Extending the per-row nudge-step mechanism to drilling and turning

**Decision**: Reuse `split_pane.NumberRow.step` exactly as
`020-turning-feed-per-rotation` and `024-feed-per-tooth-nudge-step` already
did. Milling's `_number_row()` (extended by 024) already accepts an
optional `step` parameter defaulting to `split_pane.NUDGE_STEP`; drilling's
and turning's `_number_row()` helpers do not yet, so this feature extends
both the same way 024 extended milling's — an optional `step` parameter,
defaulted so every existing call site (available power, target RPM,
number of teeth, feed rate) is unaffected.

**Rationale**: Both drilling and turning already route every plain numeric
row through one shared `_number_row()` helper (unlike turning's separate
`_feed_rate_row()` factory for its one custom-step field), mirroring
milling's own pre-024 shape exactly. Giving each helper the identical
optional `step` parameter milling's already has keeps all three screens'
`_number_row()` signatures consistent — no new field, dataclass, or
nudge-handling code path in `split_pane.py`'s existing nudge mechanics
itself, which already handles sub-1.0 steps correctly via its existing
`Decimal`-safe `nudge_selected()` arithmetic (proven by 020 and 024).

The step *value itself*, per the correction below, is computed by one
shared `split_pane.geometry_nudge_step(unit_system)` function — not
duplicated inline at each of the nine call sites.

**Alternatives considered**:

- **A dedicated per-field factory per geometry row (mirroring turning's
  `_feed_rate_row()`)**: Rejected — that shape exists in turning because
  `target_feed_rate` is a mode-dependent row built through
  `power_and_rpm_rows()`'s factory-callback pattern, not because it's the
  preferred shape for an unconditionally-present row. All nine geometry
  fields here are unconditionally present plain rows, exactly like the
  fields already going through each screen's shared `_number_row()`
  helper — extending that helper (as 024 did for milling) is the
  established, lower-footprint precedent for this shape of row.

**Correction (same PR, before merge — not a separate spec revision): this
alternative originally read "A shared step-computation helper function in
`split_pane.py`: Rejected as unnecessary abstraction for a two-branch,
one-line expression already duplicated (not shared) across the 020/024
precedents at their respective call sites." That reasoning held for 020/024
individually (each introduces its own distinct imperial value — 0.005,
0.001 — at one call site apiece, genuinely not shared logic), but does not
hold for this feature's own nine call sites, which all compute the
identical literal expression
(`NUDGE_STEP if state.unit_system is UnitSystem.METRIC else 0.1`) verbatim
across three files. A local `/code-review` pass (very-high intensity,
`pr-review-loop`) caught this as real triplication of this feature's own
logic — Constitution Principle I's "absence of duplicated logic" and
"magic numbers tied to physical meaning are named" — with a concrete
failure scenario: a future revision to the imperial geometry step value
requires editing three files, and missing one silently leaves that
screen's fields on the old step with no test catching the
*inconsistency* (each screen's tests only assert their own file's value in
isolation). Fixed by extracting `split_pane.geometry_nudge_step()`, used
by all three screens' `rows_for()`; see the contract delta.
