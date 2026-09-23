"""Integration test: the Drilling operation screen (018-tui-splitpane-redesign
US2, tasks.md T014).

Drives `screens.drilling.rows_for`/`calculate_result` directly -- the same
functions `app.py`'s key bindings call on every keystroke -- rather than
through the full headless `Application` (`test_tui_navigation.py` covers
that wiring layer separately, per spec's "Do not invest further in the
soon-to-be-deleted dialog-chain tests" recommendation to write fresh
coverage from the start). Each `RadioRow`'s `on_select` and each
`NumberRow`'s `on_commit` closure *is* what a keystroke ultimately invokes
(`on_commit` via `split_pane.move_selection`, once the user navigates away
from the field), so calling it directly is a faithful, non-flaky simulation
without prompt_toolkit's timing-sensitive pipe-input harness, without
needing to also simulate the intervening `field_buffer` typing/navigation.
"""

from __future__ import annotations

from mfgparams import CalculationMode, UnitSystem, calculate
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import (
    GEOMETRY_FIELD_IDS,
    DrillingSessionState,
    calculate_result,
    rows_for,
)


def _screen(state: DrillingSessionState | None = None) -> OperationScreen:
    return OperationScreen(
        operation="drilling",
        session_state=state or DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )


def _rows(screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(screen, None, "en", "en")


def _row(rows: list[split_pane.Row], field_id: FieldId) -> split_pane.Row:
    return next(row for row in rows if row.field_id is field_id)


def _fill_metal_mild_steel_hss(screen: OperationScreen) -> None:
    """Metal/Mild Steel/HSS, 10mm diameter, 20mm depth -- the same
    known-good combination 017's drilling test used (confirmed above to
    produce a valid, non-error `calculate()` result)."""

    _row(_rows(screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(screen), FieldId.DIAMETER).on_commit(10.0)
    _row(_rows(screen), FieldId.DEPTH).on_commit(20.0)


def test_every_fr005_field_is_visible_simultaneously_without_a_screen_transition():
    """Acceptance Scenario 1."""

    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    field_ids = {row.field_id for row in _rows(screen)}
    assert field_ids == {
        FieldId.UNIT_SYSTEM,
        FieldId.MODE,
        FieldId.MATERIAL_TYPE,
        FieldId.MATERIAL,
        FieldId.TOOL,
        FieldId.DIAMETER,
        FieldId.DEPTH,
        FieldId.AVAILABLE_POWER,
    }


def test_material_type_selection_expands_a_further_material_radio_choice():
    """Acceptance Scenario 2."""

    screen = _screen()
    assert FieldId.MATERIAL not in {row.field_id for row in _rows(screen)}
    _row(_rows(screen), FieldId.MATERIAL_TYPE).on_select("metal")
    assert FieldId.MATERIAL in {row.field_id for row in _rows(screen)}


def test_unit_system_change_converts_diameter_rather_than_discarding_it():
    """Acceptance Scenario 3, mirroring PR #94's unit-carryover fix."""

    screen = _screen()
    _row(_rows(screen), FieldId.DIAMETER).on_commit(10.0)
    _row(_rows(screen), FieldId.UNIT_SYSTEM).on_select("imperial")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system is UnitSystem.IMPERIAL
    assert state.diameter is not None
    assert round(state.diameter, 4) == round(10 / 25.4, 4)


def test_standard_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    assert result.error is None

    expected = calculate(
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
    assert result.spindle_speed_rpm == expected.spindle_speed_rpm
    assert result.feed_rate == expected.feed_rate


def test_target_rpm_field_only_present_in_fixed_rpm_mode():
    screen = _screen()
    assert FieldId.TARGET_RPM not in {row.field_id for row in _rows(screen)}
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    assert FieldId.TARGET_RPM in {row.field_id for row in _rows(screen)}


def test_fixed_rpm_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    _row(_rows(screen), FieldId.TARGET_RPM).on_commit(500.0)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    expected = calculate(
        diameter=10.0,
        depth=20.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=500.0,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_power_constrained_mode_requires_available_power_to_be_complete():
    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    assert not split_pane.is_complete(_rows(screen))
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_commit(2.0)
    assert split_pane.is_complete(_rows(screen))


def test_power_constrained_mode_reaches_a_result_matching_the_core_calculation():
    """Round-3 code-review finding: the completeness test above never
    checked that a complete Power constrained screen actually reaches a
    result matching the core calculation -- unlike Standard and Fixed RPM
    mode, which both have their own such test. Mirrors those two."""

    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_commit(2.0)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    expected = calculate(
        diameter=10.0,
        depth=20.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=2.0,
        locale="en",
        mode=CalculationMode.POWER_CONSTRAINED,
        target_rpm=None,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm
        assert result.feed_rate == expected.feed_rate


def test_switching_mode_clears_the_previous_modes_power_or_rpm_value():
    """Mirrors the pre-018 dialog chain's `mode_changed` guard: a mode's
    power/RPM field(s) must not silently default to a value entered under a
    *different* mode."""

    screen = _screen()
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_commit(5.0)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.available_power == 5.0

    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    assert state.available_power is None
    assert state.target_rpm is None


def test_geometry_fields_nudge_by_the_default_step_under_metric():
    """specs/025-imperial-geometry-nudge-step FR-004: drill diameter and
    hole depth keep today's default step under METRIC, unchanged by this
    feature."""

    screen = _screen()
    for field_id in GEOMETRY_FIELD_IDS:
        row = _row(_rows(screen), field_id)
        assert isinstance(row, split_pane.NumberRow)
        assert row.step == split_pane.NUDGE_STEP


def test_geometry_fields_nudge_by_a_finer_step_under_imperial():
    """specs/025-imperial-geometry-nudge-step FR-002: drill diameter and
    hole depth each nudge by 0.1 in under IMPERIAL, while available power
    keeps the metric 1.0 default."""

    screen = _screen()
    _row(_rows(screen), FieldId.UNIT_SYSTEM).on_select("imperial")

    for field_id in GEOMETRY_FIELD_IDS:
        row = _row(_rows(screen), field_id)
        assert isinstance(row, split_pane.NumberRow)
        assert row.step == 0.1

    power_row = _row(_rows(screen), FieldId.AVAILABLE_POWER)
    assert isinstance(power_row, split_pane.NumberRow)
    assert power_row.step == split_pane.NUDGE_STEP


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
