# Feature Specification: Turning Calculations Module

**Feature Branch**: `019-turning-calculations`

**Created**: 2026-09-11

**Status**: Draft

**Input**: User description: "Add a new \"turning\" machining process (lathe turning), as a sibling to the existing milling and drilling processes under src/mfgparams/processes/machining/. Turning is a machining operation where a workpiece rotates on a lathe spindle while a stationary single-point cutting tool removes material to produce cylindrical or conical features. Scope: core turning calculations (spindle speed, feed rate, machining time, cutting power, cutting force/torque) for standard cylindrical (straight/OD) turning; reuse the existing WorkpieceMaterial registry and configurable-tool pattern; support the same standard/fixed-RPM/power-constrained calculation modes already established for drilling/milling; expose turning through the library API, the console REPL/TUI, and consistent locale/unit handling. Out of scope: facing, grooving, parting, threading, taper turning, and boring — only straight/OD turning is in scope for this first slice."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Core Turning Parameters Interactively (Priority: P1)

A machinist or manufacturing engineer, working directly in the console text interface, selects the turning process, enters the workpiece diameter, depth of cut, length of cut, workpiece material, and turning tool, so the module calculates the recommended spindle speed (RPM), feed rate, estimated machining time, and the cutting force and power required for a straight (outside-diameter) turning pass. If the lathe's or tool's available power rating is known, it can be supplied so the module can flag when the operation exceeds it; if not known, the module still reports the power the operation requires.

**Why this priority**: This is the fundamental capability of the feature. Without it, no other turning capability (calculation modes, TUI menu entry, library exposure) has value. It mirrors the milling and drilling modules' P1 story and answers the same core question for a new process: "What settings do I use to turn this diameter safely and efficiently, and what power does it need?"

**Independent Test**: Can be fully tested by opening the console interface, selecting the turning process, choosing a material and turning tool, entering a workpiece diameter, depth of cut, and length of cut, and verifying the output returns spindle speed, feed rate, machining time, cutting force, and power that match known reference values for that material/tool/diameter/depth-of-cut combination.

**Acceptance Scenarios**:

1. **Given** a user has selected a workpiece material and turning tool and entered a valid workpiece diameter, depth of cut, and length of cut, **When** they request a calculation, **Then** the interface displays the recommended spindle speed (RPM), feed rate, estimated machining time, and the estimated cutting force and power required.
2. **Given** a user enters a workpiece diameter, depth of cut, or length of cut of zero or a negative value, **When** they request a calculation, **Then** the interface rejects the input with a clear validation message and performs no calculation.
3. **Given** a user has not yet selected a material or a turning tool, **When** they request a calculation, **Then** the interface prompts them to make the missing selection(s) before proceeding.
4. **Given** a user selects a different turning tool for the same material and diameter, **When** the calculation refreshes, **Then** the recommended spindle speed, feed rate, cutting force, and power reflect the selected tool's own cutting parameters.
5. **Given** a user knows and supplies their lathe's or tool's available power rating, **When** the estimated power required exceeds that rating, **Then** the interface displays a clear warning that the operation may not be feasible.
6. **Given** a user does not know their lathe's or tool's power rating, **When** they request a calculation, **Then** the interface still calculates and displays the estimated power the operation requires, without attempting a feasibility comparison.

---

### User Story 2 - Embed Turning Calculations in Another Application (Priority: P1)

A software developer building their own interface wants to reuse the turning calculation logic as a callable library, passing in workpiece diameter, length of cut, material, turning tool, calculation mode, and (optionally) a known power rating or target spindle speed, and receiving the same structured results the console interface would show, without invoking the console interface itself.

**Why this priority**: Every existing process in this codebase (drilling, milling) exposes its calculations as a standalone library first, with the console interface as a consumer of that library. Turning must follow the same layering from day one so it composes with the rest of the application identically to its siblings.

**Independent Test**: Can be fully tested by calling the turning module's calculation functions directly with a given diameter, length of cut, material, tool, and mode, and verifying the returned structured result matches the same values produced by the console interface for identical inputs.

**Acceptance Scenarios**:

1. **Given** a calling program supplies valid workpiece diameter, depth of cut, length of cut, material, and turning tool values directly to the library, **When** it requests a calculation, **Then** the library returns a structured result containing spindle speed, feed rate, machining time, cutting force, and power, without requiring any interactive prompts.
2. **Given** a calling program supplies an invalid input (e.g., zero or negative diameter), **When** it requests a calculation, **Then** the library reports a clear, structured error instead of raising an unhandled failure or returning an incorrect result.
3. **Given** the same inputs are provided once through the console interface and once through direct library calls, **When** both calculations run, **Then** they produce identical results.
4. **Given** a calling program supplies a `locale` parameter, **When** an error or feasibility warning occurs, **Then** the library's structured result contains the message text localized per that parameter, falling back to English for any missing translation.

---

### User Story 3 - Choose a Turning Calculation Mode (Priority: P2)

A machinist who already knows a specific spindle speed they must run (e.g., due to lathe gearing limits) or who wants the module to solve for the fastest feasible cut within their lathe's rated power, selects a calculation mode other than the standard cutting-speed-driven mode: fixed-RPM (they supply the spindle speed directly) or power-constrained (the module solves for the feasible operating point within the lathe's available power).

**Why this priority**: This extends turning to reach parity with the calculation modes already available for drilling and milling. It is not required for a minimally useful turning feature (User Story 1 already delivers a working standard-mode calculation), so it is P2 rather than P1.

**Independent Test**: Can be fully tested by selecting the fixed-RPM mode and supplying a target spindle speed, verifying the returned feed rate/force/power reflect that exact RPM rather than one derived from cutting speed; and by selecting the power-constrained mode with a lathe power rating below what standard mode would require, verifying the module returns a reduced, feasible spindle speed instead of a feasibility warning.

**Acceptance Scenarios**:

1. **Given** a user selects fixed-RPM mode and supplies a target spindle speed, **When** they request a calculation, **Then** the module computes feed rate, machining time, cutting force, and power at that exact spindle speed rather than deriving RPM from cutting speed.
2. **Given** a user selects power-constrained mode and supplies the lathe's available power, **When** the cutting speed's nominal spindle speed would exceed that power, **Then** the module reduces the spindle speed to the highest value feasible within the available power and reports that adjusted operating point, rather than merely emitting a warning.
3. **Given** a user selects power-constrained mode without supplying a power rating, **When** they request a calculation, **Then** the module reports a clear, structured error that this mode requires a power rating, and performs no calculation.
4. **Given** a user does not explicitly select a mode, **When** they request a calculation, **Then** the module defaults to the standard (cutting-speed-driven) mode.

---

### Edge Cases

- What happens when the entered workpiece diameter, depth of cut, length of cut, or other numeric input is non-numeric, missing, or extremely large (e.g., outside realistic lathe capacity)?
- What happens when the entered depth of cut is greater than or equal to the workpiece radius (physically impossible — the cut cannot remove more radius than the workpiece has)? The module rejects the request with a clear, structured error and performs no calculation.
- How does the module handle a workpiece material that is not in the supported material list?
- How does the module handle a turning tool that is not in the supported tool list, or a tool/material combination with no defined reference parameters? The module rejects the request with a clear, structured error and performs no calculation, mirroring drilling's unsupported-combination behavior.
- How does the module behave when the lathe's or tool's power rating is left unspecified in standard mode? It still returns the estimated power requirement without attempting a feasibility comparison, mirroring drilling/milling.
- What happens when power-constrained mode's solved spindle speed would fall below any realistic minimum (i.e., no feasible spindle speed exists within the supplied power)? The module reports a clear, structured error that no feasible operating point exists, rather than returning a near-zero or negative spindle speed.
- Facing, grooving, parting, threading, taper turning, and boring are explicitly out of scope for this feature; the module MUST NOT silently reinterpret a request for one of these as a straight/OD turning calculation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose turning calculation logic as a callable library, independent of any console interface, following the same layering already used by the drilling and milling processes.
- **FR-002**: The system MUST expose turning through the console interface (REPL/TUI) as a process selectable alongside the existing drilling and milling processes, built on top of the same library used by FR-001.
- **FR-003**: The system MUST allow workpiece diameter, depth of cut, length of cut, workpiece material, turning tool, and calculation mode to be supplied as inputs for a turning operation, whether via the console interface or direct library calls.
- **FR-004**: The system MUST reuse the existing `WorkpieceMaterial` registry for material selection; turning MUST NOT introduce a separate or duplicate material list.
- **FR-005**: The system MUST provide a predefined list of turning tools (e.g., differing by material composition such as high-speed steel, cobalt, or carbide), each with its own reference cutting-speed and feed adjustment factors, following the same bundled-`tools.toml` configurable-tool pattern used by drilling and milling.
- **FR-006**: In standard mode, the system MUST calculate the recommended spindle speed (RPM) from the selected material's reference cutting speed (adjusted by the selected turning tool's cutting-speed factor) and the entered workpiece diameter.
- **FR-007**: The system MUST calculate the recommended feed rate from the selected material's reference feed-per-revolution value (adjusted by the selected turning tool's feed factor) and the calculation mode's spindle speed.
- **FR-008**: The system MUST calculate the estimated machining time, in minutes (fractional, regardless of the selected unit system), based on length of cut, feed rate, and spindle speed, for a single straight/OD turning pass.
- **FR-009**: The system MUST calculate and return the estimated cutting force and estimated power required for every turning operation, based on the selected material's specific cutting force reference value and the entered depth of cut, as a standard part of the core calculation result (not a separate optional step).
- **FR-010**: The system MUST validate all numeric inputs (workpiece diameter, depth of cut, length of cut) and reject zero, negative, non-numeric, or out-of-range values, reporting a clear, actionable, catalog-sourced error in both the console interface and the library API. Default maximum bounds are workpiece diameter ≤500 mm (≈20 in), depth of cut ≤10 mm (≈0.4 in, a typical single-pass roughing limit), and length of cut ≤1000 mm (≈40 in), matching typical bench/toolroom lathe capacity; these defaults MUST be overridable via the existing external configuration mechanism without requiring code changes. Additionally, the system MUST reject a depth of cut that is greater than or equal to the workpiece radius (half the entered diameter) as physically impossible, independent of the configured maximum bound.
- **FR-011**: The system MUST require a material selection and a turning tool selection before performing any calculation and MUST report the missing selection(s) via the console interface or a structured library error. If the selected material/turning-tool combination has no defined reference parameters, the system MUST reject the request with a clear, structured error and MUST NOT fall back to generic/default values.
- **FR-012**: The system MUST support the same three calculation modes already established for drilling/milling: standard (derive spindle speed from cutting speed), fixed-RPM (the caller supplies the target spindle speed directly), and power-constrained (the system solves for the feasible spindle speed within a supplied available-power limit). Standard mode MUST be the default when no mode is specified.
- **FR-013**: In power-constrained mode, the system MUST require an available-power input and MUST reject the request with a clear, structured error if it is omitted. If no feasible spindle speed exists within the supplied power, the system MUST reject the request with a clear, structured error rather than returning an infeasible or degenerate result.
- **FR-014**: In standard and fixed-RPM modes, the system MUST accept the lathe's or tool's available power as an optional input; when supplied, the system MUST report a clear warning if the estimated required power exceeds it; when omitted, the system MUST still calculate and return the estimated power requirement without a feasibility comparison.
- **FR-015**: The system MUST present all calculated results with their units of measure clearly labeled, in both the console interface and the library's structured results, using the existing message-catalog mechanism (no turning-specific hard-coded strings).
- **FR-016**: The console interface and the library API MUST produce identical calculated results for identical inputs and calculation mode.
- **FR-017**: The system MUST support both metric units (mm, mm/rev, RPM, kW, N) and imperial units (inches, in/rev, RPM, HP, lbf), consistent with how drilling and milling handle unit systems: canonical metric internally, with imperial conversion at the process-orchestration layer.
- **FR-018**: The system MUST NOT implement facing, grooving, parting, threading, taper turning, or boring calculations as part of this feature; only straight (outside-diameter) turning is in scope.

### Key Entities

- **Turning Operation**: Represents a single calculation request; includes workpiece diameter, depth of cut, length of cut, selected material, selected turning tool, selected calculation mode, selected unit system, and optional power rating or target spindle speed, along with the resulting spindle speed, feed rate, machining time, cutting force, and power.
- **Turning Tool**: Represents a specific single-point turning tool type available for selection (e.g., by material/coating such as high-speed steel, cobalt, or carbide); includes reference cutting-speed and feed adjustment factors that combine with the selected workpiece material, following the same shape as the existing `DrillingTool`/milling tool entities.
- **Calculation Result**: Represents the structured output of a single Turning Operation (spindle speed, feed rate, machining time, cutting force, power, unit system used, and any warnings/errors), returned identically whether produced via the console interface or the library API.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can obtain recommended spindle speed, feed rate, machining time, cutting force, and power for a straight turning pass in under 30 seconds from opening the console interface.
- **SC-002**: Calculated spindle speed, feed rate, cutting force, and power values are each independently within 5% of published industry reference values for the same material, turning tool, and workpiece diameter.
- **SC-003**: 95% of users can successfully complete a single-material, single-tool standard-mode turning calculation on their first attempt via the console interface without needing external help.
- **SC-004**: Invalid input is identified and communicated within the same interaction, with zero calculations silently failing or producing incorrect results, in both the console interface and the library API.
- **SC-005**: A developer can perform a full turning calculation (including cutting force and power) through the library API alone, with no console interface involved, and receive the same result as the equivalent console session for identical inputs.
- **SC-006**: Selecting fixed-RPM or power-constrained mode changes only the spindle-speed derivation step; feed rate, machining time, cutting force, and power calculations remain the same formulas as standard mode given the resulting spindle speed, with zero duplicated calculation logic between modes.

## Assumptions

- Turning is added as a single-subtype process directly under `src/mfgparams/processes/machining/turning/` (mirroring `drilling/`), not as a multi-subtype process with an intermediate grouping layer (as `milling/` has with `end_milling`/`face_milling`), since only straight/OD turning is in scope for this feature.
- The existing `WorkpieceMaterial` registry's reference cutting speed and feed-per-revolution values are reused as-is for turning; no turning-specific material reference values are introduced.
- The initial turning tool list covers common single-point turning tool materials (e.g., high-speed steel, cobalt, carbide) using widely published standard reference cutting-speed and feed adjustment factors, consistent with how the drilling and milling tool lists were seeded; the exact list can be extended later without changing core module behavior.
- Cutting force is the natural *primary* mechanical quantity for turning's rotating-workpiece/stationary-tool geometry (unlike drilling/milling's rotating-tool geometry, where torque is the natural primary quantity), so turning reports cutting force as a new, first-class output (FR-009) rather than only reporting torque. Turning also continues to report torque and power via the same shared result fields drilling and milling already use — torque here is the spindle torque implied by the cutting force acting at the workpiece radius — for consistency with the other processes' result shape (Constitution Principle VI). Torque is not independently benchmarked for accuracy the way spindle speed, feed rate, cutting force, and power are (SC-002): it is an exact, deterministic function of cutting force and workpiece geometry, so its accuracy is entirely inherited from cutting force's — no separate reference-value comparison is needed.
- This feature ships only the English message-catalog entries required for turning's own labels and errors, reusing the existing catalog infrastructure (no new locale mechanism); additional languages remain a separate, later contribution as with drilling/milling.
- Facing, grooving, parting, threading, taper turning, and boring are deliberately deferred to a later feature, not an oversight; this mirrors how milling shipped end/face milling before later slices, and drilling shipped standard drilling before calculation modes.
