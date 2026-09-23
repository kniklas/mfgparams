"""Integration test: the Milling operation screen, both sub-operations
(018-tui-splitpane-redesign US2, tasks.md T015).

Same "call the row closures directly" approach as `test_tui_drilling.py` --
see that file's module docstring for why.
"""

from __future__ import annotations

from mfgparams import (
    CalculationMode,
    MillingSubOperation,
    UnitSystem,
    calculate_end_milling,
    calculate_face_milling,
)
from mfgparams.console.tui.app import FieldId, OperationScreen, SessionUI
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.milling import (
    GEOMETRY_FIELD_IDS,
    MillingSessionState,
    calculate_result,
    rows_for,
)


def _ui() -> SessionUI:
    from mfgparams.console.tui.app import MenuBar

    return SessionUI(menu_bar=MenuBar(entries=()))


def _screen(
    ui: SessionUI, sub_operation: MillingSubOperation = MillingSubOperation.END_MILLING
) -> OperationScreen:
    return OperationScreen(
        operation="milling",
        session_state=ui.milling_states[sub_operation],
        selected_field=FieldId.UNIT_SYSTEM,
    )


def _rows(ui: SessionUI, screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(ui, screen, None, "en", "en")


def _row(rows: list[split_pane.Row], field_id: FieldId) -> split_pane.Row:
    return next(row for row in rows if row.field_id is field_id)


def _fill_end_milling(ui: SessionUI, screen: OperationScreen) -> None:
    _row(_rows(ui, screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(ui, screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(ui, screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(ui, screen), FieldId.DIAMETER).on_commit(10.0)
    _row(_rows(ui, screen), FieldId.AXIAL_DEPTH_OF_CUT).on_commit(2.0)
    _row(_rows(ui, screen), FieldId.RADIAL_ENGAGEMENT).on_commit(1.0)
    _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH).on_commit(0.05)
    _row(_rows(ui, screen), FieldId.NUMBER_OF_TEETH).on_commit(4.0)
    _row(_rows(ui, screen), FieldId.LENGTH_OF_CUT).on_commit(50.0)


def test_every_fr005_field_is_visible_simultaneously_without_a_screen_transition():
    """Acceptance Scenario 4 -- the same simultaneous-input pattern applies
    to Milling's own inputs."""

    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    field_ids = {row.field_id for row in _rows(ui, screen)}
    assert field_ids == {
        FieldId.UNIT_SYSTEM,
        FieldId.MODE,
        FieldId.SUB_OPERATION,
        FieldId.MATERIAL_TYPE,
        FieldId.MATERIAL,
        FieldId.TOOL,
        FieldId.DIAMETER,
        FieldId.AXIAL_DEPTH_OF_CUT,
        FieldId.RADIAL_ENGAGEMENT,
        FieldId.FEED_PER_TOOTH,
        FieldId.NUMBER_OF_TEETH,
        FieldId.LENGTH_OF_CUT,
        FieldId.AVAILABLE_POWER,
    }


def test_end_milling_reaches_a_result_matching_the_core_calculation():
    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    assert result.error is None

    expected = calculate_end_milling(
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
    assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_selecting_face_milling_swaps_to_its_own_independent_session_state():
    """FR-009a: the End-Milling/Face-Milling choice is a left-pane field;
    switching it swaps `OperationScreen.session_state` in place, and each
    sub-operation keeps its own answers independently (FR-002 parity)."""

    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    end_milling_state = screen.session_state

    _row(_rows(ui, screen), FieldId.SUB_OPERATION).on_select(MillingSubOperation.FACE_MILLING.value)
    assert screen.session_state is ui.milling_states[MillingSubOperation.FACE_MILLING]
    assert screen.session_state is not end_milling_state
    # Switching back offers the still-intact End-Milling answers.
    _row(_rows(ui, screen), FieldId.SUB_OPERATION).on_select(MillingSubOperation.END_MILLING.value)
    assert screen.session_state is end_milling_state
    assert screen.session_state.diameter == 10.0


def test_face_milling_reaches_a_result_matching_the_core_calculation():
    ui = _ui()
    screen = _screen(ui, MillingSubOperation.FACE_MILLING)
    _row(_rows(ui, screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(ui, screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(ui, screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(ui, screen), FieldId.DIAMETER).on_commit(50.0)
    _row(_rows(ui, screen), FieldId.AXIAL_DEPTH_OF_CUT).on_commit(2.0)
    _row(_rows(ui, screen), FieldId.RADIAL_ENGAGEMENT).on_commit(30.0)
    _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH).on_commit(0.1)
    _row(_rows(ui, screen), FieldId.NUMBER_OF_TEETH).on_commit(6.0)
    _row(_rows(ui, screen), FieldId.LENGTH_OF_CUT).on_commit(100.0)
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    assert result.error is None

    expected = calculate_face_milling(
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
    assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_end_milling_fixed_rpm_mode_reaches_a_result_matching_the_core_calculation():
    """Round-3 code-review finding (T015): both sub-operations need
    coverage for all three `CalculationMode` values, not just Standard --
    `test_tui_drilling.py` already covers Fixed RPM/Power constrained for
    Drilling; this and the three tests below close the same gap here."""

    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    _row(_rows(ui, screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    _row(_rows(ui, screen), FieldId.TARGET_RPM).on_commit(1500.0)
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    expected = calculate_end_milling(
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
        mode=CalculationMode.FIXED_RPM,
        target_rpm=1500.0,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_end_milling_power_constrained_mode_reaches_a_result_matching_the_core_calculation():
    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    _row(_rows(ui, screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    _row(_rows(ui, screen), FieldId.AVAILABLE_POWER).on_commit(3.0)
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    expected = calculate_end_milling(
        diameter=10.0,
        axial_depth_of_cut=2.0,
        radial_depth_of_cut=1.0,
        feed_per_tooth=0.05,
        number_of_teeth=4.0,
        length_of_cut=50.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=3.0,
        locale="en",
        mode=CalculationMode.POWER_CONSTRAINED,
        target_rpm=None,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def _fill_face_milling(ui: SessionUI, screen: OperationScreen) -> None:
    _row(_rows(ui, screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(ui, screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(ui, screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(ui, screen), FieldId.DIAMETER).on_commit(50.0)
    _row(_rows(ui, screen), FieldId.AXIAL_DEPTH_OF_CUT).on_commit(2.0)
    _row(_rows(ui, screen), FieldId.RADIAL_ENGAGEMENT).on_commit(30.0)
    _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH).on_commit(0.1)
    _row(_rows(ui, screen), FieldId.NUMBER_OF_TEETH).on_commit(6.0)
    _row(_rows(ui, screen), FieldId.LENGTH_OF_CUT).on_commit(100.0)


def test_face_milling_fixed_rpm_mode_reaches_a_result_matching_the_core_calculation():
    ui = _ui()
    screen = _screen(ui, MillingSubOperation.FACE_MILLING)
    _fill_face_milling(ui, screen)
    _row(_rows(ui, screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    _row(_rows(ui, screen), FieldId.TARGET_RPM).on_commit(800.0)
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    expected = calculate_face_milling(
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
        mode=CalculationMode.FIXED_RPM,
        target_rpm=800.0,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_face_milling_power_constrained_mode_reaches_a_result_matching_the_core_calculation():
    ui = _ui()
    screen = _screen(ui, MillingSubOperation.FACE_MILLING)
    _fill_face_milling(ui, screen)
    _row(_rows(ui, screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    _row(_rows(ui, screen), FieldId.AVAILABLE_POWER).on_commit(4.0)
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    expected = calculate_face_milling(
        diameter=50.0,
        axial_depth_of_cut=2.0,
        width_of_cut=30.0,
        feed_per_tooth=0.1,
        number_of_teeth=6.0,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=4.0,
        locale="en",
        mode=CalculationMode.POWER_CONSTRAINED,
        target_rpm=None,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_revisiting_the_same_sub_operation_offers_prior_answers_as_defaults():
    """SC-005/FR-002 parity."""

    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    first_diameter = ui.milling_states[MillingSubOperation.END_MILLING].diameter

    # A fresh OperationScreen re-opened onto the same, already-populated
    # state (mirrors app.py's `_open_milling` reuse) sees the same values.
    reopened = OperationScreen(
        operation="milling",
        session_state=ui.milling_states[MillingSubOperation.END_MILLING],
        selected_field=FieldId.UNIT_SYSTEM,
    )
    assert reopened.session_state.diameter == first_diameter


def test_feed_per_tooth_row_nudges_by_a_finer_step_than_other_milling_rows():
    """specs/024-feed-per-tooth-nudge-step FR-001/FR-003: the feed-per-tooth
    row nudges by 0.1 mm/tooth under METRIC, distinct from milling's other
    rows' default 1.0 step."""

    ui = _ui()
    screen = _screen(ui)

    feed_per_tooth_row = _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH)
    assert isinstance(feed_per_tooth_row, split_pane.NumberRow)
    assert feed_per_tooth_row.step == 0.1

    diameter_row = _row(_rows(ui, screen), FieldId.DIAMETER)
    assert isinstance(diameter_row, split_pane.NumberRow)
    assert diameter_row.step == split_pane.NUDGE_STEP

    screen.selected_field = FieldId.FEED_PER_TOOTH
    split_pane.sync_buffer(_rows(ui, screen), screen)
    split_pane.nudge_selected(_rows(ui, screen), screen, 1)
    split_pane.nudge_selected(_rows(ui, screen), screen, 1)
    split_pane.nudge_selected(_rows(ui, screen), screen, 1)
    # Regression: 0.1 + 0.1 + 0.1 accumulates binary floating-point drift
    # (0.30000000000000004) that the buffer's exact-round-trip formatter
    # would otherwise surface verbatim to the user before this value is
    # ever committed (same Decimal-safe arithmetic 020-turning-feed-per-
    # rotation added for its own sub-1.0 step).
    assert screen.field_buffer == "0.3"
    split_pane.move_selection(_rows(ui, screen), screen, 1, "en")
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert round(state.feed_per_tooth, 4) == 0.3


def test_feed_per_tooth_row_nudges_by_a_finer_step_under_imperial():
    """research.md #1: 0.001 in/tooth, a standard chip-load shop-practice
    increment -- not turning's 0.005 in/rev, and not a literal 0.1 mm
    conversion."""

    ui = _ui()
    screen = _screen(ui)
    _row(_rows(ui, screen), FieldId.UNIT_SYSTEM).on_select("imperial")

    feed_per_tooth_row = _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH)
    assert isinstance(feed_per_tooth_row, split_pane.NumberRow)
    assert feed_per_tooth_row.step == 0.001


def test_feed_per_tooth_converts_across_a_unit_system_switch():
    """specs/024-feed-per-tooth-nudge-step FR-004: unchanged from today's
    existing conversion behavior -- this feature only changes the nudge
    step, not the field's value/unit-conversion handling."""

    ui = _ui()
    screen = _screen(ui)
    _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH).on_commit(0.5)
    _row(_rows(ui, screen), FieldId.UNIT_SYSTEM).on_select("imperial")
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert state.unit_system is UnitSystem.IMPERIAL
    assert round(state.feed_per_tooth, 6) == round(0.5 / 25.4, 6)


def test_feed_per_tooth_nudge_below_zero_clears_rather_than_going_negative():
    """FR-005, mirroring every other nudge-adjustable field's existing
    behavior (contract's implementation detail)."""

    ui = _ui()
    screen = _screen(ui)
    screen.selected_field = FieldId.FEED_PER_TOOTH
    split_pane.sync_buffer(_rows(ui, screen), screen)
    split_pane.nudge_selected(_rows(ui, screen), screen, 1)
    split_pane.nudge_selected(_rows(ui, screen), screen, -1)
    assert screen.field_buffer == ""


def test_feed_per_tooth_step_applies_to_face_milling_too():
    """FR-006/Acceptance Scenario 4: uniform across both sub-operations,
    since the field is shared, not sub-operation-specific."""

    ui = _ui()
    screen = _screen(ui, MillingSubOperation.FACE_MILLING)
    row = _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH)
    assert isinstance(row, split_pane.NumberRow)
    assert row.step == 0.1




def test_geometry_fields_nudge_by_the_default_step_under_metric():
    """specs/025-imperial-geometry-nudge-step FR-004: cutter diameter,
    axial depth of cut, radial engagement, and length of cut keep today's
    default step under METRIC, unchanged by this feature."""

    ui = _ui()
    screen = _screen(ui)
    for field_id in GEOMETRY_FIELD_IDS:
        row = _row(_rows(ui, screen), field_id)
        assert isinstance(row, split_pane.NumberRow)
        assert row.step == split_pane.NUDGE_STEP


def test_geometry_fields_nudge_by_a_finer_step_under_imperial():
    """specs/025-imperial-geometry-nudge-step FR-001: cutter diameter,
    axial depth of cut, radial engagement, and length of cut each nudge by
    0.1 in under IMPERIAL, distinct from feed-per-tooth's own 0.001 in
    step and from the metric 1.0 default."""

    ui = _ui()
    screen = _screen(ui)
    _row(_rows(ui, screen), FieldId.UNIT_SYSTEM).on_select("imperial")

    for field_id in GEOMETRY_FIELD_IDS:
        row = _row(_rows(ui, screen), field_id)
        assert isinstance(row, split_pane.NumberRow)
        assert row.step == 0.1

    feed_per_tooth_row = _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH)
    assert isinstance(feed_per_tooth_row, split_pane.NumberRow)
    assert feed_per_tooth_row.step == 0.001


def test_geometry_step_follows_the_unit_system_immediately_after_switching():
    """specs/025-imperial-geometry-nudge-step FR-005/User Story 2: the
    step used is recomputed fresh from the currently active unit system on
    every render, so it never lags behind a mid-session switch, including
    across repeated switches."""

    ui = _ui()
    screen = _screen(ui)
    unit_system_row = _row(_rows(ui, screen), FieldId.UNIT_SYSTEM)

    unit_system_row.on_select("imperial")
    assert _row(_rows(ui, screen), FieldId.DIAMETER).step == 0.1

    unit_system_row.on_select("metric")
    assert _row(_rows(ui, screen), FieldId.DIAMETER).step == split_pane.NUDGE_STEP

    unit_system_row.on_select("imperial")
    assert _row(_rows(ui, screen), FieldId.DIAMETER).step == 0.1
