# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A new `turning` machining process (`mfgparams.calculate_turning`,
  `mfgparams.list_turning_tools`), a sibling to the existing drilling and
  milling processes, covering standard cylindrical (straight/outside-
  diameter) turning across all three calculation modes (standard, fixed-
  RPM, power-constrained): spindle speed, feed rate, machining time,
  cutting force, torque, and power, reusing the existing workpiece-material
  registry and configurable-tool pattern (specs/019-turning-calculations).
  Exposed in the console text GUI as a third Machining tree leaf alongside
  Milling and Drilling. `CalculationResult` gains a new optional
  `cutting_force` field (populated for turning; `None` for drilling and
  milling), following the same precedent `material_removal_rate` already
  set for milling.
- Every turning calculation result now also reports `feed_per_rotation` —
  the feed rate expressed as material advance per workpiece rotation
  (mm/rev under metric, in/rev under imperial), the way feed rate is
  actually set on a lathe — alongside the existing, unchanged per-minute
  `feed_rate` (specs/020-turning-feed-per-rotation). `CalculationResult`
  gains this new optional field (populated for turning; `None` for
  drilling and milling), following the same precedent `cutting_force`
  already set. A new **feed-rate-constrained** turning calculation mode
  (`CalculationMode.FEED_RATE_CONSTRAINED`) lets a caller supply a target
  feed rate per rotation directly instead of deriving it from the
  material/tool — spindle speed is still derived exactly as standard mode,
  while machining time, cutting force, torque, and power are recomputed
  from the supplied feed rate. In the console text GUI, this mode's new
  "Feed rate per rotation" field nudges by a finer step (0.1 mm/rev metric,
  0.005 in/rev imperial) than every other numeric field's default.

### Changed

- The console text GUI's navigation model is replaced: a persistent
  horizontal menu bar (Exit, Machining, Configuration, About, Help) with a
  collapsible Machining tree (Milling, Drilling, both flat leaves) stays
  visible underneath a floating operation window — a centered, bordered
  left/right split pane (every input simultaneously visible/editable in the
  left pane, a live, auto-refreshing result in the right pane) opened over
  the bar/tree rather than replacing them — replacing 017's sequential
  dialog chain (specs/018-tui-splitpane-redesign). Up/Down always moves to
  the next/previous left-pane field regardless of type; radio fields (unit
  system, mode, material type, material, tool) are always a single
  `Label: value` line, cycled with Left/Right/Space and committed
  immediately, with no separate confirm step. Numeric fields are
  instant-edit (typing immediately edits the field's buffer, no separate
  "start editing" step) and support a Left/Right nudge in addition to
  typing a value outright, but that buffer is only written to the field
  once the user navigates away from it; text that still doesn't parse as a
  number at that point is discarded (the field keeps its last valid value)
  and surfaces as a message in a status bar beneath both panes, rather than
  in the right pane. The Configuration screen now covers all three tool
  registries (drilling, end-mill, face-mill), not just drilling's.
- Selecting Machining, Configuration, About, or Help from the menu bar now
  opens a floating dropdown/panel positioned directly under that bar
  entry, rather than replacing a shared inline body area below the bar —
  matching a typical menu-bar TUI's dropdown behavior. Escape or Up (the
  instant you're at the top of a navigable dropdown, or anywhere in a
  single-block panel with nothing to navigate) closes/erases the open
  dropdown outright, rather than leaving it open-but-unfocused underneath.
  Escaping the Drilling/Milling operation window closes it and returns
  focus to the still-open Machining tree (not the bare bar) if it was
  expanded, landing exactly where the operation was opened from; a second
  Escape from there then closes the tree itself and reaches the bar. Down
  (and j) on the bar now also activates the highlighted item, the same as
  Enter.
- The whole application now follows one consistent, Turbo-Vision-style
  color scheme — a cyan bar, a distinct blue desktop behind it, and the
  bar's own cyan-on-black for every floating window (the four dropdowns,
  the Exit confirmation dialog below, and the Drilling/Milling operation
  window alike), each with a Midnight Commander-style black drop shadow —
  replacing the terminal's own default background and the prior
  revision's reliance on prompt-toolkit's own black-on-white dialog
  default. Every dropdown's top edge sits directly beneath the bar (the
  divider line that used to sit between the bar and the desktop is
  removed).
- Selecting Exit from the menu bar now opens a floating "Are you sure you
  want to exit?" Yes/No confirmation dropdown (defaulting to No) instead
  of exiting immediately.
- Fixed a stray highlighted first character on the menu bar and every
  dropdown, caused by a focusable control's default terminal-cursor
  placement (the same class of artifact already fixed for the operation
  window's own left pane).
- Fixed a reported bug where the Machining dropdown sometimes needed two
  Down/Enter presses on the bar to expand: closing it (Escape, or Up at
  the top row) left its underlying "expanded" flag `True` even though the
  dropdown was no longer shown, so the very next press silently toggled
  it back to `False` (no visible change) instead of reopening it.
- The minimum supported terminal size is raised from 25×80 to **30×80** —
  the persistent menu bar and tree, shown alongside an operation screen's two
  panes, no longer reliably fit the previous floor.

## [2.0.0] - 2026-09-08

### Removed

- **Breaking**: the interactive line-based REPL is removed entirely, replaced
  by a full-screen, keyboard-navigable text GUI (`mfgparams`, `python -m
  mfgparams`, and `python -m mfgparams.console` all now launch it) — a menu
  (Machining → Milling, Drilling; Configuration; About; Help), each item
  reachable by arrow-key navigation or a direct keyboard shortcut
  (specs/017-console-text-gui). This un-parks the "text-base UI" item issue
  #63 originally deferred ("keep REPL; park text-base UI for later") —
  reversed deliberately during that feature's review, not silently: the REPL
  is deleted, not kept alongside the new interface or hidden behind a flag.
  Built on [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/),
  selected after a technical spike compared it against Textual and urwid on
  dependency footprint, memory, and cold-start time (specs/017-console-text
  -gui/spike-tui-framework.md); this is also the first release of the
  `console` extra's dependencies, which shipped empty since 014 specifically
  because nothing needed it until now.

  **There is no scripting/automation entry point into `mfgparams.console`
  any more.** A terminal that cannot support the text GUI (no TTY, or
  smaller than the 25×80 target) gets a clear, localized, actionable message
  and a clean exit — never a REPL fallback, since none exists.

### Changed

- **Breaking**: calculation modules are grouped **process-first**. A
  manufacturing process now contains its operations, replacing the
  operation-first grouping (issue #63, part 1 of 4):

  | Before | After |
  |---|---|
  | `mfgparams.operations.drilling` | `mfgparams.processes.machining.drilling` |
  | `mfgparams.operations.milling.end_milling` | `mfgparams.processes.machining.milling.end_milling` |
  | `mfgparams.operations.milling.face_milling` | `mfgparams.processes.machining.milling.face_milling` |
  | `mfgparams.cli` | `mfgparams.console.cli` |

  Milling keeps its sub-operation level, so end milling and face milling stay
  *within* milling rather than becoming siblings of drilling. The old paths are
  gone with **no alias, shim, or deprecation period** — nothing has been
  published to PyPI, so there is no consumer for a compatibility layer, and the
  import path now tells you where a calculation sits in the manufacturing
  domain. A future process (turning, welding, joining, forming) attaches beside
  `machining` rather than reorganising it.

  **Code importing only the documented public surface is unaffected**: every
  name in `mfgparams.__all__` is unchanged, so `from mfgparams import calculate`
  and its 13 siblings keep working exactly as before. No calculation input,
  output, formula, or bundled reference-data value changed.

- The interactive console moved into its own `mfgparams.console` sub-package,
  separate from the calculation core. The core never imports it, enforced by an
  ast scan plus a clean-interpreter `sys.modules` check rather than by
  convention.

- `python -m mfgparams.console` now works as a third way to start the console,
  alongside the `mfgparams` command and `python -m mfgparams`. All three route
  through the same entry point, so a missing console dependency gets the same
  actionable message from any of them instead of a traceback from one.

- **Breaking**: UI-facing message catalogues (prompts, labels, status text)
  moved into `mfgparams.console`, the single place to find and change what the
  console displays (issue #63, part 2 of 4). Error text stays a core
  responsibility — `CalculationResult.error.message` is now **always
  English**, regardless of `MFGPARAMS_LOCALE` or an explicit `locale=`
  argument, so the library API stays fully usable without the `console` extra
  installed. `ErrorInfo` gains two fields, `message_key` and `kwargs`, so a
  caller with its own rendering (the console) can reproduce the exact message
  template in another locale — `error.code` alone cannot, since one code can
  cover more than one message template (e.g. `INVALID_DIAMETER` covers both a
  zero-value case and an exceeds-maximum case). The `locale=` parameter on
  `calculate()`/`calculate_end_milling()`/`calculate_face_milling()` is
  retained for signature compatibility but no longer affects the returned
  message text.

### Added

- Installation extras. `pip install mfgparams` now installs only what the
  calculations require; `pip install "mfgparams[console]"` adds the console's
  dependencies, and `pip install "mfgparams[all]"` takes every optional runtime
  capability the project ships. The `console` extra is empty on delivery — the
  console needs nothing beyond the standard library today — and is declared now
  because adding an extra later is a packaging change users must react to,
  whereas populating a declared one is invisible to them. Self-referential
  extras need pip >= 21.2.
- Invoking the console when its dependencies are unavailable prints one
  actionable message naming the exact install command — quoted, and qualified
  with the running interpreter, so it can be pasted straight into any shell —
  and exits
  non-zero, instead of a traceback. A failure rooted inside `mfgparams` itself
  still surfaces as itself: a broken install is not a missing extra.

## [1.0.0]

### Changed

- **Breaking**: the package is renamed from `machine-calc`/`machine_calc` to
  `mfgparams` (issue #62) — a shorter, more generic name that better reflects
  the library's multi-material (metal and wood) manufacturing-calculation
  scope, rather than one that reads as metal-machine-specific. This is a
  straight rename with no backward-compatibility alias: `pip install
  mfgparams` replaces `pip install machine-calc`, `import mfgparams` replaces
  `import machine_calc`, and the `mfgparams` console script (and `python -m
  mfgparams`) replaces `machine-calc`/`python -m machine_calc`. The
  `MACHINE_CALC_LOCALE`, `MACHINE_CALC_RUN_PERFORMANCE_TESTS`, and
  `MACHINE_CALC_PERFORMANCE_SUMMARY_PATH` environment variables are renamed
  to `MFGPARAMS_LOCALE`, `MFGPARAMS_RUN_PERFORMANCE_TESTS`, and
  `MFGPARAMS_PERFORMANCE_SUMMARY_PATH` accordingly. No calculation logic, CLI
  behavior, or public API signature changed — only identifiers and text tied
  to the package's name. Previously published `machine-calc` releases on
  PyPI are unaffected; only this and future releases use the new name. The
  GitHub repository itself keeps its current name for now (see
  specs/012-rename-package-mfgparams/spec.md's Clarifications).
- Per Constitution Principle IV, this breaking change bumps the version's
  MAJOR component: `0.4.0` → `1.0.0`.

### Fixed

- `validate_diameter_mm()`/`validate_depth_mm()` no longer let a `NaN`
  drill diameter or hole depth pass validation (issue #56). Both checks
  (`value <= 0` and `value > maximum`) are `False` for `NaN`, so a `NaN`
  silently reached the calculation and produced a `NaN`-poisoned
  `CalculationResult` with `error=None` instead of a structured
  `INVALID_DIAMETER`/`INVALID_DEPTH` error. In the interactive CLI, the
  literal `nan` — which `_prompt_number()` parses successfully via
  `float("nan")` — was accepted at the "Drill diameter"/"Hole depth"
  prompt rather than being re-prompted.
- Both validators now route through the module's existing
  `_is_positive_finite_number()` guard, the same one every milling
  validator already used — and the same validation posture
  `validate_target_rpm()` applies via its own equivalent inline
  type/finiteness checks — so a non-numeric value returns an `ErrorInfo`
  instead of raising `TypeError` from the bound comparison, per the
  never-raises contract (FR-015). As a
  consequence, `+inf`/`-inf` (already rejected before, via two different
  checks) now report the "must be greater than 0" message rather than
  "must not exceed <max> mm", matching milling's wording for the same
  input, and a `bool` is no longer accepted as a 1 mm diameter.
- `_is_positive_finite_number()` no longer raises `OverflowError` for an
  enormous `int` such as `10**1000`. `math.isfinite()` coerces its
  argument to a C double, so it raised instead of answering; `int` is now
  short-circuited as inherently finite and the value is rejected by the
  caller's exact bound comparison. `units.to_metric_length()` catches the
  same overflow from the inch-to-mm multiplication. This also fixes the
  **bounded** milling validators (`validate_mill_diameter_mm()`,
  `validate_depth_of_cut_mm()`, `validate_length_of_cut_mm()`), which
  shared the helper and raised `OverflowError` for such an input before
  this release. The *unbounded* milling validators
  (`validate_tooth_count()`, `validate_feed_per_tooth_mm()`) still raise
  for an enormous `int` — unchanged from previous releases, since they
  have no maximum to reject it against and the value reaches float
  arithmetic downstream. Tracked separately in issue #60.
- Drilling's imperial path no longer raises `TypeError` for a non-numeric
  `diameter`/`depth`. `calculate(..., unit_system=UnitSystem.IMPERIAL)`
  converted lengths with a bare `in_to_mm()` *before* validation, so
  `diameter="abc"` raised from the inch-to-mm multiplication rather than
  returning `INVALID_DIAMETER`. Both operations now share
  `units.to_metric_length()`, which passes non-numeric and `bool` values
  through unconverted so the validators reject them — the guard milling
  already applied privately as `_to_metric()`.

## [0.4.0]

### Added

- **Milling calculation modes** (specs/010-milling-calculation-modes):
  `calculate_end_milling()` and `calculate_face_milling()` now accept the
  same `mode`/`target_rpm` parameters as drilling's `calculate()`,
  supporting **power-constrained** (reduce spindle speed/feed rate to fit
  a supplied available power budget) and **fixed-RPM** (derive feed rate,
  machining time, torque, material removal rate, and required power from
  a user-specified spindle RPM) calculation modes, in addition to the
  existing standard mode.
- The interactive CLI's milling flow now asks for a calculation mode
  (`standard`, `power-constrained`, `fixed-rpm`) immediately after the
  unit-system prompt, mirroring drilling's existing mode-selection
  prompt position; the chosen mode determines whether the available-power
  prompt is optional/advisory or required, and whether a target-RPM
  prompt is shown.
- Both new modes reuse drilling's existing `CalculationMode` enum,
  validators, and error codes (`INFEASIBLE_POWER_BUDGET`,
  `INVALID_TARGET_RPM`, `MODE_CONFLICT`) verbatim. Two new error codes are
  introduced for milling-specific edge cases: `INVALID_AVAILABLE_POWER`
  (a non-numeric, non-finite, or non-positive `available_power` supplied
  as the optional advisory value in **standard** or **fixed-RPM** mode)
  and `CALCULATION_OVERFLOW` (an otherwise-valid extreme input that
  overflows an intermediate calculation). An invalid `available_power` in
  **power-constrained** mode, where it is a required hard budget rather
  than advisory, is reported as `INFEASIBLE_POWER_BUDGET` instead, since
  no spindle speed could ever meet it.

### Unchanged

- Standard (unconstrained) milling calculations that omit `mode`/
  `target_rpm` behave identically to `009-milling-calculations` (no
  regression).

## [0.3.0]

### Added

- **Milling calculations** (specs/009-milling-calculations): new public
  entry points `calculate_end_milling()` and `calculate_face_milling()`,
  with their own bundled tool catalogs exposed via `list_end_mill_tools()`
  and `list_face_mill_tools()`. Both report spindle speed, feed rate,
  machining time, torque, required power and **material removal rate**,
  in metric or imperial units.
- New `MachiningOperation` and `MillingSubOperation` enums, and
  `CalculationResult.material_removal_rate` (cm3/min metric, in3/min
  imperial). Drilling results always leave this field `None`.
- The interactive CLI now asks which machining operation to calculate
  before anything else, and which milling sub-operation when `milling` is
  chosen. Each operation keeps its own remembered defaults across repeat
  calculations.
- New milling configuration bounds — `max_mill_diameter_mm` (200.0),
  `max_depth_of_cut_mm` (50.0, applied to both axial depth and radial/width
  engagement) and `max_length_of_cut_mm` (1000.0) — plus the matching
  validation errors and message-catalog entries.

### Changed

- The package version now has a single source of truth (Constitution IV):
  `pyproject.toml` declares `dynamic = ["version"]` and reads
  `machine_calc.__version__`, replacing the previously duplicated (and
  divergent) declarations.
- Milling reports "milling tool" wording in its missing/unknown-tool errors
  (`error.missing_mill_tool`, `error.unknown_mill_tool`) rather than reusing
  drilling's wording.

### Unchanged

- Drilling behaviour is byte-for-byte identical apart from the new leading
  operation prompt, enforced by a golden-transcript contract test captured
  from the pre-refactor CLI.

## [0.2.0] - 2026-08-11

### Added

- Built-in wood workpiece materials (specs/007-wood-materials-support):
  hardwoods **Oak, Maple**; softwoods **Pine, Spruce, Fir**; engineered
  woods **Plywood, MDF** (one generic entry per type). Reference values are
  derived as the median of multiple authoritative sources (Machinery's
  Handbook, CNC machining guides, ISO/industry standards); see
  `specs/007-wood-materials-support/research.md` §7 for citations.
- `WorkpieceMaterial.is_usable` property and
  `machine_calc.registry.get_material_validation()` to inspect load-time
  validation status of a registered material before using its numeric
  fields.
- New translated error code `UNUSABLE_MATERIAL` returned by `calculate()`
  when a selected material was registered with invalid parameters.

### Changed

- **Behavior change (FR-008, warn-and-continue):** invalid material entries
  in a user-supplied `--materials-config` file (missing, non-numeric,
  non-finite, or non-positive cutting speed / feed / specific cutting
  force) no longer abort CLI startup with a fatal `RegistryConfigError`.
  The entry is registered, a warning is logged identifying the source file
  and issue, and startup/listing continues; calculations that select such
  an entry fail safely with the `UNUSABLE_MATERIAL` error instead of
  computing a wrong number. Malformed TOML and duplicate names within one
  file remain fatal errors.
- Registry snapshots for user-supplied config paths are now cached per
  path for the lifetime of the process (previously re-read on each
  lookup); edit-and-reload of a config file requires restarting the CLI.

## [0.1.0]

- Initial release: metric/imperial drilling calculations, constrained
  calculation modes, configurable materials/tools via TOML, i18n message
  catalog, CI quality/security gates.
