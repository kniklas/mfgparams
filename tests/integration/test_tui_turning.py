"""Integration test: the Turning operation screen (specs/019-turning-calculations).

Same "call the row closures directly" approach as `test_tui_drilling.py` --
see that file's module docstring for why. Turning is structurally identical
to Drilling (single-subtype process), extended with the third dimensional
input (`depth_of_cut`).
"""

from __future__ import annotations

from mfgparams import CalculationMode, UnitSystem, calculate_turning
from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.turning import (
    GEOMETRY_FIELD_IDS,
    TurningSessionState,
    calculate_result,
    rows_for,
)


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


def test_standard_mode_result_panel_shows_feed_per_rotation_after_feed_rate():
    """specs/020-turning-feed-per-rotation FR-001/User Story 1: the result
    panel includes a new "Feed per rotation" line, immediately after "Feed
    rate", for a standard-mode calculation."""

    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    result = calculate_result(state, None, "en")
    assert result.error is None
    assert result.feed_per_rotation is not None

    text = forms.format_result(result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    lines = text.splitlines()
    feed_rate_index = next(i for i, line in enumerate(lines) if line.startswith("Feed rate:"))
    assert lines[feed_rate_index + 1].startswith("Feed per rotation:")


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


def test_feed_rate_row_only_present_in_feed_rate_constrained_mode():
    """specs/020-turning-feed-per-rotation FR-010."""

    screen = _screen()
    assert FieldId.TARGET_FEED_RATE not in {row.field_id for row in _rows(screen)}
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FEED_RATE_CONSTRAINED.value)
    field_ids = {row.field_id for row in _rows(screen)}
    assert FieldId.TARGET_FEED_RATE in field_ids
    assert FieldId.TARGET_RPM not in field_ids


def test_feed_rate_constrained_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FEED_RATE_CONSTRAINED.value)
    _row(_rows(screen), FieldId.TARGET_FEED_RATE).on_commit(0.5)
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
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm
        assert result.feed_per_rotation == expected.feed_per_rotation == 0.5

    # The result panel renders without KeyError (research.md #9) and shows
    # the new mode's spindle-speed label.
    text = forms.format_result(result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    assert "derived from cutting speed" in text


def test_feed_rate_row_nudges_by_a_finer_step_than_other_turning_rows():
    """specs/020-turning-feed-per-rotation FR-011/User Story 3: the feed-
    rate-per-rotation row nudges by 0.1 mm/rev under METRIC, distinct from
    turning's other rows' default 1.0 step."""

    screen = _screen()
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FEED_RATE_CONSTRAINED.value)

    feed_rate_row = _row(_rows(screen), FieldId.TARGET_FEED_RATE)
    assert isinstance(feed_rate_row, split_pane.NumberRow)
    assert feed_rate_row.step == 0.1

    diameter_row = _row(_rows(screen), FieldId.DIAMETER)
    assert isinstance(diameter_row, split_pane.NumberRow)
    assert diameter_row.step == split_pane.NUDGE_STEP

    screen.selected_field = FieldId.TARGET_FEED_RATE
    split_pane.sync_buffer(_rows(screen), screen)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    # Regression: 0.1 + 0.1 + 0.1 accumulates binary floating-point drift
    # (0.30000000000000004) that the buffer's exact-round-trip formatter
    # would otherwise surface verbatim to the user before this value is
    # ever committed.
    assert screen.field_buffer == "0.3"
    split_pane.move_selection(_rows(screen), screen, 1, "en")
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert round(state.target_feed_rate, 4) == 0.3


def test_feed_rate_row_nudges_by_a_finer_step_under_imperial():
    screen = _screen()
    _row(_rows(screen), FieldId.UNIT_SYSTEM).on_select("imperial")
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FEED_RATE_CONSTRAINED.value)

    feed_rate_row = _row(_rows(screen), FieldId.TARGET_FEED_RATE)
    assert isinstance(feed_rate_row, split_pane.NumberRow)
    assert feed_rate_row.step == 0.005


def test_target_feed_rate_converts_across_a_unit_system_switch():
    """specs/020-turning-feed-per-rotation FR-012, mirroring milling's
    existing feed_per_tooth field's identical treatment."""

    screen = _screen()
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FEED_RATE_CONSTRAINED.value)
    _row(_rows(screen), FieldId.TARGET_FEED_RATE).on_commit(0.5)
    _row(_rows(screen), FieldId.UNIT_SYSTEM).on_select("imperial")
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert state.unit_system is UnitSystem.IMPERIAL
    assert round(state.target_feed_rate, 6) == round(0.5 / 25.4, 6)


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


def test_switching_away_from_feed_rate_constrained_clears_target_feed_rate():
    """specs/020-turning-feed-per-rotation: a feed-rate-constrained value is
    never carried over as an editable default into a different mode."""

    screen = _screen()
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FEED_RATE_CONSTRAINED.value)
    _row(_rows(screen), FieldId.TARGET_FEED_RATE).on_commit(0.5)
    state = screen.session_state
    assert isinstance(state, TurningSessionState)
    assert state.target_feed_rate == 0.5

    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.STANDARD.value)
    assert state.target_feed_rate is None


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


def test_rotation_and_feed_constrained_mode_offers_the_right_rows_and_matches_core():
    """specs/021-turning-combined-constraints FR-001/FR-009."""

    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    mode_row = _row(_rows(screen), FieldId.MODE)
    # MEDIUM Copilot review finding on PR #102: calling on_select directly
    # (below) doesn't prove FR-009's console exposure -- it would still
    # pass even if this mode's _MODE_OPTION_KEYS entry were removed and the
    # option were unreachable from the Mode row itself.
    assert CalculationMode.ROTATION_AND_FEED_CONSTRAINED.value in [
        value for value, _ in mode_row.options
    ]
    mode_row.on_select(CalculationMode.ROTATION_AND_FEED_CONSTRAINED.value)
    field_ids = {row.field_id for row in _rows(screen)}
    assert FieldId.TARGET_RPM in field_ids
    assert FieldId.TARGET_FEED_RATE in field_ids
    assert FieldId.AVAILABLE_POWER in field_ids
    rpm_row = _row(_rows(screen), FieldId.TARGET_RPM)
    feed_row = _row(_rows(screen), FieldId.TARGET_FEED_RATE)
    power_row = _row(_rows(screen), FieldId.AVAILABLE_POWER)
    assert isinstance(rpm_row, split_pane.NumberRow) and rpm_row.required
    assert isinstance(feed_row, split_pane.NumberRow) and feed_row.required
    assert isinstance(power_row, split_pane.NumberRow) and not power_row.required

    _row(_rows(screen), FieldId.TARGET_RPM).on_commit(900)
    _row(_rows(screen), FieldId.TARGET_FEED_RATE).on_commit(0.3)
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
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
    )
    # Full field-by-field equality (FR-009's identical-results guarantee),
    # not just error/rpm/feed (Copilot review finding on this PR: an
    # earlier draft's partial comparison could pass even if the TUI wired
    # up geometry or another dependent result field incorrectly) --
    # CalculationResult is a frozen dataclass, so `==` compares every field.
    assert result == expected
    assert result.spindle_speed_rpm == 900
    assert result.feed_per_rotation == 0.3

    # The result panel renders without KeyError and shows the mode's
    # spindle-speed label, reused from FIXED_RPM's (research.md #8).
    text = forms.format_result(result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    assert "user-specified" in text


def test_power_and_feed_constrained_mode_offers_the_right_rows_and_matches_the_core_calculation():
    """specs/021-turning-combined-constraints FR-003/FR-009."""

    screen = _screen()
    _fill_metal_mild_steel_carbide(screen)
    mode_row = _row(_rows(screen), FieldId.MODE)
    # MEDIUM Copilot review finding on PR #102: same rationale as
    # test_rotation_and_feed_constrained_mode_offers_the_right_rows_and_matches_core.
    assert CalculationMode.POWER_AND_FEED_CONSTRAINED.value in [
        value for value, _ in mode_row.options
    ]
    mode_row.on_select(CalculationMode.POWER_AND_FEED_CONSTRAINED.value)
    field_ids = {row.field_id for row in _rows(screen)}
    assert FieldId.TARGET_FEED_RATE in field_ids
    assert FieldId.AVAILABLE_POWER in field_ids
    assert FieldId.TARGET_RPM not in field_ids
    feed_row = _row(_rows(screen), FieldId.TARGET_FEED_RATE)
    power_row = _row(_rows(screen), FieldId.AVAILABLE_POWER)
    assert isinstance(feed_row, split_pane.NumberRow) and feed_row.required
    assert isinstance(power_row, split_pane.NumberRow) and power_row.required

    _row(_rows(screen), FieldId.TARGET_FEED_RATE).on_commit(0.3)
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
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        target_feed_rate=0.3,
    )
    # Full field-by-field equality (FR-009's identical-results guarantee),
    # not just error/rpm/feed (Copilot review finding on this PR: an
    # earlier draft's partial comparison could pass even if the TUI wired
    # up geometry or another dependent result field incorrectly) --
    # CalculationResult is a frozen dataclass, so `==` compares every field.
    assert result == expected
    assert result.feed_per_rotation == 0.3

    # The result panel renders without KeyError and shows the mode's
    # spindle-speed label, reused from POWER_CONSTRAINED's (research.md #8).
    text = forms.format_result(result, forms.UNIT_LABELS[UnitSystem.METRIC], "en")
    assert "adjusted to fit available power" in text


def test_geometry_fields_nudge_by_the_default_step_under_metric():
    """specs/025-imperial-geometry-nudge-step FR-004: workpiece diameter,
    depth of cut, and length of cut keep today's default step under
    METRIC, unchanged by this feature."""

    screen = _screen()
    for field_id in GEOMETRY_FIELD_IDS:
        row = _row(_rows(screen), field_id)
        assert isinstance(row, split_pane.NumberRow)
        assert row.step == split_pane.NUDGE_STEP


def test_geometry_fields_nudge_by_a_finer_step_under_imperial():
    """specs/025-imperial-geometry-nudge-step FR-003: workpiece diameter,
    depth of cut, and length of cut each nudge by 0.1 in under IMPERIAL,
    distinct from feed-rate-per-rotation's own 0.005 in step."""

    screen = _screen()
    _row(_rows(screen), FieldId.UNIT_SYSTEM).on_select("imperial")
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FEED_RATE_CONSTRAINED.value)

    for field_id in GEOMETRY_FIELD_IDS:
        row = _row(_rows(screen), field_id)
        assert isinstance(row, split_pane.NumberRow)
        assert row.step == 0.1

    feed_rate_row = _row(_rows(screen), FieldId.TARGET_FEED_RATE)
    assert isinstance(feed_rate_row, split_pane.NumberRow)
    assert feed_rate_row.step == 0.005


def test_geometry_step_follows_the_unit_system_immediately_after_switching():
    """specs/025-imperial-geometry-nudge-step FR-005/User Story 2: the
    step used is recomputed fresh from the currently active unit system on
    every render, so it never lags behind a mid-session switch, including
    across repeated switches."""

    screen = _screen()
    unit_system_row = _row(_rows(screen), FieldId.UNIT_SYSTEM)

    unit_system_row.on_select("imperial")
    assert _row(_rows(screen), FieldId.DIAMETER).step == 0.1

    unit_system_row.on_select("metric")
    assert _row(_rows(screen), FieldId.DIAMETER).step == split_pane.NUDGE_STEP

    unit_system_row.on_select("imperial")
    assert _row(_rows(screen), FieldId.DIAMETER).step == 0.1
