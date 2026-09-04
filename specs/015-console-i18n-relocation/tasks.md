---

description: "Task list for feature implementation"
---

# Tasks: Console-Owned Message Catalogues

**Input**: Design documents from `/specs/015-console-i18n-relocation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Test tasks ARE included. Constitution Principle II is NON-NEGOTIABLE, and FR-005/FR-005a/
FR-005b/FR-007/SC-001/SC-006 all explicitly demand automated enforcement rather than convention.

**Organization**: Grouped by user story so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 — maps to the user stories in spec.md
- Exact file paths are given in every task

## Path Conventions

Single project, `src/` layout: `src/mfgparams/`, `tests/` at repository root (unchanged from 014).

## Traceability note

FR-005b spans Foundational and US2 by design: `ErrorInfo` gains its `message_key`/`kwargs` fields in
Foundational (T003, needed before any story touches it), while populating them at every call site and
proving the re-rendering behaviour lands in US2 (T012, T016). US1 does not depend on T003 at all — it
never touches `ErrorInfo` — so it is not blocked by it despite both being in scope for this feature.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the pre-change baseline that "no English-locale behaviour change" (SC-002,
SC-003) is verified against.

- [X] T001 Capture the pre-change baseline in `specs/015-console-i18n-relocation/baseline.md`: full
      `pytest --cov` pass/skip counts and coverage percentage, and the complete current key list of
      `src/mfgparams/locales/en.py`'s `MESSAGES` dict (this is the move's checklist — every `cli.*`/
      `material_type.*` key must appear, moved, in the console's catalogue by the end of US1)
- [X] T002 [P] Confirm the unmodified tree is green: `pip install -e ".[console,dev]"`, then `tox`
      passes

**Checkpoint**: Baseline recorded; safe to start.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Give `ErrorInfo` its new fields and give the console its own loader/catalogue
skeleton — the two things every later task builds on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `message_key: str` and `kwargs: tuple[tuple[str, object], ...] = ()` fields to
      `ErrorInfo` in `src/mfgparams/models.py`, updating its docstring per
      [data-model.md](./data-model.md) (naming matches `RegistryConfigError.message_key` — research.md #2)
- [X] T004 [P] Create `src/mfgparams/console/locales/__init__.py` and
      `src/mfgparams/console/locales/en.py` (an empty `MESSAGES: dict[str, str] = {}` scaffold, with a
      module docstring stating its ownership scope per
      [catalogue-ownership-contract.md](./contracts/catalogue-ownership-contract.md)). Spell it
      "catalog" in the docstring, matching `mfgparams/locales/en.py:1`'s existing wording — the
      planning documents say "catalogue" (British), but the code they describe already says "catalog"
      (American); new source files follow the code's spelling, not the planning prose's
- [X] T005 [P] Create `src/mfgparams/console/i18n.py`, mirroring `src/mfgparams/i18n.py`'s
      `_load_catalog`/`translate`/`has_message`/`clear_catalog_cache`/`get_locale` verbatim in
      structure, scoped to `mfgparams.console.locales.*` (research.md #1). Do **not** duplicate
      `get_raw_locale` — it has no catalogue dependency and stays a `mfgparams.i18n` import wherever
      it is used (material-translation lookups, Story 3, untouched). Same spelling note as T004:
      "catalog," matching `mfgparams/i18n.py:1`

**Checkpoint**: `ErrorInfo` has its new (unused-so-far) fields; the console has its own loader and an
empty catalogue ready to receive content. US1 and US2 can now proceed in parallel — both touch
`console/cli.py`, but at disjoint locations (T007's import block vs. T014's error-display call), so
there is no real file conflict.

---

## Phase 3: User Story 1 - Find every console string in one place (Priority: P1) 🎯 MVP

**Goal**: Every string `mfgparams.console` displays resolves from a catalogue the console owns, with
the single documented `console.missing_dependency*` exception staying in core.

**Independent Test**: Search the console package for every displayed string and confirm each
resolves through `mfgparams.console.i18n`, not `mfgparams.i18n` — except the one exception.

- [X] T006 [US1] Move every `cli.*`/`material_type.*` entry out of `src/mfgparams/locales/en.py`
      into `src/mfgparams/console/locales/en.py`, preserving text and section comments verbatim
      (research.md #4). Afterward, `mfgparams/locales/en.py` MUST contain only `error.*`, `warning.*`,
      `notice.*`, and `console.missing_dependency*` entries. Verified: 60 keys moved, 33 stayed
      (60+33=93, matching baseline.md's pre-change total exactly).
- [X] T007 [US1] Update `src/mfgparams/console/cli.py`'s import line (currently line 37) so
      `translate`, `has_message`, and `get_locale` come from `mfgparams.console.i18n`; keep
      `get_raw_locale` imported from `mfgparams.i18n` (T005's exception). **Delivered wider than
      written**: two call sites (`RegistryConfigError.message_key`, `materials_load_notice()`'s
      `notice_key`) render *core*-owned keys and needed a second import, `_translate_core` aliasing
      `mfgparams.i18n.translate`, kept separate from the console's `translate`. Also added
      `_render_error()` (FR-005a/FR-006) and rewired every immediate re-prompt validation call
      (`_prompt_diameter`, `_prompt_depth`, `_prompt_validated_length`'s six milling lambdas) to
      construct its `ErrorInfo` with `DEFAULT_LOCALE` and display it through `_render_error` — these
      constructed `ErrorInfo` directly, bypassing `calculate()`/T013 entirely, so FR-005's "always
      English" invariant did not hold for them until fixed here. Also found and fixed: two labels
      embedded inside core error text (`error.invalid_depth_of_cut.*`, `error.invalid_engagement`)
      resolve via a `cli.label.*` key that this task moves to console — added
      `cli.label.axial_depth_of_cut`/`radial_depth_of_cut`/`width_of_cut` back to
      `mfgparams/locales/en.py` as a second, narrow, documented FR-004 exception (spec.md Assumptions
      is corrected accordingly — it originally claimed `console.missing_dependency*` was the only one).

### Tests for User Story 1

- [X] T008 [P] [US1] Add `tests/static/test_console_catalogue_ownership.py`
      ([catalogue-ownership-contract.md](./contracts/catalogue-ownership-contract.md), SC-001): for
      every string literal `console/cli.py` passes to `translate()`/`has_message()`, assert the key
      exists in `mfgparams.console.locales.en.MESSAGES`; assert `console.missing_dependency*` is the
      sole exception, present in `mfgparams.locales.en.MESSAGES` and absent from the console's.
      Verified the test actually catches a regression (re-added a `cli.*` key to core's catalogue,
      confirmed it failed, reverted). 4/4 pass.
- [X] T009 [P] [US1] In the same file, add two reciprocal checks (FR-004, SC-004): (a) no `error.*`/
      `warning.*`/`notice.*`/`console.missing_dependency*` key is missing from
      `mfgparams.locales.en.MESSAGES` after T006's move — confirms nothing core still needs (FR-005)
      was over-relocated; (b) **none** of the keys now present in `mfgparams.console.locales.en
      .MESSAGES` (except `console.missing_dependency*`, which never belongs there) is still present in
      `mfgparams.locales.en.MESSAGES` — this is the actual automated enforcement of FR-004's "no alias,
      shim, or dual lookup path" and of SC-004's "enforced automatically"; without it, a `cli.*` key
      left behind in core would pass every other test in this feature undetected. **Delivered as
      set-based checks** against `message_key=` literals found by parsing `validation.py`/
      `_calculate.py`/drilling `__init__.py` (check a) and against the two catalogues' full key sets
      (check b), rather than a hardcoded key list — self-maintaining if error entries change later.
      Explicitly allowlists the three T007-discovered dual-presence keys. 4/4 pass.
- [X] T010 [US1] Add a short "Adding or changing a user-facing string" note to `README.md` (near the
      existing materials-translation section, ~line 289) naming the console-owned vs. core-owned
      catalogues and linking `contracts/catalogue-ownership-contract.md` (FR-008, SC-007)
- [X] T011 [US1] Run `tests/integration/test_cli_*.py` (the full existing console/CLI integration
      suite) and confirm no behavioural change for the English locale — same prompts, same output.
      102/102 pass.

**Checkpoint**: Every console-rendered string resolves from the console's own catalogue; English
behaviour is provably unchanged. This alone is a coherent, releasable increment.

---

## Phase 4: User Story 2 - Get a readable error without the console installed (Priority: P1)

**Goal**: `CalculationResult.error` stays fully usable — English text, no console import — without
the `console` extra, and the console re-renders translated error text when a non-English locale is
active, using `message_key`/`kwargs` rather than `code`.

**Independent Test**: In an environment without the `console` extra, trigger a validation error via
the library API and confirm the result is usable in English; with the extra installed and a
non-English locale active, confirm the console re-renders correctly.

- [X] T012 [US2] Add `message_key=`/`kwargs=` to every `ErrorInfo(...)` call site in
      `src/mfgparams/validation.py` (~25 sites; see error codes at lines 65-386), using each call's
      existing catalogue key as `message_key` and its existing `translate()` keyword arguments as
      `kwargs` (data-model.md). **Delivered wider than written**: two more construction sites exist
      outside `validation.py` — `processes/machining/milling/_calculate.py` (6 sites) and
      `processes/machining/drilling/__init__.py` (6 sites) — found by grepping the whole tree for
      `ErrorInfo(` after finishing the ~25 in `validation.py`; all 35 total sites now populate both
      fields. Verified: 1029 passed, 10 skipped, 99.30% coverage, no regressions.
- [X] T013 [US2] On every public `calculate_*`/`calculate` entry point (drilling `__init__.py:347`,
      end-milling `__init__.py:73`, face-milling `__init__.py:73`), keep the `locale: str = "en"`
      parameter for signature compatibility, but stop threading it into message-text construction:
      `ErrorInfo.message` is now built via `translate(DEFAULT_LOCALE, message_key, **dict(kwargs))`
      regardless of the caller's `locale`. Update each docstring to note `locale` no longer affects
      `CalculationResult.error.message` (FR-005, FR-007; resolves the parameter's fate left open by
      plan.md, decided here rather than deferred further — keeping it avoids a second breaking
      signature change on top of FR-005b's dataclass change). **Delivered more surgically than
      written**: the task text suggested overriding `locale` wholesale at the top of each entry
      point. That would have also broken `feasibility_warning` (`CalculationResult.feasibility_warning`,
      built via `translate(locale, "warning.feasibility", ...)` in each `_build_result`), which is
      NOT part of `ErrorInfo` and is untouched by FR-005/this feature. Fixed by introducing a
      separate `message_locale = DEFAULT_LOCALE` name, threaded only into the error-producing calls
      (`_validate_and_prepare`/`_resolve_material_and_tool`/`_validate_geometry`/
      `_validate_mode_inputs`/`_compute_metrics`), while `_build_result` keeps receiving the
      caller's real `locale` so `feasibility_warning` translation is unaffected.
- [X] T014 [US2] Update `console/cli.py`'s error-display path (the `cli.result.error` rendering) to
      re-render via `mfgparams.console.i18n.translate(locale, error.message_key, **dict(error.kwargs))`
      when the active console locale is non-English, and to display `error.message` verbatim when it
      is English ([error-info-contract.md](./contracts/error-info-contract.md) items 5-6). **Delivered
      as part of T007** (see its note): added a shared `_render_error()` helper implementing exactly
      this branch, with a `has_message()` guard so a locale/key with no console-catalogue entry (true
      for every key today, since no non-English catalog ships) falls back to `error.message` instead
      of leaking the raw key. Used at all four display sites, not just `cli.result.error` — the three
      immediate re-prompt-validation sites (`_prompt_diameter`, `_prompt_depth`,
      `_prompt_validated_length`) construct `ErrorInfo` directly, bypassing `calculate()` and T013's
      fix entirely, so they needed the same treatment for FR-005/FR-005a to hold everywhere, not just
      on the final result.

### Tests for User Story 2

- [X] T015 [P] [US2] Rewrite `tests/contract/test_library_api_milling_locale.py` (FR-007): assert
      `message` is English regardless of `locale=`/`MFGPARAMS_LOCALE`; assert `message_key`/`kwargs`
      are populated and correct; keep the existing `_FIXTURE_LOCALE` pattern but point it at the
      console's re-rendering path (T014) rather than the library API's `locale` parameter.
      **Delivered differently than written**: the old `_FIXTURE_LOCALE`/catalog-cache-injection
      pattern tested core's *own* per-locale fallback, which no longer exists at the library-API
      level (FR-005 makes it moot) — replaced with direct assertions that `message`/`message_key`/
      `kwargs` are identical across `locale="en"`/`"fr"`/`""`/`MFGPARAMS_LOCALE` set, plus a new
      `message_key`/`kwargs` correctness test and the shared-`code`-distinct-`message_key` case
      (overlapping with, not replacing, T016's dedicated SC-006 test). 16/16 pass.
- [X] T016 [P] [US2] Add `tests/unit/test_error_info_rerendering.py` (SC-006): confirm
      `validate_diameter_mm`'s zero/max cases (or `validate_mill_diameter_mm`'s) share `code` but have
      distinct `message_key`s, and that re-rendering each through a fixture non-English catalogue
      produces two distinct translated strings. 3/3 pass.
- [X] T017 [US2] Run [quickstart.md](./quickstart.md) checks 1-3 to confirm the library API is usable
      with the `console` extra uninstalled and that a shared `code` re-renders distinctly. All 3
      pass as written.

**Checkpoint**: `CalculationResult.error` is fully usable without the console; the console re-renders
correctly when non-English. Both P1 stories together deliver the slice's substance.

---

## Phase 5: User Story 3 - Keep data translations where the data lives (Priority: P2)

**Goal**: Prove `WorkpieceMaterial.translations` and its schema are untouched, so "single source of
UI strings" is never misread as reaching material data too.

**Independent Test**: Confirm the schema and material-name resolution are unchanged by this feature.

- [X] T018 [P] [US3] Add or extend a regression test in `tests/contract/test_materials_config_schema.py`
      asserting `WorkpieceMaterial.translations` and its TOML schema are unchanged by this feature.
      Added `test_translations_schema_and_resolution_are_unchanged_by_015`. 11/11 pass in that file.
- [X] T019 [P] [US3] Add a test confirming `console/cli.py`'s material-display-name lookup still
      resolves via `get_raw_locale`/`WorkpieceMaterial.translations` data, not via either message
      catalogue (SC-005). **No new test added** — found this is already exactly what
      `tests/integration/test_cli_materials_config.py::test_translated_name_shown_for_active_locale`
      and `::test_unsupported_locale_falls_back_to_english_name` assert (a translated material name
      that exists only in config data, never in either catalogue, is shown/falls back correctly).
      Both passed unmodified throughout this feature's implementation — confirmed by running them
      in isolation. Adding a near-duplicate test would not increase confidence.

**Checkpoint**: All three user stories independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 [P] Add an `## [Unreleased]` entry to `CHANGELOG.md` describing the breaking `ErrorInfo`
      shape change and the catalogue relocation — no version bump (spec Assumptions, mirroring 014's
      FR-018 precedent)
- [X] T021 [P] Full regression: `pytest --cov=mfgparams --cov-report=term-missing`, `mypy
      src/mfgparams`, `ruff check src/mfgparams tests` all green (quickstart.md check 5); coverage at
      or above the project's existing threshold. Also ran the actual CI gate commands from
      `.github/workflows/ci.yml`: `black --check`, `scripts/check_maintainability.py` (radon MI),
      `bandit -r src -ll`. All green: 1044 passed, 10 skipped, 99.06% coverage (baseline was 99.30%
      on 1029 tests; the small drop is more error-path lines now covered, not less testing). Fixed 3
      `ruff` line-length violations found along the way. `black`/`ruff format` flag 5/8 pre-existing
      files unrelated to this feature (verified via `git stash` against the pre-change tree) — left
      untouched, out of scope.
- [X] T022 Grep the repository for any remaining `mfgparams.i18n` import inside `console/cli.py`
      beyond `get_raw_locale` — must be an empty result. (The `cli.*`/`material_type.*`-key half of
      this check is enforced automatically by T009(b) now, not manually here — this task only covers
      the import-site half, which has no equivalent automated test.) **Finding**: one more import
      exists — `from mfgparams.i18n import translate as _translate_core` (T007) — deliberate and
      documented, not accidental drift: `RegistryConfigError.message_key`/`materials_load_notice()`'s
      `notice_key` are core-owned keys that must render via core's `translate`, not the console's.
      This task's real intent — no *unintentional* core-catalogue coupling crept back in — holds;
      the two `mfgparams.i18n` imports (`get_raw_locale`, `translate as _translate_core`) are both
      named, commented at their call sites, and structurally necessary.
- [X] T023 Check `.github/skills/**` and `docs/source/*.rst` for any description of the old
      single-core-catalogue layout (Principle XI precedent, 014's T045-T047); correct any found, skip
      if none reference it. `.github/skills/**` had no matches. `docs/source/milling-api.rst:190`
      (the "add a new sub-operation" guide) said "add its prompts to the message catalog" without
      naming which one, and named the entry point `cli.py` rather than `console/cli.py` — the latter
      a 014 leftover found opportunistically while here, not a 015 regression. Both corrected.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phase 3-5)**: All depend on Foundational. US1 and US2 are independent of each
  other (see Traceability note) and may run in parallel or in either order; US3 depends on neither
  functionally but is easiest to verify once US1/US2 have landed, since it is proving a negative.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational (T004, T005). No dependency on US2.
- **US2 (P1)**: Depends only on Foundational (T003). No dependency on US1 — T007 (US1, the import
  block at `console/cli.py:37`) and T014 (US2, the error-display call at `console/cli.py:438`) touch
  disjoint regions of the same file, not the same block; there is no real ordering requirement, since
  T014's call is written fully-qualified (`mfgparams.console.i18n.translate(...)`) and doesn't depend
  on T007's import change. Either order is fine.
- **US3 (P2)**: Independent of US1/US2's code; depends on Foundational only in the trivial sense that
  nothing else has broken yet.

### Parallel Opportunities

- T004, T005 — disjoint new files, fully parallel.
- T008, T009 — same new test file but independent assertions; write together, not literally parallel
  processes.
- T015, T016 — disjoint test files, fully parallel.
- T018, T019 — disjoint test files, fully parallel.
- T020, T021 — disjoint files, fully parallel.

---

## Parallel Example: Foundational

```bash
Task: "Create src/mfgparams/console/locales/__init__.py and en.py scaffold"
Task: "Create src/mfgparams/console/i18n.py mirroring mfgparams/i18n.py"
```

## Parallel Example: User Story 2 tests

```bash
Task: "Rewrite tests/contract/test_library_api_milling_locale.py per FR-007"
Task: "Add tests/unit/test_error_info_rerendering.py per SC-006"
```

---

## Implementation Strategy

### MVP scope

**User Story 1 alone** is a coherent, releasable increment — the console owns its own strings. In
practice both P1 stories (US1, US2) should land in the same pull request: US2 is what makes the
slice's central, previously-open design question (spec Clarifications) actually true in code, and
shipping US1 without it would leave `ErrorInfo` unchanged and the ownership split half-finished.

### Incremental delivery

1. Setup + Foundational → `ErrorInfo` fields exist, console catalogue/loader skeleton exists.
2. US1 → console strings relocated and enforced → **checkpoint**.
3. US2 → `ErrorInfo` re-rendering contract implemented and tested → **checkpoint**.
4. US3 → proven untouched.
5. Polish → gates green, changelog written, ready for review.

---

## Notes

- `[P]` tasks touch different files and have no incomplete dependencies.
- This feature cuts **no release**; changes accumulate under `## [Unreleased]` toward the same
  2.0.0 as 014, once slices 016-017 land and before issue #40 publishes.
- Do not add a compatibility shim or dual lookup path for a relocated key at any point, even
  temporarily — FR-004 forbids it and T009 will fail on it.

---

## Phase 7: Convergence

Appended by `/speckit-converge` on 2026-09-05, after Phases 1-6 completed (23/23 tasks, 1044
passed/10 skipped/99.06% coverage, tox/mypy/ruff/black/radon-MI/bandit all clean). Both items are
documentation-only drift in planning artifacts, found by independently re-verifying the finished
implementation against spec.md/plan.md/data-model.md rather than trusting prior task-completion
markers — no functional gap, no application code change.

- [X] T024 Update `plan.md`'s Project Structure comment on `mfgparams/locales/en.py` (currently
      "...only — cli.\*/material_type.\* entries move out (FR-001)") to note the three
      `cli.label.*` keys that stay in **both** catalogues (T007's finding, already documented in
      spec.md's Assumptions, research.md #4's addendum, and both contracts — plan.md is the one
      artifact that still doesn't say so). In the same pass, record in plan.md the `locale=`
      parameter decision spec.md explicitly delegated to it ("a plan-level decision, see
      Assumptions") but which plan.md never actually made — it exists only in tasks.md T013 today
      per FR-005, plan: Assumptions (partial)
- [X] T025 [P] Add a one-line cross-reference to `data-model.md`'s "Console catalogue" and "Core
      catalogue" entity descriptions noting the same three-key dual-presence exception (T007),
      consistent with how `contracts/catalogue-ownership-contract.md` already documents it
      per FR-004, plan: data-model.md (partial). **Delivered narrower than written**: data-model.md
      has no separate "Core catalogue" section to begin with (only "ErrorInfo (changed)" and
      "Console catalogue (new)" — core's own catalogue isn't itself a new-or-changed entity, so it
      was never given one). Added the exception note to the "Console catalogue" row only, worded to
      not reference a nonexistent second section.
