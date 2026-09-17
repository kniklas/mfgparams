# Feature Specification: Turning Combined-Constraint Modes & Machining Menu Auto-Hide

**Feature Branch**: `021-turning-combined-constraints`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "For turning add ability to constrain calcuations by combination of two input parammeters: A: fixed piece rotation & fixed feed per roation; B: fixed available power & fixed feed per rotation. Additionally in TUI: always hide mmachining winndow after operation (turnning, drilling, milling) is selected, after exiting drilling, milling, turning displlay again machining window"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Turning with a Directly Fixed Spindle Speed and Feed Together (Priority: P1)

A machinist who already knows exactly which spindle speed (RPM) and which feed per rotation they intend to run — for example, both values are already dialed into the lathe, or dictated by a fixture or process sheet — selects a calculation mode where both values are supplied directly, so the module reports machining time, cutting force, torque, and power for that exact combination instead of deriving either value from the material's or tool's reference parameters.

**Why this priority**: `020-turning-feed-per-rotation` and `019-turning-calculations` each let the machinist fix *one* of spindle speed or feed per rotation while the other is still derived from a reference lookup. When both are already known and fixed by the shop floor, forcing a derived value that doesn't match reality produces a result the machinist can't use as-is. This is the more commonly requested of the two new modes because it needs no additional power input.

**Independent Test**: Can be fully tested by selecting the new rotation-and-feed-constrained mode, supplying a target spindle speed and a target feed per rotation that differ from what standard mode would derive for the same material/tool/diameter, and verifying the returned machining time, cutting force, torque, and power are computed from the two supplied values rather than from any material/tool reference cutting speed or feed value.

**Acceptance Scenarios**:

1. **Given** a user selects the rotation-and-feed-constrained mode and supplies both a target spindle speed and a target feed per rotation, **When** they request a calculation, **Then** the module computes machining time, cutting force, torque, and power directly from the two supplied values, without deriving spindle speed from cutting speed or feed from the material/tool's reference feed value.
2. **Given** a user selects the rotation-and-feed-constrained mode but supplies only a spindle speed or only a feed per rotation (not both), **When** they request a calculation, **Then** the module reports a clear, structured error that this mode requires both values, and performs no calculation.
3. **Given** a user supplies a zero, negative, or non-numeric spindle speed or feed per rotation in this mode, **When** they request a calculation, **Then** the module reports a clear, structured error and performs no calculation.
4. **Given** a user also supplies an available power rating while using this mode, **When** the estimated required power exceeds that rating, **Then** the module reports a clear warning, exactly as standard and fixed-RPM modes already do with an optional power rating; **When** no power rating is supplied, **Then** the module still calculates and returns the estimated power requirement without a feasibility comparison.

---

### User Story 2 - Run Turning Within a Fixed Power Budget at a Fixed Feed (Priority: P2)

A machinist who must stay within a known available power limit (e.g., the lathe's rated power) but also needs to run a specific feed per rotation — for example, to meet a surface-finish requirement — selects a calculation mode where both the available power and the feed per rotation are fixed inputs, so the module solves for the highest spindle speed that keeps the operation within the power budget at that exact feed, instead of deriving feed from the material/tool's reference value the way the existing power-constrained mode does.

**Why this priority**: This extends the existing power-constrained mode (`019-turning-calculations` User Story 3) with the same feed-fixing capability added for rotation in User Story 1. It depends on feed being expressible as a direct input (`020-turning-feed-per-rotation`), and is a narrower need than User Story 1 (it requires the machinist to also know their available power), so it is P2.

**Independent Test**: Can be fully tested by selecting the power-and-feed-constrained mode, supplying an available power and a target feed per rotation distinct from the material/tool's reference feed value, and verifying the module solves for a spindle speed that keeps estimated power within the supplied budget at the supplied feed, rather than at a derived reference feed value.

**Acceptance Scenarios**:

1. **Given** a user selects the power-and-feed-constrained mode and supplies both an available power and a target feed per rotation, **When** they request a calculation, **Then** the module solves for the highest spindle speed feasible within the supplied power at the supplied feed, and computes machining time, cutting force, and power from that resulting spindle speed and the supplied feed.
2. **Given** a user selects the power-and-feed-constrained mode but supplies only one of the two required values, **When** they request a calculation, **Then** the module reports a clear, structured error that this mode requires both an available power and a feed per rotation, and performs no calculation.
3. **Given** the supplied feed per rotation is high enough that no feasible spindle speed exists within the supplied power, **When** the user requests a calculation, **Then** the module reports a clear, structured error that no feasible operating point exists, mirroring the existing power-constrained mode's behavior.
4. **Given** a user supplies a zero, negative, or non-numeric available power or feed per rotation in this mode, **When** they request a calculation, **Then** the module reports a clear, structured error and performs no calculation.

---

### User Story 3 - Machining Menu Steps Out of the Way During an Operation (Priority: P2)

A user working in the console text interface opens the Machining menu and selects an operation (turning, drilling, or milling); the menu disappears so only the selected operation's own screen is visible, and reappears, showing the same choices as before, as soon as the user exits that operation back to the top level.

**Why this priority**: This is a console usability refinement independent of the turning calculation modes in User Stories 1-2 — it applies uniformly to all three existing operations and does not block or depend on either new calculation mode, so it can be delivered and verified on its own.

**Independent Test**: Can be fully tested by opening the Machining menu, selecting each of turning, drilling, and milling in turn, verifying the Machining menu is not visible while the operation's screen is open, then exiting the operation and verifying the Machining menu is visible again.

**Acceptance Scenarios**:

1. **Given** the Machining menu is open, **When** the user selects turning, drilling, or milling, **Then** the Machining menu is hidden and only the selected operation's screen is shown.
2. **Given** an operation's screen is open (turning, drilling, or milling), **When** the user exits that operation back to the top level, **Then** the Machining menu is displayed again.
3. **Given** the user opens and exits turning, then opens and exits drilling, then opens and exits milling in the same session, **When** each exit completes, **Then** the Machining menu reappears identically every time, regardless of which operation was open.

---

### Edge Cases

- What happens when a rotation-and-feed-constrained or power-and-feed-constrained calculation's supplied values would drive machining time, cutting force, torque, or power to a non-finite or non-positive result? The module rejects the request with a clear, structured error, mirroring how the existing turning modes already guard every result.
- How do the two new modes behave when no material or turning tool has been selected yet? They still require both selections before calculating, exactly as the existing four modes already do.
- What happens if a user selects rotation-and-feed-constrained or power-and-feed-constrained mode together with inputs belonging to another mode (e.g., a target spindle speed submitted while power-and-feed-constrained is selected, in place of an available power)? The module treats the selected mode's own required inputs as authoritative and reports a clear, structured error if any of that mode's required inputs is missing, rather than silently falling back to another mode's derivation.
- Do the two new combined-constraint modes apply to drilling or milling? No — like the existing feed-rate-constrained mode, this feature is scoped to turning only.
- Does selecting an operation from the Machining menu, then immediately exiting without changing any input, still hide and reliably restore the Machining menu? Yes — the hide/show behavior does not depend on whether a calculation was run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a rotation-and-feed-constrained turning calculation mode in which the caller supplies both a target spindle speed and a target feed per rotation directly, and the module computes machining time, cutting force, torque, and power from those two supplied values without deriving either from the selected material's or tool's reference cutting speed or reference feed value.
- **FR-002**: In rotation-and-feed-constrained mode, the system MUST require both a spindle speed and a feed per rotation, and MUST reject the request with a clear, structured error if either is missing, zero, negative, or non-numeric, performing no calculation.
- **FR-003**: The system MUST provide a power-and-feed-constrained turning calculation mode in which the caller supplies both an available power and a target feed per rotation directly, and the module solves for the highest spindle speed feasible within that available power at that feed, then computes machining time, cutting force, and power from the resulting spindle speed and the supplied feed.
- **FR-004**: In power-and-feed-constrained mode, the system MUST require both an available power and a feed per rotation, and MUST reject the request with a clear, structured error if either is missing, zero, negative, or non-numeric, performing no calculation.
- **FR-005**: In power-and-feed-constrained mode, if no feasible spindle speed exists within the supplied available power at the supplied feed, the system MUST reject the request with a clear, structured error rather than returning an infeasible or degenerate result, mirroring the existing power-constrained mode.
- **FR-006**: In rotation-and-feed-constrained mode, the system MUST accept an available power as an optional input; when supplied, the system MUST report a clear warning if the estimated required power exceeds it; when omitted, the system MUST still calculate and return the estimated power requirement without a feasibility comparison.
- **FR-007**: The system MUST require a material selection and a turning tool selection before performing a calculation in either new mode, and MUST report the missing selection(s), consistent with the existing turning calculation modes.
- **FR-008**: The system MUST reject a request that selects rotation-and-feed-constrained or power-and-feed-constrained mode together with another mode's conflicting inputs (e.g., a mode-selection value that does not match the supplied inputs) as a mode conflict, consistent with how the existing feed-rate-constrained mode already rejects conflicting mode/input combinations.
- **FR-009**: The system MUST expose both new modes through the console interface and the library API, producing identical results for identical inputs, consistent with every other turning calculation mode.
- **FR-010**: The system MUST NOT apply the two new combined-constraint modes to drilling or milling; they are scoped to turning only.
- **FR-011**: In the console text interface, the system MUST hide the Machining menu immediately once the user selects turning, drilling, or milling, so that only the selected operation's own screen is visible.
- **FR-012**: In the console text interface, the system MUST redisplay the Machining menu, in the same state it was in before it was hidden, immediately once the user exits an open turning, drilling, or milling screen back to the top level.
- **FR-013**: The hide-on-select and restore-on-exit behavior in FR-011 and FR-012 MUST apply identically and symmetrically to all three operations (turning, drilling, milling).

### Key Entities

- **Turning Operation**: Extended with two additional calculation-mode values (rotation-and-feed-constrained, power-and-feed-constrained), each carrying its own pair of required direct inputs (spindle speed + feed per rotation, or available power + feed per rotation) alongside the existing diameter, depth of cut, length of cut, material, and tool inputs already defined by `019-turning-calculations`.
- **Machining Menu**: The console text interface's operation-selection surface (listing turning, drilling, milling); its visibility now toggles based on whether an operation's own screen is currently open.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A machinist who already knows their target spindle speed and feed per rotation can obtain machining time, cutting force, torque, and power for that exact combination without needing to look up or override any material/tool reference value.
- **SC-002**: A machinist who knows their available power and required feed per rotation can obtain a feasible spindle speed and the resulting machining time, cutting force, and power within the same interaction, with zero calculations silently failing or producing incorrect results.
- **SC-003**: For a given spindle speed, feed per rotation, diameter, depth of cut, and material/tool combination, rotation-and-feed-constrained mode's machining time, cutting force, torque, and power exactly match the values produced by feeding the same spindle speed and feed per rotation through the existing turning formulas — zero deviation, since no reference-value derivation is involved.
- **SC-004**: Selecting an operation from the Machining menu results in the menu being off-screen within the same interaction, and exiting that operation results in the Machining menu being visible again within the same interaction, 100% of the time across all three operations.
- **SC-005**: Invalid or incomplete input to either new calculation mode is identified and communicated within the same interaction, in both the console interface and the library API.

## Assumptions

- The two new modes are additive: they do not change the existing standard, fixed-RPM, power-constrained, or feed-rate-constrained modes' behavior, defaults, or results for turning.
- "Fixed piece rotation" in the feature request refers to a fixed spindle speed (RPM), the same spindle-speed quantity already used by the existing fixed-RPM mode — not a fixed number of workpiece revolutions for the pass.
- Feed per rotation in both new modes uses the same feed-per-rotation value and unit handling (mm/rev metric, in/rev imperial) already introduced by `020-turning-feed-per-rotation`.
- The Machining menu referred to in the feature request is the console text interface's operation-selection menu (listing turning, drilling, and milling); "the machining window" and "the Machining menu" refer to the same on-screen element.
- Restoring the Machining menu "in the same state" means the same selection/highlight position it had before being hidden, not a reset to a default position.
- This TUI visibility change is purely presentational: it does not change which operations are available, how they are opened, or any calculation behavior.
