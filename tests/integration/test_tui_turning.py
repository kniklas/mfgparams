"""Integration test: the Turning operation screen (specs/019-turning-calculations).

Same "call the row closures directly" approach as `test_tui_drilling.py` --
see that file's module docstring for why. Turning is structurally identical
to Drilling (single-subtype process), extended with the third dimensional
input (`depth_of_cut`).
"""

from __future__ import annotations

from mfgparams import CalculationMode, UnitSystem, calculate_turning
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.turning import TurningSessionState, calculate_result, rows_for


def _screen(state: TurningSessionState | None = None) -> OperationScreen:
    return OperationScreen(
        operation="turning",
        session_state=state or TurningSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )


def _rows(screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(screen, None, "en", "en")


def _row(rows: list[split_pane.Row], field_id: FieldId) -> split_pane.Row:
    return next(row for row in rows if row.field_id is field_id)


def _fill_metal_mild_steel_carbide(screen: OperationScreen) -> None:
    _row(_rows(screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(screen), FieldId.TOOL).on_select("Carbide")
    _row(_rows(screen), FieldId.DIAMETER).on_commit(40.0)
    _row(_rows(screen), FieldId.DEPTH_OF_CUT).on_commit(2.0)
    _row(_rows(screen), FieldId.LENGTH_OF_CUT).on_commit(100.0)


def test_every_required_field_is_visible_simultaneously_without_a_screen_transition():
    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    field_ids = {row.field_id for row in _rows(screen)}
    assert field_ids == {
        FieldId.UNIT_SYSTEM,
        FieldId.MODE,
        FieldId.MATERIAL_TYPE,
        FieldId.MATERIAL,
        FieldId.TOOL,
        FieldId.DIAMETER,
        FieldId.DEPTH_OF_CUT,
        FieldId.LENGTH_OF_CUT,
        FieldId.AVAILABLE_POWER,
    }


def test_material_type_selection_expands_a_further_material_radio_choice():
    screen = _screen()
    assert FieldId.MATERIAL not in {row.field_id for row in _rows(screen)}
    _row(_rows(screen), FieldId.MATERIAL_TYPE).on_select("metal")
    assert FieldId.MATERIAL in {row.field_id for row in _rows(screen)}


def test_unit_system_change_converts_diameter_and_depth_of_cut_rather_than_discarding_them():
    """Mirrors drilling's PR #94 unit-carryover fix, extended to turning's
    depth_of_cut field."""

    screen = _screen()
    _row(_rows(screen), FieldId.DIAMETER).on_commit(40.0)
    _row(_rows(screen), FieldId.DEPTH_OF_CUT).on_commit(2.0)
    _row(_rows(screen), FieldId.UNIT_SYSTEM).on_select("imperial")
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert state.unit_system is UnitSystem.IMPERIAL
    assert round(state.diameter, 4) == round(40 / 25.4, 4)
    assert round(state.depth_of_cut, 4) == round(2 / 25.4, 4)


def test_standard_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    assert result.error is None

    expected = calculate_turning(
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
    assert result.spindle_speed_rpm == expected.spindle_speed_rpm
    assert result.feed_rate == expected.feed_rate
    assert result.cutting_force == expected.cutting_force


def test_target_rpm_field_only_present_in_fixed_rpm_mode():
    screen = _screen()
    assert FieldId.TARGET_RPM not in {row.field_id for row in _rows(screen)}
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    assert FieldId.TARGET_RPM in {row.field_id for row in _rows(screen)}


def test_fixed_rpm_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    _row(_rows(screen), FieldId.TARGET_RPM).on_commit(900.0)
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    expected = calculate_turning(
        diameter=40.0,
        depth_of_cut=2.0,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=900.0,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_power_constrained_mode_requires_available_power_to_be_complete():
    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    assert not split_pane.is_complete(_rows(screen))
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_commit(0.5)
    assert split_pane.is_complete(_rows(screen))


def test_power_constrained_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_commit(0.5)
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    expected = calculate_turning(
        diameter=40.0,
        depth_of_cut=2.0,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.METRIC,
        available_power=0.5,
        locale="en",
        mode=CalculationMode.POWER_CONSTRAINED,
        target_rpm=None,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm
        assert result.feed_rate == expected.feed_rate


def test_switching_mode_clears_the_previous_modes_power_or_rpm_value():
    screen = _screen()
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_commit(0.5)
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert state.available_power == 0.5

    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    assert state.available_power is None
    assert state.target_rpm is None


def test_invalid_depth_of_cut_shows_structured_error_instead_of_result():
    """spec.md Edge Cases: depth of cut >= workpiece radius surfaces as an
    inline error, not a crash or a stale result."""

    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    _row(_rows(screen), FieldId.DIAMETER).on_commit(10.0)  # radius = 5mm
    _row(_rows(screen), FieldId.DEPTH_OF_CUT).on_commit(6.0)
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    assert result.error is not None
    assert result.error.code == "INVALID_DEPTH_OF_CUT"
