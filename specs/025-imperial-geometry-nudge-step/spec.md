# Feature Specification: Imperial Arrow-Key Nudge Step for Geometry Fields

**Feature Branch**: `025-imperial-geometry-nudge-step`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "imperial: when using left-right arrow use 0.1 in increase/decrease for: milling: cutter diameter, axial depth, radial depth, length of cut; drilling: drill diameter, hole depth; turning: workpiece diameter, depth of cut, length of cut. Additionally: when switching from imperial to metric, or metric to imperial use these increments even if earlier values were entered."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fine-Tune Geometry Fields with Arrow Keys Under Imperial (Priority: P1)

A machinist working in the console text interface under the imperial unit
system uses the left and right arrow keys to nudge a geometry field —
cutter diameter, axial depth of cut, radial depth, or length of cut on the
milling screen; drill diameter or hole depth on the drilling screen;
workpiece diameter, depth of cut, or length of cut on the turning screen —
rather than typing an exact numeric value every time.

**Why this priority**: These nine fields currently all share the
interface's default arrow-key step of 1 (whole unit) regardless of unit
system. Under imperial, dimensions on these fields are typically well
under an inch or in small fractional increments, so a 1-inch nudge is too
coarse to be practically usable — this is the core problem the feature
exists to fix, and it is the only story in this feature.

**Independent Test**: Can be fully tested by switching any of the three
operation screens (milling, drilling, turning) to the imperial unit
system, selecting one of the nine listed fields, and pressing the right
(then left) arrow key, verifying the value changes by 0.1 (inch) per
press instead of the previous 1 (inch) step.

**Acceptance Scenarios**:

1. **Given** the milling screen is set to the imperial unit system and the
   cutter diameter, axial depth of cut, radial depth, or length of cut
   field is selected, **When** the user presses the right or left arrow
   key, **Then** the field's value changes by 0.1 in per press.
2. **Given** the drilling screen is set to the imperial unit system and
   the drill diameter or hole depth field is selected, **When** the user
   presses the right or left arrow key, **Then** the field's value
   changes by 0.1 in per press.
3. **Given** the turning screen is set to the imperial unit system and the
   workpiece diameter, depth of cut, or length of cut field is selected,
   **When** the user presses the right or left arrow key, **Then** the
   field's value changes by 0.1 in per press.
4. **Given** any of the nine fields is selected under the metric unit
   system, **When** the user presses the right or left arrow key,
   **Then** the field's value changes by today's existing metric step
   (unchanged by this feature).

---

### User Story 2 - Correct Step Applies Immediately After Switching Unit System (Priority: P2)

A machinist who has already entered a value for one of the nine fields
switches the operation screen's unit system toggle (imperial to metric,
or metric to imperial). Immediately after the switch, without doing
anything else, the machinist nudges that same field with the arrow keys
and gets the step size that matches the *new* unit system, not the one
that was active when the value was originally entered.

**Why this priority**: This is a correctness guarantee on top of Story
1 — without it, a user could enter a value under metric, switch to
imperial, and still nudge in metric-sized increments (or vice versa),
which would be confusing and error-prone. It depends on Story 1 existing
first (there must be a distinct imperial step to apply correctly).

**Independent Test**: Can be fully tested by entering a value for one of
the nine fields under one unit system, switching the screen to the other
unit system, and immediately pressing an arrow key, verifying the step
used matches the newly active unit system.

**Acceptance Scenarios**:

1. **Given** a value was entered for one of the nine fields under metric,
   **When** the user switches the screen to imperial, **Then** the very
   next arrow-key press on that field nudges it by the imperial step
   (0.1 in), not the metric step.
2. **Given** a value was entered for one of the nine fields under
   imperial, **When** the user switches the screen to metric, **Then**
   the very next arrow-key press on that field nudges it by the metric
   step (unchanged from today), not the imperial step.
3. **Given** the user switches unit system repeatedly (metric → imperial
   → metric → imperial) without leaving the screen, **When** the user
   nudges a field after each switch, **Then** the step used always
   matches the unit system active at the moment of the nudge.

---

### Edge Cases

- Does this feature change the field's *value* when the unit system is
  switched? No — the existing value-conversion behavior (the number
  itself converting to the equivalent physical quantity in the new unit)
  is unchanged; only the arrow-key increment size changes.
- What happens when a user nudges one of these fields below zero with the
  left arrow key? It clears to unset, mirroring the existing nudge
  behavior for every other numeric field on these screens — unaffected by
  this feature.
- Does this feature change the arrow-key step for any other field on
  these three screens, such as milling's feed-per-tooth
  (`024-feed-per-tooth-nudge-step`) or turning's feed-rate-per-rotation
  (`020-turning-feed-per-rotation`)? No — those fields already have their
  own dedicated step overrides from prior features and are left
  unchanged; this feature is additionally scoped to the nine geometry
  fields listed above only.
- Does this feature change the metric step for any of the nine fields?
  No — only the imperial step changes; metric keeps today's default step.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On the milling screen, under the imperial unit system, the
  cutter diameter, axial depth of cut, radial depth, and length of cut
  fields MUST each use an arrow-key increment of 0.1 in per press.
- **FR-002**: On the drilling screen, under the imperial unit system, the
  drill diameter and hole depth fields MUST each use an arrow-key
  increment of 0.1 in per press.
- **FR-003**: On the turning screen, under the imperial unit system, the
  workpiece diameter, depth of cut, and length of cut fields MUST each
  use an arrow-key increment of 0.1 in per press.
- **FR-004**: Under the metric unit system, the arrow-key increment for
  all nine fields listed in FR-001 through FR-003 MUST remain unchanged
  from today's existing default step.
- **FR-005**: The arrow-key increment applied to a field MUST always
  match the unit system currently active on the screen at the moment of
  the nudge, including immediately after the user switches the unit
  system — regardless of which unit system was active when the field's
  current value was entered.
- **FR-006**: This feature MUST NOT change the value-conversion behavior
  that already applies when the user switches unit system (the
  remembered value continues to convert to the equivalent physical
  quantity in the new unit, unchanged from today).
- **FR-007**: A nudge that would take any of the nine fields at or below
  zero MUST clear it to unset, mirroring the existing behavior of every
  other nudge-adjustable numeric field on these screens.
- **FR-008**: This feature MUST NOT change the arrow-key increment for
  any field outside the nine listed — in particular, milling's
  feed-per-tooth field and turning's feed-rate-per-rotation field keep
  their own existing step overrides from prior features, and every other
  field on these three screens keeps today's default step.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Under the imperial unit system, a user can move each of the
  nine listed fields to any value that is a multiple of 0.1 in using only
  arrow-key presses, without typing a value.
- **SC-002**: Under the metric unit system, none of the nine fields'
  arrow-key adjustment granularity changes as a result of this feature.
- **SC-003**: No field outside the nine listed changes its arrow-key
  adjustment granularity as a result of this feature.
- **SC-004**: A user switching a screen's unit system mid-session sees
  the arrow-key step for each of the nine fields match the newly active
  unit system on the very next nudge, with no leftover step from the
  previous unit system.

## Assumptions

- The existing custom-step arrow-key mechanism (already used to give
  milling's feed-per-tooth field and turning's feed-rate-per-rotation
  field their own finer increments) is reused as-is; no new interaction
  capability is needed for this feature.
- 0.1 in is the correct imperial-unit-system step for all nine fields,
  per the explicit feature request — unlike the feed-per-tooth and
  feed-rate-per-rotation precedents, no separate shop-practice research
  is needed here because the request already specifies the exact
  imperial value.
- The metric step for these nine fields is not being changed by this
  feature; it keeps whatever default step it already uses today.
- Because each screen already recomputes a field's step fresh from the
  currently active unit system on every render (rather than caching or
  storing it), applying the imperial override consistently within that
  existing pattern is expected to satisfy the "correct step immediately
  after switching" requirement (User Story 2) without additional
  transition-specific logic.
