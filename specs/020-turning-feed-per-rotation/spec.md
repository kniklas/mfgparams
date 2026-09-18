# Feature Specification: Turning Feed Rate Per Rotation & Constrained Mode

**Feature Branch**: `020-turning-feed-per-rotation`

**Created**: 2026-09-12

**Status**: Draft

**Input**: User description: "turning feed rate should be specified as mm per piece rotation; there should be added a calculation mode: feed rate constrained; on TUI feed rate per rotation is adjusted per 0.1mm when using right and left arrows"

## Clarifications

### Session 2026-09-12

- Q: `CalculationResult.feed_rate` is a field shared by drilling, milling, and turning, documented uniformly as distance-per-unit-time. Should turning's new per-rotation feed value redefine that shared field only for turning, add a new turning-specific field, or redefine it for all three processes? → A: Add a new, turning-specific feed-per-rotation value alongside the existing `feed_rate`, which continues to report the distance-per-time value unchanged for turning (and drilling/milling remain untouched by this feature).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read Turning Feed Rate as an Amount Per Workpiece Rotation (Priority: P1)

A machinist or manufacturing engineer viewing any turning calculation result (standard, fixed-RPM, or power-constrained mode) sees a feed-per-rotation value included in the result — the distance the tool advances for each rotation of the workpiece (e.g., mm/rev) — alongside the existing feed rate, matching how feed rate is actually set on a lathe.

**Why this priority**: Every other turning capability builds on this value being available the way a machinist actually dials it in. Reporting feed rate only per unit time forces a mental conversion (and a spindle-speed lookup) before the number is usable at the machine, undermining `019-turning-calculations`' own goal of a directly actionable result.

**Independent Test**: Can be fully tested by running a standard-mode turning calculation with known material/tool/diameter inputs and verifying the result includes a feed-per-rotation value equal to the expected distance-per-rotation value (matching the value already used internally to derive machining time), while the existing feed rate value is unchanged.

**Acceptance Scenarios**:

1. **Given** a user runs a standard-mode turning calculation, **When** the result is returned, **Then** the result includes a feed-per-rotation value (mm/rev under metric, in/rev under imperial), clearly labeled, alongside the existing feed rate value.
2. **Given** a user runs a fixed-RPM or power-constrained turning calculation, **When** the result is returned, **Then** the result includes the same feed-per-rotation value, consistent with standard mode.
3. **Given** the same underlying inputs are calculated before and after this feature ships, **When** the results are compared, **Then** the spindle speed, machining time, cutting force, torque, power, and existing feed rate values are all unchanged — the only difference is the addition of the new feed-per-rotation value.

---

### User Story 2 - Choose a Feed-Rate-Constrained Turning Calculation Mode (Priority: P2)

A machinist who wants to run a specific feed rate per rotation — for example, to match a surface-finish requirement or a setting already dialed into the lathe — selects a new feed-rate-constrained calculation mode and supplies that feed rate directly, instead of using the material/tool's reference feed value.

**Why this priority**: This extends turning's existing calculation-mode parity (`019-turning-calculations` User Story 3: standard, fixed-RPM, power-constrained) with a fourth way of driving the calculation. It depends on feed rate already being expressed per rotation (User Story 1), and is not required for that foundational correctness fix to have value, so it is P2.

**Independent Test**: Can be fully tested by selecting feed-rate-constrained mode, supplying a target feed rate per rotation distinct from the material/tool's reference value, and verifying the returned machining time, cutting force, torque, and power are calculated from the supplied feed rate rather than the material/tool's own reference feed value, while spindle speed is still derived the same way standard mode derives it.

**Acceptance Scenarios**:

1. **Given** a user selects feed-rate-constrained mode and supplies a target feed rate per rotation, **When** they request a calculation, **Then** the module computes spindle speed the same way standard mode does (from the material's and tool's reference cutting speed and the entered diameter), and computes machining time, cutting force, torque, and power from the supplied feed rate rather than the material/tool's reference feed value.
2. **Given** a user selects feed-rate-constrained mode without supplying a feed rate, **When** they request a calculation, **Then** the module reports a clear, structured error that this mode requires a feed rate, and performs no calculation.
3. **Given** a user supplies a zero, negative, or non-numeric feed rate in feed-rate-constrained mode, **When** they request a calculation, **Then** the module reports a clear, structured error and performs no calculation.
4. **Given** a user selects feed-rate-constrained mode together with a target RPM, or together with an available power used as a hard constraint (power-constrained mode), **When** they request a calculation, **Then** the module rejects the request as a mode conflict rather than attempting to satisfy more than one mode at once.

---

### User Story 3 - Fine-Tune Feed Rate Per Rotation with Arrow Keys (Priority: P3)

A machinist working in the console text interface, with feed-rate-constrained mode selected, uses the left and right arrow keys to nudge the feed-rate-per-rotation field up or down in small, precise steps, rather than typing an exact numeric value every time.

**Why this priority**: This is a usability refinement on top of User Story 2's new editable field; the mode is already fully usable via typed input without it, so it is the lowest priority of the three.

**Independent Test**: Can be fully tested by selecting feed-rate-constrained mode, selecting the feed-rate-per-rotation field, and pressing the right (then left) arrow key, verifying the value increases (then decreases) by 0.1 mm per rotation under the metric unit system, distinct from the larger step used when nudging turning's other numeric fields (e.g., diameter, depth of cut).

**Acceptance Scenarios**:

1. **Given** the feed-rate-per-rotation field is selected under the metric unit system, **When** the user presses the right arrow key, **Then** the field's value increases by 0.1 mm per rotation; **When** the user presses the left arrow key, **Then** it decreases by 0.1 mm per rotation.
2. **Given** the feed-rate-per-rotation field is selected under the imperial unit system, **When** the user presses the right or left arrow key, **Then** the field's value changes by a correspondingly small increment (finer than turning's other numeric fields), converted consistently with the rest of the interface's unit handling.
3. **Given** the user switches the unit system while a feed-rate-per-rotation value is already entered, **When** the switch completes, **Then** the remembered value converts to the equivalent quantity in the new unit system rather than being reinterpreted as the same raw number under the new unit.

---

### Edge Cases

- What happens when a feed-rate-constrained calculation's supplied feed rate, combined with the derived spindle speed, would drive machining time, cutting force, torque, or power to a non-finite or non-positive value (e.g., an extreme feed rate)? The module rejects the request with a clear, structured error, mirroring how `019-turning-calculations` already guards every other mode's results.
- What happens when a user nudges the feed-rate-per-rotation field below zero with the left arrow key? It clears to unset rather than going negative, mirroring the existing nudge behavior for turning's other numeric fields.
- How does feed-rate-constrained mode behave when no material or turning tool has been selected yet? The module still requires both selections before calculating, exactly as the other three modes already do (`019-turning-calculations` FR-011).
- Does adding the feed-per-rotation value (User Story 1) affect the underlying spindle speed, machining time, cutting force, torque, power, or the existing feed rate formulas? No — this feature only adds a new feed-per-rotation value to the result; every existing calculated value, including the existing feed rate value, is unchanged (Acceptance Scenario 1.3).
- Does feed-rate-constrained mode apply to drilling or milling? No — this feature is scoped to turning only (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST include, in every turning calculation result (standard, fixed-RPM, power-constrained, and feed-rate-constrained), a feed-per-rotation value — the amount of material advance per workpiece rotation (mm/rev under the metric unit system, in/rev under the imperial unit system) — alongside the existing feed rate value, in both the console interface and the library API.
- **FR-002**: Per the resolved Clarification (Session 2026-09-12), the system MUST NOT change the meaning, value, or unit of the existing feed rate result field for turning, drilling, or milling; the feed-per-rotation value introduced by FR-001 is an additional, turning-specific value, not a replacement for or redefinition of the existing field.
- **FR-003**: This feature MUST NOT change turning's underlying spindle-speed, machining-time, cutting-force, torque, or power formulas established by `019-turning-calculations` — only that a feed-per-rotation value is added to the result (FR-001) and, for the new mode, which value is supplied as an input versus derived as an output (FR-004, FR-005).
- **FR-004**: The system MUST allow a turning calculation request to select a new feed-rate-constrained calculation mode, supplying a target feed rate per workpiece rotation directly instead of deriving it from the selected material's and turning tool's reference feed value.
- **FR-005**: In feed-rate-constrained mode, the system MUST derive spindle speed exactly as standard mode does (from the selected material's and turning tool's reference cutting speed and the entered diameter), and MUST calculate machining time, cutting force, torque, and power from that derived spindle speed combined with the user-supplied feed-per-rotation value. The result's feed-per-rotation value (FR-001) MUST reflect the supplied value directly, and its existing feed rate value MUST reflect the equivalent per-time rate at the derived spindle speed.
- **FR-006**: The system MUST validate a supplied feed-rate-constrained-mode feed rate as a positive, finite number, and MUST reject zero, negative, non-numeric, `NaN`, or infinite values with a clear, structured error, performing no calculation — mirroring the validation already applied to fixed-RPM's target RPM.
- **FR-007**: Feed-rate-constrained mode MUST be mutually exclusive with fixed-RPM mode and with power-constrained mode on the same turning calculation request; supplying more than one of a target feed rate, a target RPM, or an available power used as a hard constraint MUST be rejected with the same mode-conflict error already used for turning's other modes. Supplying an available power as the existing optional/advisory input alongside feed-rate-constrained mode remains allowed.
- **FR-008**: When feed-rate-constrained mode is used together with a supplied advisory available power, the system MUST apply the existing feasibility-warning behavior — a warning is included if the power required at the resulting spindle speed and supplied feed rate exceeds the available power — without altering the user-supplied feed rate.
- **FR-009**: The system MUST require a material selection and a turning tool selection before performing a feed-rate-constrained calculation, and MUST report the missing selection(s), exactly as the other three turning modes already require (`019-turning-calculations` FR-011).
- **FR-010**: The console interface MUST present feed-rate-constrained mode as a selectable option alongside turning's existing standard, fixed-RPM, and power-constrained options, and MUST show a required feed-rate-per-rotation input field only when this mode is selected, mirroring how the target-RPM field is shown only in fixed-RPM mode.
- **FR-011**: The console text interface MUST allow the user to increase or decrease the feed-rate-per-rotation field's value using the left and right arrow keys, in increments of 0.1 mm per rotation under the metric unit system (and a correspondingly small increment under the imperial unit system), distinct from the larger increment step used when nudging turning's other numeric fields (diameter, depth of cut, length of cut, available power, target RPM).
- **FR-012**: The feed-rate-per-rotation field's remembered value MUST convert consistently between metric and imperial units when the user switches unit system mid-session, mirroring how diameter, depth of cut, length of cut, and available power already convert.
- **FR-013**: All new user-facing text introduced by this feature (the feed-rate-constrained mode option, the feed-rate-per-rotation field label, and any new error messages) MUST be sourced from the existing shared message catalog, reusing existing entries where the wording is mode-generic rather than duplicating them.
- **FR-014**: This feature is scoped to turning only; extending feed-rate-constrained mode, or the per-rotation feed-rate reporting change, to drilling or milling is out of scope.

### Key Entities

- **Feed-Rate Constraint**: A caller-supplied target feed rate per workpiece rotation, used as a direct input (rather than a derived output) to a turning calculation, when feed-rate-constrained mode is selected — the feed-rate counterpart to `019-turning-calculations`' existing Spindle Speed Constraint (fixed-RPM) and Power Constraint (power-constrained).
- **Feed-Per-Rotation Value**: A new, turning-specific result value — the amount of material advance per workpiece rotation — included in every turning calculation result alongside the existing (unchanged) per-time feed rate value. In feed-rate-constrained mode it echoes the supplied Feed-Rate Constraint directly; in the other three modes it is derived from the existing feed rate and spindle speed.
- **Calculation Mode**: The existing shared value (standard, fixed-RPM, power-constrained) gains a fourth turning-specific option, feed-rate-constrained. Exactly one mode applies per request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users viewing any turning calculation result can read the feed rate as an amount of material advance per workpiece rotation directly from the result, with zero need to separately look up or mentally derive that value from the existing per-time feed rate.
- **SC-002**: Given a desired feed rate per rotation, users obtain a complete turning calculation (spindle speed, machining time, cutting force, torque, power) reflecting that exact feed rate in a single request, completing within 0.5-1.0s, the same numeric performance target as a standard turning calculation.
- **SC-003**: 100% of feed-rate-constrained results use the exact user-supplied feed-per-rotation value in their machining-time, cutting-force, torque, and power calculations, with zero silent substitution of the material/tool's reference feed value.
- **SC-004**: In the console interface, users can adjust the feed-rate-per-rotation value to within 0.1 mm/rev of a desired target using only the left/right arrow keys, without typing a numeric value.
- **SC-005**: Existing standard, fixed-RPM, and power-constrained turning calculations continue to produce the same underlying spindle speed, machining time, cutting force, torque, power, and existing feed rate values as before this feature ships (no regression to `019-turning-calculations`'s behavior); the only difference is the addition of the new feed-per-rotation value.

## Assumptions

- Per the resolved Clarification (Session 2026-09-12), the existing feed rate result field's meaning and unit stay unchanged for turning, and drilling's/milling's own calculation behavior is unaffected by this feature; the per-rotation value is exposed as a new, additional, turning-specific field rather than a redefinition. Drilling and milling do gain one small, explicit guard (rejecting the new `FEED_RATE_CONSTRAINED` mode with a structured `UNSUPPORTED_MODE` error rather than silently mislabeling a standard-mode result) — a Copilot review finding during implementation established that `calculate()`/`calculate_end_milling()`/`calculate_face_milling()` accept the shared `CalculationMode` enum directly and are reachable with this value regardless of the console's own restricted mode list, so this guard was necessary rather than optional polish.
- Feed-rate-constrained mode derives spindle speed exactly as standard mode does; it does not also let the user fix spindle speed at the same time. Combining a fixed feed rate with a fixed RPM, or with a hard power constraint, in the same request is treated as a mode conflict (FR-007), consistent with the "exactly one mode per request" rule already governing turning's other modes.
- Feed-rate-constrained mode, and the per-rotation feed-rate reporting change, are scoped to turning only in this feature (FR-014); extending either to drilling or milling, if desired, is a separate future feature — mirroring the historical split between `002-constrained-calculation-modes` (drilling-only) and `010-milling-calculation-modes` (milling, added later).
- The imperial-unit equivalent of the 0.1 mm per-rotation arrow-key step is a small, comparably fine increment (rather than a full 0.1 in, which would be a coarse ~2.5 mm step in comparison); the precise imperial value is an implementation detail for the planning phase, not user-facing scope.
- This feature reuses turning's existing message-catalog entries, mode-conflict error code, and unit-conversion mechanism wherever the wording or behavior is mode-generic, rather than introducing turning-specific duplicates.
- This feature does not change how the material/tool reference feed value itself is looked up or stored; it only changes what happens with the resulting feed rate (how it's expressed, and — in the new mode — that it can be supplied directly instead).
