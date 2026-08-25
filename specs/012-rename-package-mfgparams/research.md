# Phase 0 Research: Rename Package to mfgparams

No items in Technical Context were marked `NEEDS CLARIFICATION` — this is a mechanical rename
within an already-established stack (Python, setuptools, pytest, Sphinx). The research below
covers the decisions needed to execute that rename safely, not technology selection.

## 1. New name confirmation

- **Decision**: The new distribution and import name is `mfgparams` for both
  (`pyproject.toml`'s `[project].name = "mfgparams"` and the importable package
  `src/mfgparams/`).
- **Rationale**: Taken directly from issue #62's stated target; confirmed in spec Assumptions.
  Using the identical string for both distribution and module name (rather than a
  hyphen/underscore pair like today's `machine-calc`/`machine_calc`) is simpler — `mfgparams`
  has no hyphen to begin with, so there is nothing to diverge.
- **Alternatives considered**: Keeping the current hyphen/underscore split pattern was
  considered and rejected as unnecessary complexity — `mfgparams` needs no hyphenated form.

## 2. Rename mechanism

- **Decision**: `git mv src/machine_calc src/mfgparams`, followed by a repo-wide, case-sensitive
  text substitution of `machine_calc` → `mfgparams` and `machine-calc` → `mfgparams` across
  tracked files, excluding the paths identified in item 5 below.
- **Rationale**: `git mv` preserves file history for the moved directory; a scripted
  substitution (not manual per-file editing) is the only way to reliably cover ~200 hits across
  174+32 files without missing occurrences, per FR-003/FR-008.
- **Alternatives considered**: An IDE "rename symbol" refactor only rewrites Python import
  references, not the arbitrary-text hits in `.toml`/`.md`/`.yml`/`.rst` files, so it alone is
  insufficient here and was rejected as the sole mechanism (it may still be used for the Python
  import edits specifically, as an implementation detail).

## 3. Exclusion list for the substitution

- **Decision**: The repo-wide substitution MUST skip:
  1. Any URL containing the literal GitHub repository slug `kniklas/machine-calc` (badges,
     issue links, the `LICENSE.md` copyright/notice line) — per spec Clarifications, the
     repository itself is not renamed by this feature.
  2. Gitignored, generated directories: `*.egg-info/`, `build/`, `dist/`, `.mypy_cache/`,
     `.ruff_cache/`, `.pytest_cache/` — these regenerate from source on the next build/test run
     and must not be hand-edited (stale copies would be misleading, not incorrect).
  3. Historical record entries that are supposed to name the old value on purpose: the new
     CHANGELOG entry documenting the rename (FR-007) and this feature's own spec/plan/research
     documents, which quote the old name as historical/contextual fact.
- **Rationale**: Blind substitution across every file would break working badge/issue links
  (item 1) and would edit/leave-stale files that are never committed anyway (item 2), while
  scrubbing the old name from historical record-keeping (item 3) would make the rename's own
  documentation unable to say what was renamed from what.
- **Alternatives considered**: Excluding only `.gitignore`-matched paths (skipping the URL
  carve-out) was considered and rejected — it would silently break the CI and codecov badges
  in `README.md` and the GitHub issue link in `LICENSE.md`, which is a regression this feature
  must not introduce.

## 4. Verification strategy (FR-008)

- **Decision**: Add a static test (e.g. `tests/static/test_no_old_package_name.py`, alongside
  the existing `tests/static/test_no_hardcoded_strings.py`) that walks tracked, non-generated
  files and asserts zero occurrences of `machine_calc` / `machine-calc`, excluding the same
  carve-outs as item 3 above (repo-slug URLs, and this feature's own historical
  spec/plan/CHANGELOG text, allow-listed by path).
- **Rationale**: A codified, CI-enforced check is the only way to make "no stale references"
  (User Story 2, SC-001) durable — a one-time manual grep at implementation time would not
  catch future regressions (e.g., a contributor pasting old example code from an old issue).
- **Alternatives considered**: A one-off shell script run manually before merge was considered
  and rejected because it isn't enforced by CI and would not catch future reintroductions of the
  old name, unlike a committed test.

## 5. Console-script / CLI entry point naming

- **Decision**: Rename the `[project.scripts]` entry point from `machine-calc = ...` to
  `mfgparams = "mfgparams.__main__:main"`.
- **Rationale**: The installed CLI command name is part of the package's public identity
  (FR-001/FR-002 scope: "distribution name" and "importable module name" both surface through
  this entry point); leaving the old command name installed would be an inconsistent partial
  rename and a stale reference by FR-003's own standard.
- **Alternatives considered**: Keeping `machine-calc` as a second, alias entry point pointing at
  the same `main()` was considered and rejected — it is exactly the kind of
  backward-compatibility shim FR-006 explicitly rules out.

## 6. Sphinx documentation update strategy

- **Decision**: Update `docs/source/conf.py`'s project metadata and every `.rst` file's
  `automodule`/`autoclass` (or equivalent) directives from `machine_calc.*` to `mfgparams.*`,
  then rebuild docs locally to confirm no broken autodoc references before merge.
- **Rationale**: Constitution Principle VII requires the Sphinx build to keep passing and stay
  synchronized with the code; autodoc directives are literal Python import paths, so they break
  immediately (import error at doc-build time) if left pointing at the old module name.
- **Alternatives considered**: None — this is a direct, mechanical consequence of the module
  rename with no reasonable alternative.

## 7. Build/tooling config repointing

- **Decision**: Update every CI/tooling config that hard-codes the old package path as a
  target — `[tool.pytest.ini_options].addopts` (`--cov=machine_calc`), `[tool.coverage.run
  ].source`, `[tool.mypy].files`, `[tool.setuptools.package-data]` key, and any `bandit`/
  `radon`/`xenon` invocation in `.github/workflows/ci.yml` that names `src/machine_calc` — to
  point at `mfgparams`/`src/mfgparams`.
- **Rationale**: Constitution Principle IX gates (type-checking, complexity, security scanning)
  must keep actually scanning the real source tree; a config still pointing at
  `src/machine_calc` after the `git mv` would silently scan nothing (empty/missing path) rather
  than failing loudly, which is worse than a hard failure.
- **Alternatives considered**: Relying on tool defaults (no explicit path) was considered for
  some tools and rejected — several of these tools (coverage, pytest `--cov`) require an
  explicit target and would otherwise report 0% coverage silently rather than erroring.

**Addendum (post-`/speckit-analyze` finding E1)**: A repo-wide sweep for `MACHINE_CALC_*`
found three environment variables, not one — `MACHINE_CALC_LOCALE` (locale resolution,
`src/mfgparams/i18n.py`), `MACHINE_CALC_RUN_PERFORMANCE_TESTS` (the performance-suite opt-in
gate, `tests/performance/conftest.py` and `.github/workflows/ci.yml`'s performance job), and
`MACHINE_CALC_PERFORMANCE_SUMMARY_PATH` (originally the only one documented here). All three
follow the same rename rule (drop the alias, no dual name, per FR-006) and are now covered
together in `tasks.md` T007.
