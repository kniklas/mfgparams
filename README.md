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

## Install

```bash
pip install mfgparams                # core dependencies only
pip install "mfgparams[console]"     # adds the console's dependencies
pip install "mfgparams[all]"         # adds every optional runtime dependency
```

`[all]` names the other extras rather than restating them, and pip only
understands that form from **21.2** onward — older pips (including the one
Python 3.9 ships) reject it. `python -m pip install --upgrade pip` first if
you are on one.

An extra gates **dependencies, not modules**: every install ships the same
wheel, `mfgparams.console` included. What `[console]` adds is what the
console's text GUI *needs* ([prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/)),
so embedding the library in another application does not drag that
requirement in with it. `pip install mfgparams` alone gives you every
calculation function but not a working `mfgparams` command — the console
needs `[console]` installed to run at all.

If a console dependency is ever unavailable, invoking `mfgparams` prints the
exact command that fixes it and exits non-zero rather than showing a traceback.
A failure inside `mfgparams` itself — a damaged install, a missing *core*
dependency — still raises normally, because `pip install "mfgparams[console]"`
would not fix it.

## Package structure

Modules are grouped **process-first**: a manufacturing process contains its
operations, and an operation may contain sub-operations.

```text
mfgparams                                          public API — import from here
mfgparams.processes.machining.drilling
mfgparams.processes.machining.milling.end_milling
mfgparams.processes.machining.milling.face_milling
mfgparams.console                                  interactive console
```

The calculation modules are re-exported at the top level, so
`from mfgparams import calculate` is the supported way to reach them; the
qualified paths are there to say where a calculation sits in the manufacturing
domain. `mfgparams.console` is *not* part of that surface — the console is
reached through the `mfgparams` command, `python -m mfgparams`, or
`python -m mfgparams.console`. All three behave identically.

A future process (turning, welding, joining, forming) attaches beside
`machining` rather than reorganising it.

## Install (development)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip   # needed on Python 3.9's bundled pip (<21.3),
                                      # which predates PEP 660 editable-install support;
                                      # also below 21.2, which predates the self-referential
                                      # extra that `mfgparams[all]` is built from
pip install -e ".[dev]"
```

> **Note:** `source .venv/bin/activate` only applies to your *current* shell — a new
> terminal session needs to re-run it. If a bare `pytest` reports collection errors like
> `ModuleNotFoundError: No module named 'mfgparams'`, your shell is picking up a different
> `pytest` from `PATH` instead of `.venv/bin/pytest` — re-activate the venv (or run
> `.venv/bin/pytest` directly) and try again.

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

## Use the interactive text GUI

```bash
mfgparams
```

(`python -m mfgparams` and `python -m mfgparams.console` reach the same
interface.) A persistent menu bar stays visible across the top of the
screen, in a distinct shade from the blue desktop directly beneath it (no
divider line between them): **Exit**, **Machining**, **Configuration**,
**About**, **Help** — navigate with the arrow keys and Enter (**Down**
does the same as Enter: it opens the highlighted item, the natural
"descend into" gesture for a horizontal bar), or an item's underlined
keyboard shortcut. Choosing **Machining**, **Configuration**, **About**,
or **Help** opens a floating dropdown, its top edge directly under the bar
and its background matching the bar's own shade, with a Midnight
Commander-style drop shadow — not inline content replacing the desktop.
Machining's dropdown shows **Milling** and **Drilling** as flat leaves;
selecting either opens its operation screen directly, with no further
tree-level expansion. Escape closes whichever dropdown/panel is open and
returns focus to the bar; Up does the same the instant you're at the top
of a navigable list (Machining's tree) or in a single-block panel with
nothing to navigate (Configuration/About/Help) — the dropdown is erased,
not left open-but-unfocused underneath. Selecting **Exit** opens a "Are
you sure you want to exit?" confirmation dropdown (defaulting to **No**)
rather than exiting immediately — Left/Right toggle Yes/No, Enter/Space
confirms the highlighted choice, and **y**/**n** answer directly.

Opening Drilling or Milling shows a centered, bordered floating window,
shaded and colored the same cyan-on-black as every other floating window,
over the menu bar and tree (which stay visible underneath, untouched): the
left pane lists every input for that operation at once — unit system,
calculation mode, material type/material, tool, and the operation's
geometry fields (plus, for Milling, the end-milling/face-milling choice) —
all simultaneously visible and editable, with no separate screen per field.
The right pane shows the live result, refreshing automatically once every
required field has a value. **Up/Down** (or **j/k**) always moves to the
next/previous field, regardless of its type. A radio field (unit system,
mode, material type, material, tool, sub-operation) is always a single
`Label: value` line — **Left/Right**/**h/l**/**Space** cycle its value with
wraparound and commit it immediately, with no separate confirm step. A
numeric field becomes editable the instant you select it (typing a digit or
`.`/`-` edits its buffer immediately, Backspace removes the last character,
Left/Right nudges it by a small step) — but that text is only written to the
field the instant you navigate away from it (Up/Down); text that still
doesn't parse as a number at that point is discarded (the field keeps its
last valid value) and a message appears in the status bar beneath both
panes, replacing the usual keyboard hint until you correct it.

Escape closes the operation window outright (a single press, not two) and
returns focus to the still-open Machining tree if it was expanded — not
the bare menu bar — so you land back exactly where you opened the
operation from; a second Escape from there closes the tree itself and
reaches the bar. Either way, you can start another calculation — the same
operation or a different one — without leaving the text GUI. Each
operation remembers its own previous answers as defaults for the rest of
the session.

The whole application follows one consistent, Turbo-Vision-style color
scheme — a cyan bar, a distinct blue desktop behind it, and the bar's own
cyan-on-black for every floating window (the Machining/Configuration/
About/Help dropdowns, the Exit confirmation dialog, and the Drilling/
Milling operation window alike), each with a Midnight Commander-style
black drop shadow — rather than the terminal's own default background.

For drilling, the calculation-mode field (`standard`, `power-constrained`,
`fixed-rpm`) sits right after unit system in the left pane;
`power-constrained` then makes available power a required field, and
`fixed-rpm` adds a required target spindle speed (with an optional advisory
available power). Milling (both end milling and face milling) presents the
same calculation-mode field in the same position.

### Material selection is two-step

Materials are grouped by **material type**, so the text GUI asks for the
type first and then only offers the materials belonging to it: choosing
`Wood` then offers only `Oak, Maple, Pine, Spruce, Fir, Plywood, MDF`.

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
  error and the CLI exits without starting the text GUI.
- Invalid material numeric fields (missing/non-numeric/non-positive cutting
  speed, feed, or specific cutting force) are logged as warnings at registry
  load time; startup continues and the entry remains listable, but calculations
  with that entry fail safely with a user-facing `UNUSABLE_MATERIAL` error.

See [`specs/005-configurable-materials-tools/quickstart.md`](specs/005-configurable-materials-tools/quickstart.md)
for full runnable scenarios, and
[`specs/005-configurable-materials-tools/contracts/materials-config-schema.md`](specs/005-configurable-materials-tools/contracts/materials-config-schema.md)
for the exact TOML schema.

### Adding or changing a user-facing string

Every user-facing string lives in a message catalog, never inlined at its call site (Constitution
Principle VIII). Which catalog depends on what the string is:

- A prompt, label, or status/progress message the interactive console displays — add or edit it in
  `mfgparams/console/locales/en.py`.
- Error, warning, or startup-notice text returned by the library API (`ErrorInfo.message`,
  `CalculationResult.feasibility_warning`, a materials-config load notice/error) — add or edit it in
  `mfgparams/locales/en.py`. This text must stay readable without the `console` extra installed.
- The material/tool *display name* a user supplies via `[materials.translations]`/
  `[tools.translations]` in their own config file is not a catalog entry at all — see the materials
  configuration section above.

See [`specs/015-console-i18n-relocation/contracts/catalogue-ownership-contract.md`](specs/015-console-i18n-relocation/contracts/catalogue-ownership-contract.md)
for the full rule, including two narrow, explicitly documented exceptions.

### `console/tui/` architecture

The text GUI (`mfgparams/console/tui/`) is one persistent
[prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) `Application`
for the whole session, constructed once by `app.py`'s `build_app()` — not a
chain of short-lived, per-screen `Application`s the way the 017-era dialog
chain worked (prompt-toolkit does not support a second, nested
`Application.run()` call, which is exactly why that model changed). Three
kinds of state stay deliberately separate:

- **`SessionUI`** (`app.py`) — the session-lifetime, business-relevant state:
  the menu bar's fixed entries, the Machining tree's expand/collapse flag
  (`MachiningTree` — Milling and Drilling are flat leaves, so this is a
  single `bool`), which operation screen (if any) is open
  (`OperationScreen`), and each operation's own remembered inputs
  (`DrillingSessionState`/`MillingSessionState`, one instance per operation —
  two for Milling, one per sub-operation — so revisiting a screen offers the
  previous answers as defaults). `tree` and `open_operation` are independent
  fields with no code path writing both from the same handler: collapsing the
  tree never closes an open operation, and vice versa — trivially so, since
  the operation screen renders as a floating window (a
  `prompt_toolkit.layout.FloatContainer`/`Float` layered above the
  bar+tree, not embedded inside their own container) that isn't part of the
  tree's container at all.
- **`_ViewState`** (`app.py`, module-private) — pure UI-presentation state
  that does *not* survive a body change on purpose: which *background* body
  is currently shown (`body_mode` — the tree, About, Help, or Configuration;
  an open operation is not one of its values, since the floating window is
  independent of it) and which row is highlighted within it. Kept separate
  from `SessionUI` so, for example, selecting Configuration from the bar
  never touches the Machining tree's own state.
- **`OperationScreen.field_buffer`** — the raw, not-yet-committed text of
  whichever numeric field is currently selected in a split-pane screen (see
  below); empty for a radio field, which has no buffered state of its own
  since Left/Right/Space commit it immediately. Committed only when the
  user navigates away from the field (Up/Down) — distinct from that field's
  last-committed value until then. `OperationScreen.status` is a sibling
  field: `None` normally, or a transient message (e.g. "'abc' is not a
  number") shown in the bottom status bar in place of the usual keyboard
  hint, set only when navigating away from a field whose buffer didn't
  parse.

Four widgets render as pure functions of this state — `menu.render_menu_bar`,
`machining_menu.render_tree`, `screens.about.render_about`,
`screens.help.render_help` — rather than each owning its own dialog/`Layout`.
The Drilling/Milling screens (`screens/drilling.py`, `screens/milling.py`)
are built the same way but share one more layer,
`screens/split_pane.py`: each screen's `rows_for()` returns a list of
`RadioRow`/`NumberRow` describing that operation's current fields (a later
row's presence or options can depend on an earlier row's committed value —
e.g. the specific-material row only appears once a material type is chosen
— so the list is rebuilt every render, not cached), and `split_pane.py`
owns the shared navigation/edit/nudge/commit logic and the right pane's
two-state result machine (a placeholder while any required field is still
unset; a result, or an error `calculate()` itself rejects for a
complete-but-invalid combination, once every required field has a value).
Text that never parses as a number is not a right-pane state at all — it
never reaches `session_state`, so it can't reach `calculate()` either;
instead it surfaces via the bottom status bar (`render_bottom_bar`), only
once the user tries to navigate away from the offending field, not while
still typing. Deliberately, this module does *not* re-validate field ranges
itself — `calculate()`/`calculate_end_milling()`/`calculate_face_milling()`
already re-validate every field internally regardless of caller.

Testing drives the real `Application` headlessly:
`prompt_toolkit.output.DummyOutput` renders nowhere, and
`prompt_toolkit.input.create_pipe_input` feeds a scripted key sequence from a
background thread (with explicit `contextvars` propagation — a plain
`threading.Thread` does not inherit prompt-toolkit's ambient input/output
context). `tests/integration/_tui_test_support.py`'s `run_headless()`
supports an `on_batch` hook that runs between each batch of keys, so a test
can inspect `SessionUI`/`OperationScreen` state mid-session (e.g. confirming
the right pane shows a placeholder before every field is complete), not just
after the whole script finishes.

## Run the tests

```bash
pytest
```

This project targets Python 3.9+ for compatibility with older/stable Linux
distributions (see `.specify/memory/constitution.md` Principle V), and aims
for ≥90% test coverage on calculation modules (Principle II). The command
above runs against whichever Python interpreter is active in your virtual
environment.

See `specs/001-metal-drilling-calc/` for the full spec, plan, and task
breakdown driving this implementation.

### Checking every supported Python version locally

To verify a change against every officially supported Python version
(3.9-3.12) without hand-building a separate environment per version,
use [`tox`](https://tox.wiki/) (installed as part of the `dev` extra; each
environment it builds installs the narrower `test` extra):

```bash
tox            # the suite + coverage gate once per supported version
tox -p auto    # the same, in parallel
tox -e py39    # or just one version, for a faster inner loop

# Narrowing down one failure: pass `--no-cov` with any filter, or the 90%
# coverage gate fails the environment even when every selected test passed.
tox -e py39 -- --no-cov -k drilling -x

# The wheel-contents assertions, which the envs above deselect. They verify
# packaging rather than Python-version compatibility, so they run once.
tox -e packaging
```

The version envs deselect the `packaging` marker
(`tests/integration/test_packaging_bundled_data.py`). Those tests shell out to
`python -m build`, and setuptools writes its scratch tree to `<repo>/build/`
regardless of `--outdir` — one directory shared by every env. Running them in
all four was what made `tox -p` unsafe (issue #74); with no env in `envlist`
building, parallel mode works. CI runs them once in its `build` job, which is
equally merge-blocking, so nothing stops gating on them.

Any supported interpreter not installed on your machine (e.g., no `python3.9`
on `PATH`) is reported `SKIPPED` rather than failing the run — install it
(e.g., via `pyenv install 3.9`) to include it.

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

Every pull request is measured against the following checks, per
`.specify/memory/constitution.md` Principle IX. All of them gate a merge, but only
three are named in `main`'s ruleset — see the note below the table. Most of them also
run conditionally: a check with nothing in its scope to evaluate (e.g. `typecheck` on a
pull request that touches no Python source) reports **Skipped**, not run — see the
path-based selection note below the table.

| Check | Tool | Enforces |
|---|---|---|
| `changes` | `dorny/paths-filter` | Classifies the diff into path categories that decide which of the jobs below actually run |
| `lint` | `ruff` (incl. `C90`/mccabe) | Style, formatting, cyclomatic complexity (FR-001); also runs whenever `.github/skills/**`/`.claude/**` changes (skill-symlink integrity) |
| `complexity` | `scripts/check_maintainability.py` (`radon mi`) | Maintainability Index (FR-002) |
| `typecheck` | `mypy` | Static type errors (FR-003) |
| `security` | `bandit` | High/medium-severity security findings (FR-004) |
| `dependency-scan` | `pip-audit` | Known CVEs in resolved dependencies (FR-005); also runs weekly, independent of PRs, and is never path-selected |
| `test (3.9)`, `test (3.10)`, `test (3.11)`, `test (3.12)` | `pytest -m "not packaging" --cov` | Test failures / coverage below 90%, checked separately on every officially supported Python version |
| `build` | `python -m build`, then `pytest -m packaging` | Package build failures, and the wheel-contents assertions — the only place in CI they run; also runs whenever `README.md`/`LICENSE.md` changes (packaging metadata) |
| `docs` | Sphinx | Docs build failures |
| `repo-invariants` | `pytest` (two repo-wide static tests) | No stray reference to this package's old name/layout anywhere in the tree — reruns unconditionally, since `test`'s own path-based skip can't safely cover a check that scans every file regardless of category |
| CodeQL (`Analyze (python)`) | GitHub CodeQL default setup | New high-confidence security alerts (FR-006) |
| `ci-ok` | aggregate | Passes when every one of the ten jobs above (excluding CodeQL) either succeeded or was intentionally skipped by path selection; fails on any real failure or cancellation |

`main`'s ruleset requires exactly three checks — **`ci-ok`, `Analyze (python)`
and `CodeQL`** — not the individual jobs. Every job in the table still runs and
reports under its own name; they are simply no longer read by branch
protection, so renaming a job or adding a Python version no longer requires a
ruleset change (issue #75 P2.4). `Analyze (python)` and `CodeQL` stay separate
because they come from GitHub's managed CodeQL setup rather than `ci.yml`.

**Path-based selection** (`specs/016-ci-path-based-selection`): `lint`, `complexity`,
`typecheck`, `security`, `test`, `build`, and `docs` skip themselves when a pull request's
changed paths fall outside what each depends on (e.g. a specs-only or docs-only PR shows
most of them as Skipped) — a `Skipped` job does not block `ci-ok`, only a real `failure`/
`cancelled` does. `changes` and `repo-invariants` are never skipped for path reasons.
`performance`, `quality-summary`, `deploy-docs` and `sync-agent-integrations` are
supporting jobs, deliberately outside `ci-ok`; pulling one in would make it a merge
blocker, which `tests/static/test_ci_ok_aggregate_check.py` fails on.

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
