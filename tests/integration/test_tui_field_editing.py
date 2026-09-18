"""Integration test: numeric-field buffered edit/nudge and radio-field
cycle-and-commit navigation (018-tui-splitpane-redesign FR-016/FR-017/
FR-005, tasks.md T016, rewritten a second time to match the pre-plan
prototype exactly -- see `split_pane.py`'s module docstring for why).

Drives `screens.split_pane`'s edit/nudge/move functions directly against a
real Drilling screen's rows -- the same functions `app.py`'s key bindings
call.

Governing behaviors (matching the prototype's own code, not the
Phase-8/`RadioList`-style two-step interaction this file previously
tested):

- A radio field is a single `Label: value` line. Left/Right/Space cycle its
  value with wraparound and commit it *immediately* via `on_select` -- no
  separate highlight/confirm step, no more `radio_navigate`/`radio_commit`.
- Up/Down (`move_selection`) always moves between fields, unconditionally.
- A numeric field's typed/nudged text lives in `field_buffer` only.
  `session_state` is untouched until the user navigates away from the
  field (`move_selection`, which calls `_commit_current` first).
"""

from __future__ import annotations

from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import DrillingSessionState, rows_for


def _screen() -> OperationScreen:
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    split_pane.sync_buffer(rows_for(screen, None, "en", "en"), screen)
    return screen


def _rows(screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(screen, None, "en", "en")


def _goto(screen: OperationScreen, field_id: FieldId) -> None:
    """Jumps directly to a field with nothing pending -- used only for
    initial setup in these tests, not to simulate a mid-edit Up/Down (that
    commit path is `move_selection`, exercised explicitly below)."""

    rows = _rows(screen)
    ids = [row.field_id for row in rows]
    screen.selected_field = field_id
    assert field_id in ids
    split_pane.sync_buffer(rows, screen)


def _row(rows: list[split_pane.Row], field_id: FieldId) -> split_pane.Row:
    return next(row for row in rows if row.field_id is field_id)


def test_typing_a_digit_edits_the_buffer_without_committing_until_navigating_away():
    """FR-016."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "1")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert screen.field_buffer == "1"
    assert state.diameter is None  # not yet committed

    split_pane.edit_selected(_rows(screen), screen, "5")
    assert screen.field_buffer == "15"
    assert state.diameter is None  # still not committed

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    assert state.diameter == 15.0


def test_backspace_edits_the_buffer_too():
    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "1")
    split_pane.edit_selected(_rows(screen), screen, "5")
    split_pane.backspace_selected(_rows(screen), screen)
    assert screen.field_buffer == "1"

    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter is None  # still uncommitted

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    assert state.diameter == 1.0


def test_number_row_step_defaults_to_nudge_step():
    """specs/020-turning-feed-per-rotation FR-011/research.md #7: every
    existing NumberRow (drilling, milling, and turning's own diameter/
    depth/length/power/RPM rows) keeps nudging by the shared default
    NUDGE_STEP unless a row explicitly overrides it."""

    screen = _screen()
    row = _row(_rows(screen), FieldId.DIAMETER)
    assert isinstance(row, split_pane.NumberRow)
    assert row.step == split_pane.NUDGE_STEP


def test_left_right_nudges_a_numeric_fields_buffer_without_committing_until_navigating_away():
    """FR-017."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    assert screen.field_buffer == "1"
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter is None  # still uncommitted

    split_pane.nudge_selected(_rows(screen), screen, 1)
    assert screen.field_buffer == "2"

    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert screen.field_buffer == "1"

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    assert state.diameter == split_pane.NUDGE_STEP


def test_nudging_at_or_below_zero_clears_the_buffer_rather_than_going_negative():
    """Contract §4's implementation detail."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert screen.field_buffer == ""

    # Nudging down from unset stays unset (never goes negative).
    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert screen.field_buffer == ""

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter is None


def test_left_right_cycles_a_radio_field_and_commits_it_immediately():
    """Matches the prototype's `cycle_field`: no buffering, no separate
    confirm step -- Left/Right/Space on a radio field commits right away."""

    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    split_pane.nudge_selected(_rows(screen), screen, 1)

    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "imperial"


def test_left_from_an_unset_radio_field_wraps_to_the_last_option():
    """Regression test for a bug a code-review pass on PR #96 found: the
    very first Left/h press on an *unset* radio field (e.g. Material type,
    which starts `None`) landed on the second-to-last option instead of
    wrapping to the last one -- a sentinel index of -1 made Right/l/Space
    correct by coincidence ((-1 + 1) % n == 0, the first option) but broke
    the symmetric case. Right's own correctness is re-verified here too, so
    a future fix can't silently break it while fixing Left."""

    screen = _screen()
    _goto(screen, FieldId.MATERIAL_TYPE)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.material_type is None

    options = [value for value, _ in _row(_rows(screen), FieldId.MATERIAL_TYPE).options]
    assert len(options) >= 2, "need at least two material types for this test to mean anything"

    split_pane.nudge_selected(_rows(screen), screen, -1)  # Left, from unset
    assert state.material_type == options[-1]


def test_right_from_an_unset_radio_field_still_selects_the_first_option():
    screen = _screen()
    _goto(screen, FieldId.MATERIAL_TYPE)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)

    options = [value for value, _ in _row(_rows(screen), FieldId.MATERIAL_TYPE).options]
    split_pane.nudge_selected(_rows(screen), screen, 1)  # Right, from unset
    assert state.material_type == options[0]


def test_radio_cycle_wraps_at_the_boundary_rather_than_clamping():
    """`unit_system` has exactly two options; cycling past either end wraps
    around rather than clamping (matching the prototype's modulo
    arithmetic, unlike a `RadioList`'s own clamped navigation)."""

    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "metric"

    split_pane.nudge_selected(_rows(screen), screen, -1)  # wraps backward past the start
    assert state.unit_system.value == "imperial"

    split_pane.nudge_selected(_rows(screen), screen, 1)  # wraps forward back to the start
    assert state.unit_system.value == "metric"


def test_up_down_always_moves_between_fields_regardless_of_row_type():
    """Up/Down (`move_selection`) is unconditional -- no per-field-type
    dispatch, unlike the retired Tab/Shift-Tab-vs-Up/Down split."""

    screen = _screen()
    rows = _rows(screen)
    ids = [row.field_id for row in rows]
    assert screen.selected_field is FieldId.UNIT_SYSTEM

    split_pane.move_selection(rows, screen, 1, "en")
    assert screen.selected_field == ids[1]

    split_pane.move_selection(_rows(screen), screen, -1, "en")
    assert screen.selected_field is FieldId.UNIT_SYSTEM


def test_move_selection_commits_the_pending_numeric_edit_before_moving_away():
    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "7")

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter == 7.0


def test_selecting_a_field_syncs_the_buffer_to_its_committed_value():
    """Landing on a field shows what's already committed, so a user can
    backspace to edit an existing value rather than only ever overwriting
    blindly."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "7")
    split_pane.move_selection(_rows(screen), screen, 1, "en")  # commits 7.0, moves to DEPTH
    split_pane.move_selection(_rows(screen), screen, -1, "en")  # moves back to DIAMETER
    assert screen.field_buffer == "7"


def test_revisiting_a_field_beyond_four_significant_digits_does_not_corrupt_it():
    """CRITICAL regression test for a round-3 code-review finding on PR
    #96: `sync_buffer` used to reuse `_format` (a lossy, display-only 4
    significant-digit formatter, `.4g`) to populate `field_buffer` too.
    Simply revisiting a field with a value beyond 4 significant digits --
    with no edit at all -- silently rewrote it: 12345 synced to a buffer of
    "1.234e+04", which re-committed as 12340.0 on navigating away again."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "12345")
    split_pane.move_selection(_rows(screen), screen, 1, "en")  # commits 12345.0, moves to DEPTH
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter == 12345.0

    split_pane.move_selection(_rows(screen), screen, -1, "en")  # back to DIAMETER, no edit
    assert screen.field_buffer == "12345"
    split_pane.move_selection(_rows(screen), screen, 1, "en")  # leave again, still unedited
    assert state.diameter == 12345.0  # must not have silently become 12340.0


def test_nudging_a_field_beyond_four_significant_digits_adjusts_by_exactly_one_step():
    """The same bug also corrupted `nudge_selected`: nudging Right added
    `NUDGE_STEP` to whatever the (previously lossy) buffer parsed as, so
    nudging from a revisited 12345 landed on 12341, not 12346."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "12345")
    split_pane.move_selection(_rows(screen), screen, 1, "en")  # commits 12345.0
    split_pane.move_selection(_rows(screen), screen, -1, "en")  # back to DIAMETER

    split_pane.nudge_selected(_rows(screen), screen, 1)
    assert screen.field_buffer == "12346"
