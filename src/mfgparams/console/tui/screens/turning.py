"""The Turning operation screen (specs/019-turning-calculations).

Mirrors `screens/drilling.py` exactly (turning is a single-subtype process,
structurally identical to drilling), extended with the third dimensional
input (`depth_of_cut`) drilling doesn't have. `TurningSessionState` follows
the same one-instance-per-session pattern as `DrillingSessionState`: it
lives on `SessionUI.turning_state` for the whole app session, so revisiting
this screen after a calculation offers the previous answers as defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from mfgparams import (
    CalculationMode,
    UnitSystem,
    calculate_turning,
    list_material_types,
    list_materials,
    list_turning_tools,
)
from mfgparams.console.i18n import translate
from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.models import CalculationResult
from mfgparams.processes.machining.turning.tools import get_turning_tool
from mfgparams.registry import get_material

_MODE_OPTION_KEYS = {
    CalculationMode.STANDARD: "tui.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "tui.mode.power_constrained",
    CalculationMode.FIXED_RPM: "tui.mode.fixed_rpm",
}


@dataclass
class TurningSessionState:
    """Editable defaults carried across visits to this screen within one
    app session. Mirrors `DrillingSessionState`, with `depth_of_cut` and
    `length_of_cut` in place of drilling's single `depth`."""

    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    depth_of_cut: float | None = None
    length_of_cut: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode: CalculationMode = CalculationMode.STANDARD


def _convert_on_unit_change(state: TurningSessionState, unit_system: UnitSystem) -> None:
    """Keep remembered diameter/depth-of-cut/length-of-cut/power meaning
    their original physical quantity across a unit-system switch, rather
    than re-offering the same raw number relabeled under the new unit
    (Copilot review on PR #94: a remembered 10 mm silently became a
    defaulted "10 in"). Must run before `state.unit_system` is overwritten
    -- it is the "from" system here."""

    if unit_system is state.unit_system:
        return
    if state.diameter is not None:
        state.diameter = forms.convert_length(state.diameter, state.unit_system, unit_system)
    if state.depth_of_cut is not None:
        state.depth_of_cut = forms.convert_length(
            state.depth_of_cut, state.unit_system, unit_system
        )
    if state.length_of_cut is not None:
        state.length_of_cut = forms.convert_length(
            state.length_of_cut, state.unit_system, unit_system
        )
    if state.available_power is not None:
        state.available_power = forms.convert_power(
            state.available_power, state.unit_system, unit_system
        )


def _number_row(
    field_id: FieldId, label: str, unit: str, value: float | None, required: bool, setter
) -> split_pane.NumberRow:
    """`on_commit` is called only when the user navigates away from this
    field (`split_pane.move_selection`), with the already-parsed value --
    matching drilling's `_number_row` exactly."""

    return split_pane.NumberRow(
        field_id=field_id,
        label=label,
        unit=unit,
        value=value,
        required=required,
        on_commit=setter,
    )


def rows_for(
    screen: OperationScreen, materials_config_path: str | None, locale: str, display_locale: str
) -> list[split_pane.Row]:
    """This screen's `split_pane.Row` list, in FR-005's field order
    (contracts/cli-repl-turning.md)."""

    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    labels = forms.UNIT_LABELS[state.unit_system]
    rows: list[split_pane.Row] = []

    def _set_unit_system(value: str) -> None:
        new_unit_system = UnitSystem.METRIC if value == "metric" else UnitSystem.IMPERIAL
        _convert_on_unit_change(state, new_unit_system)
        state.unit_system = new_unit_system

    rows.append(
        split_pane.RadioRow(
            field_id=FieldId.UNIT_SYSTEM,
            label=translate(locale, "tui.label.unit_system"),
            options=[
                ("metric", translate(locale, "tui.unit_system.metric")),
                ("imperial", translate(locale, "tui.unit_system.imperial")),
            ],
            value="metric" if state.unit_system is UnitSystem.METRIC else "imperial",
            on_select=_set_unit_system,
        )
    )

    def _set_mode(value: str) -> None:
        new_mode = CalculationMode(value)
        if new_mode is not state.previous_mode:
            # A mode's power/RPM field(s) shouldn't default to a value
            # carried over from a *different* mode (mirrors drilling's
            # identically-motivated `_set_mode` guard).
            state.available_power = None
            state.target_rpm = None
        state.mode = new_mode
        state.previous_mode = new_mode

    rows.append(
        split_pane.RadioRow(
            field_id=FieldId.MODE,
            label=translate(locale, "tui.label.mode"),
            options=[
                (mode.value, translate(locale, key)) for mode, key in _MODE_OPTION_KEYS.items()
            ],
            value=state.mode.value,
            on_select=_set_mode,
        )
    )

    material_types = list_material_types(config_path=materials_config_path)

    def _set_material_type(value: str) -> None:
        if value != state.material_type:
            state.material = None
        state.material_type = value

    material_type_labels = {mt: forms.material_type_label(mt, locale) for mt in material_types}
    rows.append(
        split_pane.RadioRow(
            field_id=FieldId.MATERIAL_TYPE,
            label=translate(locale, "tui.label.material_type"),
            options=list(forms.unique_labels(material_type_labels).items()),
            value=state.material_type,
            on_select=_set_material_type,
        )
    )

    if state.material_type is not None:
        material_names = list_materials(
            config_path=materials_config_path, material_type=state.material_type
        )
        materials = {name: get_material(name, materials_config_path) for name in material_names}
        display = {
            name: forms.display_label(material, display_locale, locale)
            for name, material in materials.items()
            if material is not None
        }
        rows.append(
            split_pane.RadioRow(
                field_id=FieldId.MATERIAL,
                label=translate(locale, "tui.label.material"),
                options=list(forms.unique_labels(display).items()),
                value=state.material,
                on_select=lambda value: setattr(state, "material", value),
            )
        )

    tool_names = list_turning_tools(config_path=materials_config_path)
    tools = {name: get_turning_tool(name, materials_config_path) for name in tool_names}
    tool_display = {
        name: forms.display_label(tool, display_locale, locale)
        for name, tool in tools.items()
        if tool is not None
    }
    rows.append(
        split_pane.RadioRow(
            field_id=FieldId.TOOL,
            label=translate(locale, "tui.label.turning_tool"),
            options=list(forms.unique_labels(tool_display).items()),
            value=state.tool,
            on_select=lambda value: setattr(state, "tool", value),
        )
    )

    rows.append(
        _number_row(
            FieldId.DIAMETER,
            translate(locale, "tui.label.workpiece_diameter"),
            labels["diameter"],
            state.diameter,
            True,
            lambda value: setattr(state, "diameter", value),
        )
    )
    rows.append(
        _number_row(
            FieldId.DEPTH_OF_CUT,
            translate(locale, "tui.label.depth_of_cut"),
            labels["depth_of_cut"],
            state.depth_of_cut,
            True,
            lambda value: setattr(state, "depth_of_cut", value),
        )
    )
    rows.append(
        _number_row(
            FieldId.LENGTH_OF_CUT,
            translate(locale, "tui.label.length_of_cut"),
            labels["depth"],  # length-of-cut shares drilling/depth's "mm"/"in" unit label
            state.length_of_cut,
            True,
            lambda value: setattr(state, "length_of_cut", value),
        )
    )

    def _power_row(label_key: str, required: bool) -> split_pane.NumberRow:
        return _number_row(
            FieldId.AVAILABLE_POWER,
            translate(locale, label_key),
            labels["power"],
            state.available_power,
            required,
            lambda value: setattr(state, "available_power", value),
        )

    def _rpm_row() -> split_pane.NumberRow:
        return _number_row(
            FieldId.TARGET_RPM,
            translate(locale, "tui.label.target_rpm"),
            "RPM",
            state.target_rpm,
            True,
            lambda value: setattr(state, "target_rpm", value),
        )

    rows.extend(
        split_pane.power_and_rpm_rows(
            power_constrained=state.mode is CalculationMode.POWER_CONSTRAINED,
            fixed_rpm=state.mode is CalculationMode.FIXED_RPM,
            power_row=_power_row,
            rpm_row=_rpm_row,
        )
    )

    return rows


def calculate_result(
    state: TurningSessionState, materials_config_path: str | None, locale: str
) -> CalculationResult:
    """The `calculate_turning()` call `split_pane.render_right_pane` invokes
    once every required field (per `rows_for`) holds a value."""

    return calculate_turning(
        diameter=cast(float, state.diameter),
        depth_of_cut=cast(float, state.depth_of_cut),
        length_of_cut=cast(float, state.length_of_cut),
        material=cast(str, state.material),
        tool=cast(str, state.tool),
        unit_system=state.unit_system,
        available_power=state.available_power,
        locale=locale,
        mode=state.mode,
        target_rpm=state.target_rpm,
        materials_config_path=materials_config_path,
    )
