# Specification Quality Checklist: Console-Owned Message Catalogues

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-04
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (FR-005 resolved 2026-09-04 — see Clarifications)
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

- FR-005/FR-005a (the error-reporting contract once core stops owning translated error text) was the
  central open design question this slice existed to resolve, per
  [[mfgparams-core-i18n-constraint]]. Resolved 2026-09-04: core keeps English-only error text;
  console layers translation on top. See spec.md Clarifications.
- FR-005b (how the console re-renders a message when a single `code` covers more than one template,
  e.g. `INVALID_DIAMETER`'s zero/max cases): resolved 2026-09-04 during `/speckit-clarify` — `ErrorInfo`
  gains `message_key` + `kwargs` fields (renamed from the initially-drafted `message_id`/`params`
  during `/speckit-plan`, to match the existing `RegistryConfigError.message_key`/
  `MergeResult.notice_key` naming — see research.md #2); `code` is unaffected. See spec.md
  Clarifications.
- One follow-on design detail is explicitly deferred to `/speckit-plan`, not blocking here: the fate
  of the library API's `locale=` parameter now that it no longer affects `ErrorInfo.message`.
