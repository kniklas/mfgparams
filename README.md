# mfgparams

[![CI](https://github.com/kniklas/mfgparams/actions/workflows/ci.yml/badge.svg)](https://github.com/kniklas/mfgparams/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kniklas/mfgparams/branch/main/graph/badge.svg)](https://codecov.io/gh/kniklas/mfgparams)

A Python library and interactive command-line tool for metal machining
calculations. It covers **drilling** (twist drills) and **milling** (end
milling and face milling), reporting spindle speed, feed rate, machining
time, torque and required power — plus material removal rate for milling.

📖 **[Full generated documentation (Sphinx)](https://kniklas.github.io/mfgparams/)** —
published automatically to GitHub Pages on every merge to `main`.

> **Status**: Early implementation (drilling + milling calculation engines
> and CLI).
> Full end-user/developer documentation and CI/CD automation are tracked in
> [`specs/001-metal-drilling-calc/tasks.md`](specs/001-metal-drilling-calc/tasks.md)
> (Polish phase) and will replace this placeholder README.

## License

`mfgparams` is **free for noncommercial use** (personal, hobby, research,
education, evaluation, etc.) under the
[PolyForm Noncommercial License 1.0.0](LICENSE.md). Any commercial use —
using the software inside a for-profit business, in a paid product or
service, or any other revenue-generating context — requires a separate,
paid commercial license from the copyright holder. To request one, open an
issue: <https://github.com/kniklas/mfgparams/issues/new>. See
[`LICENSE.md`](LICENSE.md) for the full terms; all rights not expressly
granted there, including all commercial rights, are reserved.

## Install (development)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip   # needed on Python 3.9's bundled pip (<21.3),
                                       # which predates PEP 660 editable-install support
pip install -e ".[dev]"
```

## Use as a library

```python
from mfgparams import calculate, UnitSystem, CalculationMode

result = calculate(
    diameter=10,
    depth=25,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
)
print(result)
```

### Milling

End milling and face milling have their own entry points, since their inputs
differ from drilling's:

```python
from mfgparams import calculate_end_milling, calculate_face_milling

# End milling: a slot/profile cut, described by axial and radial depth of cut.
result = calculate_end_milling(
    diameter=10,               # cutter diameter, mm (METRIC) or in (IMPERIAL)
    axial_depth_of_cut=2,
    radial_depth_of_cut=5,
    feed_per_tooth=0.05,       # mm/tooth or in/tooth
    number_of_teeth=4,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)
print(result.material_removal_rate)  # cm3/min (METRIC) or in3/min (IMPERIAL)

# Face milling: a facing pass, described by axial depth and width of cut.
result = calculate_face_milling(
    diameter=50,
    axial_depth_of_cut=1.5,
    width_of_cut=40,
    feed_per_tooth=0.15,
    number_of_teeth=5,
    length_of_cut=200,
    material="Mild Steel",
    tool="Carbide",
)
```

Milling has its own tool catalogs, listed with `list_end_mill_tools()` and
`list_face_mill_tools()`. Drilling results always leave
`material_removal_rate` as `None`.

Both entry points also accept the same `mode`/`target_rpm`/`available_power`
arguments as drilling's `calculate()` (see "Constrained calculation modes"
below) — for example `calculate_end_milling(..., mode=CalculationMode.FIXED_RPM,
target_rpm=3000)`.

See `specs/009-milling-calculations/quickstart.md` and
`specs/010-milling-calculation-modes/quickstart.md` for full scenarios.

### Constrained calculation modes

Two opt-in modes are available alongside the default `STANDARD` mode:

```python
# Power-constrained: reduce spindle speed to fit an available power budget.
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=1.2,  # kW (METRIC) or HP (IMPERIAL)
)

# Fixed-RPM: calculate from a caller-supplied target spindle speed.
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    mode=CalculationMode.FIXED_RPM,
    target_rpm=500,
)
```

See `specs/002-constrained-calculation-modes/quickstart.md` for full
scenarios, including error handling (`INFEASIBLE_POWER_BUDGET`,
`INVALID_TARGET_RPM`, `MODE_CONFLICT`).

## Use the interactive CLI

```bash
python -m mfgparams
```

The REPL first asks which **machining operation** to calculate, and — when
you choose `milling` — which sub-operation:

```text
Machining operation (drilling, milling) (drilling): milling
Milling operation (end milling, face milling) (end milling): face milling
```

Choosing `drilling` leads to exactly the drilling session as before. After
each result you can run another calculation and pick a different operation;
each operation remembers its own previous answers as defaults.

For drilling, the REPL prompts for a calculation mode (`standard`, `power-constrained`,
`fixed-rpm`) right after the unit-system prompt; `power-constrained` then
asks for a required available power, and `fixed-rpm` asks for a required
target spindle speed (with an optional advisory available power). Milling's
REPL sessions (both end milling and face milling) prompt for the same
calculation mode at the same point in the sequence, right after the
unit-system prompt and before material selection.

### Material selection is two-step

Materials are grouped by **material type**, so the REPL asks for the type
first and then only offers the materials belonging to it:

```text
Material type (Metal, Wood): Wood
Material (Oak, Maple, Pine, Spruce, Fir, Plywood, MDF): Oak
```

This keeps the material list short as the catalog grows. On a repeat
calculation the previous type is offered as the default; switching to a
different type discards the remembered material, so you always pick a
material that actually belongs to the chosen type.

### Configurable materials & tools

The built-in materials are grouped into two types:

- `metal` — Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium
- `wood` — Oak, Maple (hardwood), Pine, Spruce, Fir (softwood),
  Plywood, MDF (engineered wood)

Three built-in tools (HSS, Cobalt, Carbide) are bundled with the package and
used automatically with no configuration required.

To add your own materials/tools, or override a built-in tool's factors,
pass an optional user TOML file via `--materials-config`, either through the
`mfgparams` console script or `python -m mfgparams` (both parse the
same CLI flag):

```bash
mfgparams --materials-config my-mfgparams.toml
# or: python -m mfgparams --materials-config my-mfgparams.toml
```

```toml
# my-mfgparams.toml
[[materials]]
name = "Bronze"
material_type = "metal"           # groups it under the "Metal" type prompt
reference_cutting_speed = 45.0    # m/min (or ft/min if unit_system = "imperial")
reference_feed_per_rev = 0.18     # mm/rev (or in/rev if imperial)
specific_cutting_force = 750.0    # N/mm^2 (or psi if imperial)

[[materials]]
name = "PVC"
material_type = "plastic"         # a brand-new type - no code change needed
reference_cutting_speed = 200.0
reference_feed_per_rev = 0.30
specific_cutting_force = 80.0

[[tools]]
name = "Carbide"                  # matches a built-in name -> overrides its factors
cutting_speed_factor = 3.0
feed_factor = 1.1
```

- `material_type` is a free-form identifier, so declaring a value that is not
  yet in use (e.g. `"plastic"` or `"cement"`) registers a new type in the
  material-type prompt without any code change. Types are listed in the order
  they first appear across the bundled then user-supplied materials.
- Types with a known identifier (`metal`, `wood`) get a translated label;
  any other identifier is displayed title-cased (`composite-fibre` →
  `Composite Fibre`).
- `material_type` is optional. A material that omits it is grouped under
  `uncategorized`. Because the key is "sticky" when merging, a user entry that
  overrides a built-in material without restating `material_type` keeps the
  built-in type rather than being decategorized.

- Entries with a new `name` are **added** alongside the built-in defaults;
  entries whose `name` matches a built-in material/tool **override** it.
- `unit_system = "imperial"` (default: `"metric"`) declares that the entry's
  numeric fields are in imperial units; they are converted to metric
  automatically and produce identical results to an equivalent metric entry.
- An optional `[materials.translations]` (or `[tools.translations]`) table
  maps a locale code (e.g. `fr`) to a translated display name, shown when
  `MFGPARAMS_LOCALE` is set accordingly; unset/unsupported locales and
  entries without a translation fall back to the English `name`.
- A missing/unreadable `--materials-config` file is a non-fatal notice — the
  CLI falls back to the bundled defaults. A malformed TOML file or a
  duplicate material/tool `name` within the file is a fatal, translated
  error and the CLI exits without starting the REPL.
- Invalid material numeric fields (missing/non-numeric/non-positive cutting
  speed, feed, or specific cutting force) are logged as warnings at registry
  load time; startup continues and the entry remains listable, but calculations
  with that entry fail safely with a user-facing `UNUSABLE_MATERIAL` error.

See [`specs/005-configurable-materials-tools/quickstart.md`](specs/005-configurable-materials-tools/quickstart.md)
for full runnable scenarios, and
[`specs/005-configurable-materials-tools/contracts/materials-config-schema.md`](specs/005-configurable-materials-tools/contracts/materials-config-schema.md)
for the exact TOML schema.

## Run the tests

```bash
pytest
```

This project targets Python 3.9+ for compatibility with older/stable Linux
distributions (see `.specify/memory/constitution.md` Principle V), and aims
for ≥90% test coverage on calculation modules (Principle II). The command
above runs against whichever Python interpreter is active in your virtual
environment.

### Checking every supported Python version locally

To verify a change against every officially supported Python version
(3.9-3.12) without hand-building a separate environment per version,
use [`tox`](https://tox.wiki/) (installed as part of the `dev` extra):

```bash
tox            # runs the full suite + coverage gate once per supported version
tox -e py39    # or just one version, for a faster inner loop
```

Any supported interpreter not installed on your machine (e.g., no `python3.9`
on `PATH`) is reported `SKIPPED` rather than failing the run — install it
(e.g., via `pyenv install 3.9`) to include it.

See `specs/001-metal-drilling-calc/` for the full spec, plan, and task
breakdown driving this implementation.

### Legacy-hardware performance suite (opt-in)

A separate, opt-in `tests/performance/` suite checks that every public
calculation function stays within the resource budget of
Constitution Principle V's legacy/low-power hardware target (single-core
CPU, ~64-128 MB RAM, 0.5-1.0s per calculation). It is skipped automatically
by the `pytest` command above and does not affect its duration, outcome, or
coverage. Run it explicitly with:

```bash
MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov -v -s
```

See `specs/006-legacy-hardware-performance-tests/quickstart.md` for the full
set of validation scenarios (including graceful degradation on macOS/Windows
and actionable failure reporting).

## Quality & Security Gates (CI)

Every pull request runs the following required checks (`.github/workflows/ci.yml`),
per `.specify/memory/constitution.md` Principle IX:

| Check | Tool | Enforces |
|---|---|---|
| `lint` | `ruff` (incl. `C90`/mccabe) | Style, formatting, cyclomatic complexity (FR-001) |
| `complexity` | `scripts/check_maintainability.py` (`radon mi`) | Maintainability Index (FR-002) |
| `typecheck` | `mypy` | Static type errors (FR-003) |
| `security` | `bandit` | High/medium-severity security findings (FR-004) |
| `dependency-scan` | `pip-audit` | Known CVEs in resolved dependencies (FR-005); also runs weekly, independent of PRs |
| `test` | `pytest --cov` | Test failures / coverage below 90% |
| `build` | `python -m build` | Package build failures |
| `docs` | Sphinx | Docs build failures |
| CodeQL (`Analyze (python)`) | GitHub CodeQL default setup | New high-confidence security alerts (FR-006) |

`main` is protected by two GitHub rulesets (not classic branch protection): a
status-checks ruleset with **no bypass for anyone** (a failing required check blocks
every contributor, including the repository owner), and a separate PR-review ruleset
whose "require a pull request" rule has a bypass scoped only to the repository owner.
See `specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md` for the full
contract.

### Multi-agent skill sync

A separate, non-PR-blocking `sync-agent-integrations` job (same file, weekly cron plus
on-demand `workflow_dispatch`) regenerates every installed coding-agent integration
(currently GitHub Copilot's `.github/agents/`+`.github/prompts/`, Claude Code's
`.claude/skills/`) from Spec Kit's upstream template source, and opens a pull request
only when something actually drifted. This keeps per-agent instructions from being
hand-duplicated or silently going stale, per `.specify/memory/constitution.md`
Principle XI — see `specs/011-multi-agent-skill-sync` for the full design.

### Shared skills across coding agents

Some repo-specific skills under `.github/skills/` (GitHub Copilot's skill
directory) are genuinely useful from Claude Code too — e.g. `pr-review-loop`,
`pypi-package-builder`, `skill-authoring`. Rather than hand-copying them into
`.claude/skills/` (which would duplicate and drift, exactly what
`.specify/memory/constitution.md` Principle XI forbids), each one is
symlinked from `.claude/skills/<name>` to the canonical skill directory
`.github/skills/<name>/` (which holds `SKILL.md` and any supporting
files) — one physical directory, referenced from two places, so it can't
diverge (Principle XI's "genuinely shared, hand-authored skills"
exception, v1.9.0).

`code-review` is deliberately **not** symlinked: it collides with Claude
Code's own bundled `/code-review` skill, and a same-named project skill
takes precedence over a bundled one, so linking it would silently shadow
Claude Code's built-in review capability instead of adding to it.

**Setting this up** (already done once and committed as real symlinks, but
run this after cloning if `.claude/skills/<name>` looks broken or missing —
notably on Windows, where a clone made without symlink support checked out
as plain text files instead of real symlinks):

```bash
python scripts/setup_skill_symlinks.py          # create/fix the symlinks
python scripts/setup_skill_symlinks.py --check  # report status only, exit non-zero if anything's wrong
```

CI runs the `--check` form in the `lint` job, so a committed link that
goes missing, points at the wrong skill, or gets replaced by a hand-copied
duplicate fails the build rather than drifting unnoticed.

On Windows, running the script above requires either Developer Mode
(Settings > Update & Security > For developers) or an elevated
(Administrator) terminal — the script's error message repeats this if it
can't create a symlink. Separately, and only relevant to *future* clones
(not to fixing an existing checkout with the script above): setting
`git config --global core.symlinks true` **before** cloning makes `git
checkout` materialize a real symlink for you in the first place, instead
of the plain-text placeholder file that puts you in this situation.
`core.symlinks` has no effect on the script's own symlink creation —
Developer Mode/elevation alone is what that needs.

### Documented exceptions instead of silent suppressions

If a finding is a genuine false positive or an accepted, understood risk, suppress it
with the tool's own native mechanism **and a rationale comment**, so the exception is
visible in the code/PR diff rather than hidden in CI config:

- **Complexity** (`ruff`/C901): `# noqa: C901  <why this function's complexity is
  necessary/accepted>`
- **Security** (`bandit`): `# nosec B### <why this specific finding is a false positive
  or accepted risk>` — do not use a bare `# nosec` (it silently suppresses everything on
  that line), and avoid putting the literal word "nosec" in unrelated comment text
  elsewhere on the line, since bandit's suppression regex matches that substring
  anywhere in the trailing comment.
- **Type errors** (`mypy`): `# type: ignore[<error-code>]  <why this specific mypy rule
  doesn't apply here>` — never a bare `# type: ignore` (it hides all future errors on
  that line, not just the one you reviewed).
- **Dependency findings** (`pip-audit`): add a documented ignore entry (e.g. `pyproject.toml`
  `[tool.pip-audit]` `ignore-vulns`, with a comment linking the CVE and the acceptance
  rationale) rather than pinning to an insecure version silently.

**Complexity and security exceptions specifically also require the same rationale to be
restated in the pull request description itself** (Constitution Principle IX) — the
in-code comment alone is not sufficient for these two gates, since they are the ones
most likely to hide a real defect if suppressed casually. See
`.github/pull_request_template.md` for the required section, and reviewers: **reject any
PR that suppresses a complexity or security finding without both** the in-code rationale
comment **and** the PR-description restatement.
