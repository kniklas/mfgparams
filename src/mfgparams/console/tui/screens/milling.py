"""The Milling operation screen (FR-002/FR-004/FR-005/FR-009): end milling
and face milling.

`MillingSessionState` mirrors `console/cli.py`'s (retired)
`_MillingSessionState` unchanged: one instance per sub-operation lives for
the whole app session (`SessionUI.milling_states`), so re-selecting the
same sub-operation offers its own previous answers as defaults without the
other sub-operation's answers leaking in (FR-002 parity). The
End-Milling/Face-Milling choice itself (FR-009a) is a `split_pane.RadioRow`
like any other FR-005 field, following Drilling's placement resolution
(FR-005a) -- selecting a different value swaps which `MillingSessionState`
the open `OperationScreen.session_state` points at, in place, without
closing and reopening the screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, cast

from mfgparams import (
    CalculationMode,
    MillingSubOperation,
    UnitSystem,
    calculate_end_milling,
    calculate_face_milling,
    list_end_mill_tools,
    list_face_mill_tools,
    list_material_types,
    list_materials,
)
from mfgparams.console.i18n import translate
from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen, SessionUI
from mfgparams.console.tui.screens import split_pane
from mfgparams.models import CalculationResult
from mfgparams.processes.machining.milling.end_milling.tools import get_end_mill_tool
from mfgparams.processes.machining.milling.face_milling.tools import get_face_mill_tool
from mfgparams.registry import get_material

_MODE_OPTION_KEYS = {
    CalculationMode.STANDARD: "tui.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "tui.mode.power_constrained",
    CalculationMode.FIXED_RPM: "tui.mode.fixed_rpm",
}

_SUB_OPERATION_OPTION_KEYS = {
    MillingSubOperation.END_MILLING: "tui.milling_sub_operation.end_milling",
    MillingSubOperation.FACE_MILLING: "tui.milling_sub_operation.face_milling",
}


@dataclass
class MillingSessionState:
    """Ported unchanged from `console/cli.py`'s `_MillingSessionState`."""

    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    axial_depth_of_cut: float | None = None
    radial_engagement: float | None = None
    feed_per_tooth: float | None = None
    number_of_teeth: float | None = None
    length_of_cut: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode: CalculationMode = CalculationMode.STANDARD


def _convert_on_unit_change(state: MillingSessionState, unit_system: UnitSystem) -> None:
    """Keep remembered geometry/power meaning their original physical
    quantity across a unit-system switch (Copilot review on PR #94).
    `number_of_teeth`/`target_rpm` are pure counts/RPM and never converted.
    """

    if unit_system is state.unit_system:
        return
    if state.diameter is not None:
        state.diameter = forms.convert_length(state.diameter, state.unit_system, unit_system)
    if state.axial_depth_of_cut is not None:
        state.axial_depth_of_cut = forms.convert_length(
            state.axial_depth_of_cut, state.unit_system, unit_system
        )
    if state.radial_engagement is not None:
        state.radial_engagement = forms.convert_length(
            state.radial_engagement, state.unit_system, unit_system
        )
    if state.feed_per_tooth is not None:
        state.feed_per_tooth = forms.convert_length(
            state.feed_per_tooth, state.unit_system, unit_system
        )
    if state.length_of_cut is not None:
        state.length_of_cut = forms.convert_length(
            state.length_of_cut, state.unit_system, unit_system
        )
    if state.available_power is not None:
        state.available_power = forms.convert_power(
            state.available_power, state.unit_system, unit_system
        )


def current_sub_operation(ui: SessionUI, state: MillingSessionState) -> MillingSubOperation:
    """Reverse-lookup: which sub-operation `state` belongs to, by identity
    against `ui.milling_states` -- the only place that mapping lives (no
    `sub_operation` field on `MillingSessionState` itself, mirroring how
    `MachiningTree` has no field naming "which leaf is selected" either)."""

    for sub_operation, candidate in ui.milling_states.items():
        if candidate is state:
            return sub_operation
    raise AssertionError("session_state is not one of ui.milling_states' values")


def _number_row(
    field_id: FieldId,
    label: str,
    unit: str,
    value: float | None,
    required: bool,
    setter,
    step: float = split_pane.NUDGE_STEP,
) -> split_pane.NumberRow:
    """See drilling.py's identically-shaped helper: `on_commit` is called
    only on navigating away from this field, with the already-parsed
    value. `step` (024-feed-per-tooth-nudge-step) defaults to the shared
    NUDGE_STEP, matching every row that doesn't pass one explicitly."""

    return split_pane.NumberRow(
        field_id=field_id,
        label=label,
        unit=unit,
        value=value,
        required=required,
        on_commit=setter,
        step=step,
    )


def _tool_registry_for(
    sub_operation: MillingSubOperation, materials_config_path: str | None
) -> tuple[list[str], Callable[[str, str | None], object | None], str, str]:
    """The one structural difference between End Milling and Face Milling:
    which tool registry/label/engagement-field label applies. Extracted
    from `rows_for` (Constitution Principle I / complexity gate) -- the two
    sub-operations differ only in *which registry*, not in how a row is
    built from it."""

    if sub_operation is MillingSubOperation.END_MILLING:
        return (
            list_end_mill_tools(config_path=materials_config_path),
            get_end_mill_tool,
            "tui.label.end_mill_tool",
            "cli.label.radial_depth_of_cut",
        )
    return (
        list_face_mill_tools(config_path=materials_config_path),
        get_face_mill_tool,
        "tui.label.face_mill_tool",
        "cli.label.width_of_cut",
    )


def rows_for(
    ui: SessionUI,
    screen: OperationScreen,
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> list[split_pane.Row]:
    """This screen's `split_pane.Row` list. Unlike `drilling.rows_for`,
    needs `ui` (not just `state`) so the sub-operation row's `on_select` can
    swap `screen.session_state` in place (FR-009a)."""

    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    sub_operation = current_sub_operation(ui, state)
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

    def _set_sub_operation(value: str) -> None:
        screen.session_state = ui.milling_states[MillingSubOperation(value)]

    rows.append(
        split_pane.RadioRow(
            field_id=FieldId.SUB_OPERATION,
            label=translate(locale, "tui.label.milling_sub_operation"),
            options=[
                (sub.value, translate(locale, key))
                for sub, key in _SUB_OPERATION_OPTION_KEYS.items()
            ],
            value=sub_operation.value,
            on_select=_set_sub_operation,
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
            # `unique_labels()` disambiguates, matching the Material/Tool
            # rows below -- without it, two user-supplied `material_type`
            # IDs that title-case to the same fallback label (e.g.
            # "cast_iron"/"cast-iron") would render as two indistinguishable
            # options a code-review pass on PR #96 found this row alone was
            # missing that guard for.
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

    tool_names, tool_resolve, tool_label_key, engagement_label_key = _tool_registry_for(
        sub_operation, materials_config_path
    )
    tools = {name: tool_resolve(name, materials_config_path) for name in tool_names}
    tool_display = {
        name: forms.display_label(tool, display_locale, locale)  # type: ignore[arg-type]
        for name, tool in tools.items()
        if tool is not None
    }
    rows.append(
        split_pane.RadioRow(
            field_id=FieldId.TOOL,
            label=translate(locale, tool_label_key),
            options=list(forms.unique_labels(tool_display).items()),
            value=state.tool,
            on_select=lambda value: setattr(state, "tool", value),
        )
    )

    # 025-imperial-geometry-nudge-step/research.md #1: 0.1 in under
    # IMPERIAL for geometry fields -- the shared NUDGE_STEP (1.0) is left
    # unchanged under METRIC.
    geometry_step = split_pane.NUDGE_STEP if state.unit_system is UnitSystem.METRIC else 0.1
    rows.append(
        _number_row(
            FieldId.DIAMETER,
            translate(locale, "tui.label.mill_diameter"),
            labels["diameter"],
            state.diameter,
            True,
            lambda value: setattr(state, "diameter", value),
            step=geometry_step,
        )
    )
    rows.append(
        _number_row(
            FieldId.AXIAL_DEPTH_OF_CUT,
            translate(locale, "cli.label.axial_depth_of_cut"),
            labels["depth"],
            state.axial_depth_of_cut,
            True,
            lambda value: setattr(state, "axial_depth_of_cut", value),
            step=geometry_step,
        )
    )
    rows.append(
        _number_row(
            FieldId.RADIAL_ENGAGEMENT,
            translate(locale, engagement_label_key),
            labels["depth"],
            state.radial_engagement,
            True,
            lambda value: setattr(state, "radial_engagement", value),
            step=geometry_step,
        )
    )
    # 024-feed-per-tooth-nudge-step/research.md #1: 0.1 mm/tooth under
    # METRIC, 0.001 in/tooth under IMPERIAL -- both far finer than the
    # shared NUDGE_STEP (1.0) every other row here keeps, and the
    # imperial value is a standard chip-load shop-practice increment, not
    # a literal conversion of the metric one.
    feed_per_tooth_step = 0.1 if state.unit_system is UnitSystem.METRIC else 0.001
    rows.append(
        _number_row(
            FieldId.FEED_PER_TOOTH,
            translate(locale, "tui.label.feed_per_tooth"),
            labels["feed_per_tooth"],
            state.feed_per_tooth,
            True,
            lambda value: setattr(state, "feed_per_tooth", value),
            step=feed_per_tooth_step,
        )
    )
    rows.append(
        _number_row(
            FieldId.NUMBER_OF_TEETH,
            translate(locale, "tui.label.number_of_teeth"),
            translate(locale, "tui.unit.teeth"),
            state.number_of_teeth,
            True,
            lambda value: setattr(state, "number_of_teeth", value),
        )
    )
    rows.append(
        _number_row(
            FieldId.LENGTH_OF_CUT,
            translate(locale, "tui.label.length_of_cut"),
            labels["depth"],
            state.length_of_cut,
            True,
            lambda value: setattr(state, "length_of_cut", value),
            step=geometry_step,
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
    ui: SessionUI, state: MillingSessionState, materials_config_path: str | None, locale: str
) -> CalculationResult:
    """The `calculate_end_milling()`/`calculate_face_milling()` call
    `split_pane.render_right_pane` invokes once every required field holds
    a value (FR-006/FR-006a)."""

    sub_operation = current_sub_operation(ui, state)
    diameter = cast(float, state.diameter)
    axial_depth_of_cut = cast(float, state.axial_depth_of_cut)
    engagement = cast(float, state.radial_engagement)
    feed_per_tooth = cast(float, state.feed_per_tooth)
    number_of_teeth = cast(float, state.number_of_teeth)
    length_of_cut = cast(float, state.length_of_cut)
    material = cast(str, state.material)
    tool = cast(str, state.tool)

    if sub_operation is MillingSubOperation.END_MILLING:
        return calculate_end_milling(
            diameter=diameter,
            axial_depth_of_cut=axial_depth_of_cut,
            radial_depth_of_cut=engagement,
            feed_per_tooth=feed_per_tooth,
            number_of_teeth=number_of_teeth,
            length_of_cut=length_of_cut,
            material=material,
            tool=tool,
            unit_system=state.unit_system,
            available_power=state.available_power,
            locale=locale,
            mode=state.mode,
            target_rpm=state.target_rpm,
            materials_config_path=materials_config_path,
        )
    return calculate_face_milling(
        diameter=diameter,
        axial_depth_of_cut=axial_depth_of_cut,
        width_of_cut=engagement,
        feed_per_tooth=feed_per_tooth,
        number_of_teeth=number_of_teeth,
        length_of_cut=length_of_cut,
        material=material,
        tool=tool,
        unit_system=state.unit_system,
        available_power=state.available_power,
        locale=locale,
        mode=state.mode,
        target_rpm=state.target_rpm,
        materials_config_path=materials_config_path,
    )
