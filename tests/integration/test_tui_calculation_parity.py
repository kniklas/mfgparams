"""Integration test: the TUI's displayed result is byte-identical to the
core calculation, for identical inputs (018-tui-splitpane-redesign SC-004,
tasks.md T026).

Contract §6: this feature is a presentation-layer change only -- the
calculation contract itself is unchanged. Compares
`forms.format_result`'s rendered text (what the right pane actually shows)
against `calculate()`/`calculate_end_milling()`/`calculate_face_milling()`
called directly, not just comparing the underlying `CalculationResult`
objects field-by-field.
"""

from __future__ import annotations

from mfgparams import (
    CalculationMode,
    UnitSystem,
    calculate,
    calculate_end_milling,
    calculate_face_milling,
    calculate_turning,
)
from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen, SessionUI
from mfgparams.console.tui.screens.drilling import DrillingSessionState
from mfgparams.console.tui.screens.drilling import calculate_result as drilling_calculate
from mfgparams.console.tui.screens.drilling import rows_for as drilling_rows_for
from mfgparams.console.tui.screens.milling import calculate_result as milling_calculate
from mfgparams.console.tui.screens.turning import TurningSessionState
from mfgparams.console.tui.screens.turning import calculate_result as turning_calculate
from mfgparams.console.tui.screens.turning import rows_for as turning_rows_for


def _row(rows, field_id: FieldId):
    return next(row for row in rows if row.field_id is field_id)


def test_drilling_result_text_is_byte_identical_to_the_core_calculation():
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.MATERIAL).on_select("Mild Steel")
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.TOOL).on_select("HSS")
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.DIAMETER).on_commit(10.0)
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.DEPTH).on_commit(20.0)

    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    tui_result = drilling_calculate(state, None, "en")
    tui_text = forms.format_result(tui_result, forms.UNIT_LABELS[state.unit_system], "en")

    direct_result = calculate(
        diameter=10.0,
        depth=20.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.STANDARD,
        target_rpm=None,
    )
    direct_text = forms.format_result(direct_result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    assert tui_text == direct_text


def test_end_milling_result_text_is_byte_identical_to_the_core_calculation():
    from mfgparams import MillingSubOperation
    from mfgparams.console.tui.app import MenuBar
    from mfgparams.console.tui.screens.milling import MillingSessionState
    from mfgparams.console.tui.screens.milling import rows_for as milling_rows_for

    ui = SessionUI(menu_bar=MenuBar(entries=()))
    screen = OperationScreen(
        operation="milling",
        session_state=ui.milling_states[MillingSubOperation.END_MILLING],
        selected_field=FieldId.UNIT_SYSTEM,
    )
    for field_id, value in [
        (FieldId.MATERIAL_TYPE, "metal"),
        (FieldId.MATERIAL, "Mild Steel"),
        (FieldId.TOOL, "HSS"),
    ]:
        _row(milling_rows_for(ui, screen, None, "en", "en"), field_id).on_select(value)
    for field_id, text in [
        (FieldId.DIAMETER, "10"),
        (FieldId.AXIAL_DEPTH_OF_CUT, "2"),
        (FieldId.RADIAL_ENGAGEMENT, "1"),
        (FieldId.FEED_PER_TOOTH, "0.05"),
        (FieldId.NUMBER_OF_TEETH, "4"),
        (FieldId.LENGTH_OF_CUT, "50"),
    ]:
        _row(milling_rows_for(ui, screen, None, "en", "en"), field_id).on_commit(float(text))

    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    tui_result = milling_calculate(ui, state, None, "en")
    tui_text = forms.format_result(tui_result, forms.UNIT_LABELS[state.unit_system], "en")

    direct_result = calculate_end_milling(
        diameter=10.0,
        axial_depth_of_cut=2.0,
        radial_depth_of_cut=1.0,
        feed_per_tooth=0.05,
        number_of_teeth=4.0,
        length_of_cut=50.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.STANDARD,
        target_rpm=None,
    )
    direct_text = forms.format_result(direct_result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    assert tui_text == direct_text


def test_face_milling_result_text_is_byte_identical_to_the_core_calculation():
    from mfgparams import MillingSubOperation
    from mfgparams.console.tui.app import MenuBar
    from mfgparams.console.tui.screens.milling import MillingSessionState
    from mfgparams.console.tui.screens.milling import rows_for as milling_rows_for

    ui = SessionUI(menu_bar=MenuBar(entries=()))
    screen = OperationScreen(
        operation="milling",
        session_state=ui.milling_states[MillingSubOperation.FACE_MILLING],
        selected_field=FieldId.UNIT_SYSTEM,
    )
    for field_id, value in [
        (FieldId.MATERIAL_TYPE, "metal"),
        (FieldId.MATERIAL, "Mild Steel"),
        (FieldId.TOOL, "HSS"),
    ]:
        _row(milling_rows_for(ui, screen, None, "en", "en"), field_id).on_select(value)
    for field_id, text in [
        (FieldId.DIAMETER, "50"),
        (FieldId.AXIAL_DEPTH_OF_CUT, "2"),
        (FieldId.RADIAL_ENGAGEMENT, "30"),
        (FieldId.FEED_PER_TOOTH, "0.1"),
        (FieldId.NUMBER_OF_TEETH, "6"),
        (FieldId.LENGTH_OF_CUT, "100"),
    ]:
        _row(milling_rows_for(ui, screen, None, "en", "en"), field_id).on_commit(float(text))

    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    tui_result = milling_calculate(ui, state, None, "en")
    tui_text = forms.format_result(tui_result, forms.UNIT_LABELS[state.unit_system], "en")

    direct_result = calculate_face_milling(
        diameter=50.0,
        axial_depth_of_cut=2.0,
        width_of_cut=30.0,
        feed_per_tooth=0.1,
        number_of_teeth=6.0,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.STANDARD,
        target_rpm=None,
    )
    direct_text = forms.format_result(direct_result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    assert tui_text == direct_text


def test_turning_result_text_is_byte_identical_to_the_core_calculation():
    screen = OperationScreen(
        operation="turning",
        session_state=TurningSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    _row(turning_rows_for(screen, None, "en", "en"), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(turning_rows_for(screen, None, "en", "en"), FieldId.MATERIAL).on_select("Mild Steel")
    _row(turning_rows_for(screen, None, "en", "en"), FieldId.TOOL).on_select("Carbide")
    _row(turning_rows_for(screen, None, "en", "en"), FieldId.DIAMETER).on_commit(40.0)
    _row(turning_rows_for(screen, None, "en", "en"), FieldId.DEPTH_OF_CUT).on_commit(2.0)
    _row(turning_rows_for(screen, None, "en", "en"), FieldId.LENGTH_OF_CUT).on_commit(100.0)

    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    tui_result = turning_calculate(state, None, "en")
    tui_text = forms.format_result(tui_result, forms.UNIT_LABELS[state.unit_system], "en")

    direct_result = calculate_turning(
        diameter=40.0,
        depth_of_cut=2.0,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.STANDARD,
        target_rpm=None,
    )
    direct_text = forms.format_result(direct_result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    assert tui_text == direct_text
