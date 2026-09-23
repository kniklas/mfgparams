# Feature Specification: Milling Feed-Per-Tooth Nudge Step

**Feature Branch**: `024-feed-per-tooth-nudge-step`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "create PR and new spec to use 0.1mm/tooth when using left/right arrow when adjusting feed per tooth value"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fine-Tune Feed Per Tooth with Arrow Keys (Priority: P1)

A machinist working in the console text interface, on a milling operation
screen with a milling tool selected, uses the left and right arrow keys to
nudge the feed-per-tooth field up or down in small, precise steps, rather
than typing an exact numeric value every time.

**Why this priority**: Feed per tooth (chip load) is already an editable
field on the milling screen, but its arrow-key step currently uses the
shared 1 mm/tooth default — far coarser than the field's real-world
values, which are typically well under 1 mm/tooth. This makes the
existing arrow-key interaction effectively unusable for this field today,
so it is the only story in this feature.

**Independent Test**: Can be fully tested by selecting a milling
operation, selecting the feed-per-tooth field, and pressing the right
(then left) arrow key, verifying the value increases (then decreases) by
0.1 mm per tooth under the metric unit system, distinct from the larger
step used when nudging milling's other numeric fields (e.g., diameter,
depth of cut).

**Acceptance Scenarios**:

1. **Given** the feed-per-tooth field is selected under the metric unit
   system, **When** the user presses the right arrow key, **Then** the
   field's value increases by 0.1 mm per tooth; **When** the user presses
   the left arrow key, **Then** it decreases by 0.1 mm per tooth.
2. **Given** the feed-per-tooth field is selected under the imperial unit
   system, **When** the user presses the right or left arrow key,
   **Then** the field's value changes by a correspondingly small
   increment (finer than milling's other numeric fields), converted
   consistently with the rest of the interface's unit handling.
3. **Given** the user switches the unit system while a feed-per-tooth
   value is already entered, **When** the switch completes, **Then** the
   remembered value converts to the equivalent quantity in the new unit
   system rather than being reinterpreted as the same raw number under
   the new unit — unchanged from today's behavior.
4. **Given** the feed-per-tooth field is selected on either a face-milling
   or an end-milling operation, **When** the user nudges it, **Then** the
   0.1 mm/tooth (or imperial-equivalent) step applies identically on
   both — the field is shared, not sub-operation-specific.

---

### Edge Cases

- What happens when a user nudges the feed-per-tooth field below zero
  with the left arrow key? It clears to unset rather than going negative,
  mirroring the existing nudge behavior for every other numeric field on
  the milling screen.
- Does this feature change the arrow-key step for any other milling field
  (diameter, depth of cut, width of cut, available power, target RPM)?
  No — the smaller step is scoped to feed-per-tooth only; every other
  field keeps today's default step.
- Does this feature change feed-per-tooth's value, its role in the
  milling calculation, or how it converts between unit systems? No —
  only the arrow-key increment changes; the field's value, validation,
  and use in the milling calculation are unaffected.
- Does this feature apply to drilling or turning? No — those screens'
  own fields and nudge steps (including turning's existing
  feed-rate-per-rotation step from `020-turning-feed-per-rotation`) are
  unaffected; this feature is scoped to milling's feed-per-tooth field
  only.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The console text interface MUST allow the user to increase
  or decrease the feed-per-tooth field's value using the left and right
  arrow keys, in increments of 0.1 mm per tooth under the metric unit
  system, distinct from the larger default increment step used when
  nudging milling's other numeric fields (diameter, depth of cut, width
  of cut, available power, target RPM).
- **FR-002**: Under the imperial unit system, the feed-per-tooth field's
  arrow-key increment MUST be a correspondingly small, standard
  shop-practice chip-load value — not a coarse literal unit conversion of
  0.1 mm — mirroring how `020-turning-feed-per-rotation` derived its own
  imperial feed-rate-per-rotation increment (0.005 in/rev) rather than
  literally converting its 0.1 mm/rev metric step.
- **FR-003**: This feature MUST NOT change the arrow-key increment used
  by any other numeric field on the milling screen; the smaller step
  applies to feed-per-tooth only.
- **FR-004**: The feed-per-tooth field's remembered value MUST continue
  to convert consistently between metric and imperial units when the
  user switches unit system mid-session, exactly as it already does
  today — this feature changes only the nudge increment, not the field's
  existing value or unit-conversion behavior.
- **FR-005**: A nudge that would take the feed-per-tooth value at or
  below zero MUST clear it to unset, mirroring the existing behavior of
  every other nudge-adjustable numeric field on the milling screen.
- **FR-006**: This feature MUST apply uniformly to every milling
  sub-operation that exposes the feed-per-tooth field (face milling, end
  milling); it MUST NOT be limited to one sub-operation.
- **FR-007**: This feature is scoped to milling only; drilling's fields
  and turning's existing feed-rate-per-rotation nudge step are unaffected.
- **FR-008**: This feature MUST NOT change feed-per-tooth's value,
  validation, or its use in the underlying milling calculations — only
  how far the value moves per arrow-key press.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Under the metric unit system, a user can move the
  feed-per-tooth field to any value that is a multiple of 0.1 mm/tooth
  using only arrow-key presses, without typing a value.
- **SC-002**: Under the imperial unit system, a user can fine-tune the
  feed-per-tooth field in increments matching standard chip-load shop
  practice, without typing a value.
- **SC-003**: No other numeric field on the milling screen changes its
  arrow-key adjustment granularity as a result of this feature.
- **SC-004**: A user switching between metric and imperial mid-session
  sees the feed-per-tooth value convert exactly as it already does
  today, with no change in that behavior attributable to this feature.

## Assumptions

- The existing custom-step arrow-key mechanism (already used to give
  turning's feed-rate-per-rotation field its own finer increment,
  `020-turning-feed-per-rotation`) is reused as-is; no new interaction
  capability is needed for this feature.
- 0.1 mm/tooth is the correct metric-unit-system step, per the explicit
  feature request, and matches common face/end-milling chip-load
  adjustment granularity.
- The imperial-unit equivalent is a standard, named shop-practice chip-load
  value, to be researched and documented during planning (mirroring
  `020-turning-feed-per-rotation` research.md's own derivation of its
  imperial feed-rate step) rather than specified here as a literal
  0.1 mm conversion.
- Feed per tooth is currently a single field shared across milling's
  face-milling and end-milling sub-operations, confirmed in the current
  console interface; this feature does not need to distinguish between
  them.
