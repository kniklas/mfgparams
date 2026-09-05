# Data Model: CI Path-Based Job Selection

This feature has no runtime data model — its "entities" are CI configuration concepts that
exist only inside `ci.yml` and its static tests. They are documented here in the same spirit
as a data model, because the mapping between them is exactly what could silently drift.

## Path Category

A named group of path globs that one or more CI jobs depend on.

| Field | Description |
|---|---|
| `name` | Stable identifier, also the `dorny/paths-filter` filter key and the `changes` job's output name (e.g. `needs.changes.outputs.python`). |
| `globs` | Ordered list of glob patterns (`dorny/paths-filter` syntax) that put a changed file in this category. |
| `is_catch_all` | `true` only for `other` — matches any *genuinely unanticipated* path (FR-003), explicitly excluding the known-non-code paths below, not just the other three named categories. |

Instances (see research.md #2 for rationale):

| `name` | `globs` | `is_catch_all` |
|---|---|---|
| `python` | `src/**`, `tests/**`, `pyproject.toml`, `tox.ini`, `scripts/sync_agent_integrations.py`, `scripts/setup_skill_symlinks.py` | false |
| `docs` | `docs/**` | false |
| `ci_config` | `.github/workflows/**` | false |
| `skills` | `.github/skills/**`, `.claude/**` | false |
| `packaging_metadata` | `README.md`, `LICENSE.md` | false |
| `other` | `**`, then a `!`-prefixed exclusion entry for every glob above **and** every known-non-code path from spec.md's Assumptions (`specs/**`, `.github/skills/**`, root `*.md`, `.claude/**`) — evaluated in its **own** `dorny/paths-filter` step with `predicate-quantifier: every` | true |

**Corrections (all three found during live quickstart validation, not planning):**

1. The first implementation of `other` negated only the three named categories' globs,
   omitting the known-non-code paths spec.md's own Assumptions section already named. That
   made a specs-only change match `other` (nothing else) and therefore run every filtered job
   anyway — exactly the case this feature exists to skip, and the opposite of `other`'s intent
   as a safety net for paths nobody anticipated rather than a catch-all for paths already
   named and deliberately excluded elsewhere in this same spec.
2. Fixing (1) as a single `!(src/**|tests/**|...|specs/**|...)` extglob string still failed
   the same live check: `dorny/paths-filter`'s live log showed
   `specs/016-ci-path-based-selection/quickstart.md` matching `other = true` even with
   `specs/**` inside that negation. A single extglob negation containing `**` inside its
   alternatives is unreliable in the underlying matcher. Switched to a *list*: a bare `**`
   positive entry, then one `!`-prefixed entry per excluded glob.
3. The list form from (2) *still* failed the identical live check, still reporting
   `other = true` for the same file. Root cause: `dorny/paths-filter`'s `predicate-quantifier`
   (default `some`) means a filter matches if **any** listed pattern matches - and a bare
   `**` always matches, so every negation listed after it is moot under the default. The
   list-plus-negation idiom only works under `predicate-quantifier: every` (all listed
   patterns must match simultaneously), which is a setting for the whole `paths-filter` step,
   not a per-filter option. Since `python`/`docs`/`ci_config` are plain OR-lists that need the
   default `some` (a file need only match one of several globs to be `python`, say), `other`
   was moved into its **own** `paths-filter` step with `predicate-quantifier: every` set
   explicitly, leaving the first step's default untouched for the other three filters.
4. Found by Copilot's round-2 review of PR #89, not live validation: two of the four
   known-non-code paths were never actually safe to fully skip. `.github/skills/**`/
   `.claude/**` broke `lint`'s `setup_skill_symlinks.py --check` (a skill added without its
   symlink, or a broken symlink, would merge undetected), and `README.md`/`LICENSE.md` are
   named as `pyproject.toml`'s `readme`/`license-files` (a build input, so `build` must run
   when either changes). The `skills`/`packaging_metadata` categories above narrow the fix to
   exactly the jobs that need it (`lint`, `build`) rather than re-running the whole toolchain
   for these paths the way folding them into `other` would. `specs/**` and the remaining root
   `*.md` files are unaffected — see `repo-invariants` in the Job Path Policy table below for
   the separate, third gap this same review round found in `test`.

## Job Path Policy

The association from one existing CI job to the path categories that cause it to run, plus its
fail-open behavior.

| Field | Description |
|---|---|
| `job` | The CI job name (`ci.yml` job key). |
| `depends_on_categories` | Set of `Path Category.name` values; the job runs if *any* is true for the current run. |
| `filtered` | `false` for jobs FR-006 explicitly excludes from path selection — they run on every non-scheduled trigger exactly as today. |
| `fails_open_on_changes_failure` | `true` for every `filtered: true` job — see research.md #5. Not applicable when `filtered: false`. |

Instances:

| `job` | `depends_on_categories` | `filtered` |
|---|---|---|
| `lint` | `{python, skills, ci_config, other}` | true |
| `complexity` | `{python, ci_config, other}` | true |
| `typecheck` | `{python, ci_config, other}` | true |
| `security` | `{python, ci_config, other}` | true |
| `test` | `{python, ci_config, other}` | true |
| `build` | `{python, packaging_metadata, ci_config, other}` | true |
| `docs` | `{python, docs, ci_config, other}` | true |
| `dependency-scan` | N/A | false (FR-006) |
| `sync-agent-integrations` | N/A | false (FR-006; schedule/workflow_dispatch only, unaffected either way) |
| `performance` | N/A | false — informational-only (`continue-on-error`), out of `ci-ok`'s gate already; left running on every trigger unchanged, since narrowing it would change SC-003 for no benefit (it costs nothing to `ci-ok`'s outcome) |
| `repo-invariants` | N/A | false — never filtered, by design: re-runs `test_no_old_package_name.py`/`test_no_old_layout.py` (also collected inside `test`) unconditionally on every non-scheduled trigger, because both walk every git-tracked file and a violation can appear under any path category `test` is allowed to skip for (added in Copilot's round-2 review of PR #89; see data-model.md Path Category Corrections note #4) |
| `changes` | N/A | N/A — this is the filter producer, not a filtered job. Excludes both `schedule` and, since round 2, `workflow_dispatch` too (`if: github.event_name != 'schedule' && github.event_name != 'workflow_dispatch'`) — every filtered job already bypasses `changes`'s outputs on manual dispatch (FR-006), so there is nothing left for `changes` itself to compute on that trigger, and running it anyway only gave a checkout/filter failure a way to fail a manual run nothing downstream needed it for |
| `quality-summary` | N/A | false — reporting only; renders whatever result each dependency reports, including `skipped` (research.md #4) |
| `deploy-docs` | N/A | false — `push`-to-`main`-only, independent of this feature |

Every `ci_config` and `other` entry above exists because FR-004 (CI-config changes run
everything) and FR-003 (unmatched paths run everything) apply identically to all seven
filtered jobs — there is no job for which either exception is narrower than the others.
`skills` and `packaging_metadata`, by contrast, are each read by exactly one job (`lint`,
`build` respectively) — narrower carve-outs for the two round-2 gaps that were specific to
what those two jobs individually check, not general to the whole toolchain.

## `ci-ok` Dependency Result Classification

The predicate `ci-ok`'s assertion step applies to each entry in its `needs:` map.

| GitHub Actions job `result` | Blocks `ci-ok`? | Why |
|---|---|---|
| `success` | No | Ran and passed — today's behavior, unchanged. |
| `skipped` | No (changed by this feature) | Either intentionally excluded by path selection (decision #3) or the job legitimately had nothing to do; either way, FR-005 requires this to be non-blocking. |
| `failure` | Yes | Ran and failed — unchanged (FR-007: this feature never changes a job's own pass/fail outcome). |
| `cancelled` | Yes | Unchanged — a cancelled run is not a clean signal either way, so it stays conservative. |

`changes` itself is a member of `ci-ok`'s `needs:` and is classified by this same table; since
it has no `needs:` of its own and runs on every non-scheduled trigger, its `result` can only
ever be `success` or `failure` in practice — never `skipped` — so no special case is required
for it here (research.md #5).
