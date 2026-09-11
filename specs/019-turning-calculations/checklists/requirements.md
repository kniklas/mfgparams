# Specification Quality Checklist: Turning Calculations Module

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-11
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- All items pass on the first validation pass. The feature description provided by the user was specific enough (naming the sibling processes to mirror, the calculation modes to support, and explicit out-of-scope variants) that no [NEEDS CLARIFICATION] markers were needed; reasonable defaults are documented in the Assumptions section instead.
- Updated during `/speckit-plan`'s Phase 0 research: formula research surfaced that turning's cutting-force/power calculation requires a **depth of cut** input distinct from workpiece diameter (analogous to milling's `axial_depth_of_cut`/`radial_depth_of_cut`), which the initial draft omitted. Added to FR-003, FR-009, FR-010, the User Story 1/2 acceptance scenarios, the Edge Cases, and the Turning Operation entity; re-validated, still passes all checklist items.
- Updated during `/speckit-tasks`/`/speckit-analyze` prep, in two rounds: first found that a generic `validate_depth_of_cut_mm` already exists in `src/mfgparams/validation.py` (added for milling); then, on closer reading of its actual bound (`max_depth_of_cut_mm` defaults to 50 mm, sized for milling cutters — too permissive for turning's ≤10 mm realistic depth of cut) and of `config.py`'s existing per-operation-bound precedent (drilling's `max_diameter_mm` vs. milling's own distinct `max_mill_diameter_mm`), settled on turning getting its own three validator functions and three `Configuration` bound fields (`validate_turning_diameter_mm`/`max_turning_diameter_mm`, `validate_turning_depth_of_cut_mm`/`max_turning_depth_of_cut_mm`, `validate_turning_length_of_cut_mm`/`max_turning_length_of_cut_mm`), reusing the existing `INVALID_DIAMETER`/`INVALID_DEPTH_OF_CUT`/`INVALID_LENGTH_OF_CUT` codes throughout — **zero new error codes**, not even the `INVALID_CUT_LENGTH` code an earlier pass had introduced. Corrected `data-model.md`, both library/CLI contracts, `research.md`, `quickstart.md`, and `tasks.md`. No change needed to `spec.md` itself (business-level requirements, not implementation-level codes/bounds).
- Ran `/speckit-analyze` (formal cross-artifact pass) after the above corrections. Found and remediated two issues in `spec.md` itself: (1) HIGH — the Assumptions section stated cutting force is reported "not torque", directly contradicting `data-model.md`/`contracts/library-api-turning.md`, which both populate a `torque` field for turning (reusing the shared `CalculationResult` shape per Constitution Principle VI); reworded the Assumptions entry to state torque is still returned (for shape-consistency with drilling/milling) but isn't independently accuracy-benchmarked in SC-002 since it's an exact deterministic function of cutting force and geometry. (2) MEDIUM — `spec.md` said "cut length" in 12 places while every other artifact (`plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`, `tasks.md`) says "length of cut" (deliberately, to match milling's reused `length_of_cut` field); swept `spec.md` to match. Two lower-severity coverage notes (FR-004's non-duplication not explicitly regression-tested; SC-006's no-duplicated-logic property verified by code review, not an automated task) were left as-is — acceptable per the same posture milling's original spec took.
