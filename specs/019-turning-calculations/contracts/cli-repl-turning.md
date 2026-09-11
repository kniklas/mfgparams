# Contract: Console Text GUI — Machining Tree & Turning Screen

**Feature**: [../spec.md](../spec.md) | **Library contract**: [./library-api-turning.md](./library-api-turning.md)

Extends the current split-pane console text GUI (`018-tui-splitpane-redesign`,
`src/mfgparams/console/tui/`) with a third Machining tree leaf and its own operation
screen, following exactly the pattern `machining_menu.py`/`app.py`/`screens/drilling.py`
already establish for Drilling and Milling. This supersedes the older linear-REPL-style
contracts (`specs/001-metal-drilling-calc/contracts/cli-repl.md`,
`specs/009-milling-calculations/contracts/cli-repl-milling.md`) for describing *how a
process is reached*, since the console is no longer a step-by-step REPL loop — those
contracts' description of individual field prompts and message-catalog sourcing still
holds, just delivered through split-pane rows instead of sequential dialogs.

## Machining tree (extends `machining_menu.py`)

`tree_rows()` gains a third, always-present flat leaf (FR-002), alongside the existing
Milling and Drilling leaves — no new tree nesting/expansion is introduced, matching how
Drilling's leaf itself was flattened in the 018 redesign (`machining_menu.py` module
docstring):

```python
RowAction = Literal["open_milling", "open_drilling", "open_turning"]  # extended

def tree_rows(tree: MachiningTree) -> list[TreeRow]:
    return [
        TreeRow("tui.machining_menu.milling", "open_milling", indent=0),
        TreeRow("tui.machining_menu.drilling", "open_drilling", indent=0),
        TreeRow("tui.machining_menu.turning", "open_turning", indent=0),  # NEW
    ]
```

- `tui.machining_menu.turning` is a new message-catalog key (English entry only, per
  FR-015/Constitution VIII), following the same key-naming convention as the existing two.
- Mnemonic assignment (`tree_mnemonics`) requires no code change — it already recomputes
  unique accelerators over however many rows `tree_rows()` returns.

## App dispatch (extends `app.py`)

A new `_open_turning(ui, materials_config_path, display_locale)` helper, structurally
identical to `_open_drilling`/`_open_milling` (same `OperationScreen` wrapper, same
floating-window presence model via `SessionUI.open_operation`), wired into the tree's
selection handler:

```python
if row.action == "open_milling":
    _open_milling(ui, materials_config_path, display_locale)
elif row.action == "open_drilling":
    _open_drilling(ui, materials_config_path, display_locale)
else:
    _open_turning(ui, materials_config_path, display_locale)  # NEW
```

## Turning operation screen (`screens/turning.py`, new — mirrors `screens/drilling.py`)

`TurningSessionState` (one instance per app session, carried as editable defaults across
revisits, exactly as `DrillingSessionState` — FR-002 parity with the console's own
established convention):

```python
@dataclass
class TurningSessionState:
    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    depth_of_cut: float | None = None   # NEW field this feature introduces
    length_of_cut: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode: CalculationMode = CalculationMode.STANDARD
```

`rows_for()` field order (split-pane `Row` list, rebuilt every render like drilling's):

1. Unit system (`RadioRow`, reused verbatim).
2. Calculation mode (`RadioRow`, reused verbatim — standard/power-constrained/fixed-RPM).
3. Material type, then material (`RadioRow`, reused verbatim two-step flow).
4. Turning tool (`RadioRow`, mirrors the Tool row — sources `list_turning_tools()`
   instead of `list_tools()`; labeled via a **new** `tui.label.turning_tool` catalog key
   ("Turning tool"), since the existing `tui.label.tool` key's text is drilling-specific
   ("Drilling tool") — milling's tool rows follow this same per-operation-key precedent
   with `tui.label.end_mill_tool`/`tui.label.face_mill_tool`).
5. Workpiece diameter (`NumberRow`, required — mirrors the Diameter row; labeled via a
   **new** `tui.label.workpiece_diameter` key ("Workpiece diameter"), since
   `tui.label.diameter`'s text is drilling-specific ("Drill diameter") — same
   per-operation-key precedent milling's `tui.label.mill_diameter` follows).
6. **Depth of cut (`NumberRow`, required — NEW row this feature introduces)**, labeled via
   a new `tui.label.depth_of_cut` catalog key ("Depth of cut"), unit from a new
   `labels["depth_of_cut"]` entry in `forms.UNIT_LABELS` (mm/in).
7. Length of cut (`NumberRow`, required — mirrors the Depth row). **Reuses** the existing
   `tui.label.length_of_cut` catalog key verbatim (already introduced for milling's
   `length_of_cut` field, with the generic wording "Length of cut" that fits turning
   equally well) — no new catalog key needed here.
8. Mode-conditional available-power / target-RPM row(s) — reused verbatim via
   `split_pane.power_and_rpm_rows(...)`, identical to drilling's.

`_convert_on_unit_change` gains the same treatment for `depth_of_cut` and `length_of_cut`
that drilling's already applies to `diameter`/`depth` (Copilot review precedent on PR #94:
a remembered value must convert its physical quantity across a unit-system switch, not be
silently relabeled).

`calculate_result()` calls `calculate_turning(...)` (library-api-turning.md) with the
state's fields, once every required row holds a value — identical trigger condition to
drilling's `calculate_result()`.

## Result display (extends `forms.py` / result-rendering helpers)

The result panel adds a **Cutting force** line (new `cutting_force` field,
data-model.md), following the existing `tui.result.*` per-field key convention
(`tui.result.spindle_speed`, `tui.result.torque`, ...) with a new
`tui.result.cutting_force` catalog key ("Cutting force:      {value} {unit}"), unit from a
new `labels["cutting_force"]` entry in `forms.UNIT_LABELS` (N/lbf) — displayed alongside
the existing Spindle speed / Feed rate / Machining time / Torque / Power lines, in that
existing order, per FR-015.

## Design-review note

Per the `tui-design` skill (design-before-build checklist for console/TUI screens): the
tree leaf and the overall screen field-list mechanism have an exact prototype to copy
(Drilling's leaf and `rows_for`/`NumberRow`/`RadioRow` pattern), so no new palette/layout
contract is needed for those. The one net-new visual element — the Depth of cut row and
its result-panel counterpart — reuses the existing `NumberRow`/result-line style classes
verbatim (no new color or layout invented), so it likewise needs no separate design
sign-off; this is noted here rather than skipped silently, per that skill's intent.

## Identical-results guarantee (FR-016, unchanged contract)

The console's turning screen and the library MUST continue to produce identical
`CalculationResult` values for identical inputs — `calculate_result()` is a thin adapter
over `calculate_turning()`, exactly as drilling's and milling's screens are over their own
`calculate*()` functions.
