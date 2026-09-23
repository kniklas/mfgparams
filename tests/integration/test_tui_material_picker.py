"""Integration test: the metal Material selection window's open/navigate/
confirm/cancel plumbing, plus User Story 1's common-name search
(specs/023-material-selector-dialog, tasks.md T019/T024).

Drives the real, single persistent `Application` headlessly
(`_tui_test_support.run_headless`), the same technique
`test_tui_navigation.py` uses -- this dialog is a `Float`/key-binding wiring
concern, not something `rows_for`'s row callbacks alone can exercise the way
`test_tui_drilling.py` tests the rest of the Drilling screen.

Every candidate here comes from the bundled registry, which does not yet
populate `material_number`/`short_notation` (tasks.md T035 is a separate,
later data-entry task) -- every row in these tests exercises FR-010's
blank-cell case incidentally, by virtue of the bundled data's current state.

Only `Up`/`Down` (not the `j`/`k` aliases the rest of the pane also accepts)
are bound inside this dialog, since it accepts free-text search input (User
Story 1 onward) that must not be able to type the letters "j"/"k" and have
them silently swallowed as navigation instead -- so key sequences below use
the raw ANSI arrow escapes rather than this repo's usual `j`/`k` convention.

The first several scenarios below predate User Story 1's search behavior
being wired up and so operate against the full, unfiltered 6-material
bundled metal list; the later ones exercise `query_common`'s live filtering.

``run_headless`` requires ``target`` (the app) to actually call
``event.app.exit()`` by the end of the key script -- it is not enough for
the interesting state to merely settle mid-script. Every scenario below
therefore sends its own "interesting" key prefix, then a generous, over-
provided trailing Escape sequence (``_TRAILING_CLOSE``) to unwind however
much is currently open (the dialog if still open, then the operation
window, then the still-expanded Machining tree) and finally exit from the
bare bar -- mirroring `test_tui_navigation.py`'s own trailing-Escape
convention. Extra Escapes beyond what a given scenario actually needs are
harmless: once the app exits, `run_headless`'s batch loop stops sending
further batches. Snapshots are indexed at the fixed position right after
the interesting prefix (`len(prefix)`), not `[-1]`, since the trailing
Escapes generate further snapshots of their own.
"""

from __future__ import annotations

import pytest
from _tui_test_support import run_headless

import mfgparams.console.tui.app as app_mod
from mfgparams.console.i18n import get_locale
from mfgparams.i18n import get_raw_locale
from mfgparams.registry_config import clear_cache


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    """Mirrors `test_tui_materials_config.py`'s own fixture: the registry
    snapshot is `functools.cache`d by config path (research.md #8), so
    tests using a custom `--materials-config` file clear it before/after."""

    clear_cache()
    yield
    clear_cache()


_UP = "\x1b[A"
_DOWN = "\x1b[B"
_ENTER = "\r"
_ESCAPE = "\x1b"

#: Opens Drilling (bar mnemonic "m" -> Machining tree, "d" -> Drilling leaf,
#: matching `test_tui_navigation.py`'s own convention), moves down to
#: Material Type ("j" twice -- outside the dialog, so the ordinary pane
#: j/k aliases are safe here), selects "metal" (first option, from unset),
#: then moves down once more onto the Material row itself.
_REACH_METAL_MATERIAL_ROW = ["m", "d", "j", "j", " ", "j"]

#: Same as above but opens Turning instead (tree row 2, reached via "j","j"
#: from Milling, matching `test_tui_navigation.py`'s own convention for
#: Turning) -- `turning.py`'s `rows_for` uses the identical field order
#: (unit system, mode, material type, material, tool), so the same
#: Down/Space/Down suffix reaches its Material row too. Used by
#: `test_the_dialog_behaves_identically_from_turning` (FR-012/SC-004): a
#: second operation's `TurningSessionState` (not `DrillingSessionState`)
#: proves the trigger/binding logic is genuinely operation-agnostic, not
#: incidentally Drilling-only.
_REACH_METAL_MATERIAL_ROW_VIA_TURNING = ["m", "j", "j", _ENTER, "j", "j", " ", "j"]

#: Same idea again but opens Milling instead (tree row 0, the default --
#: "m" then Enter directly, matching `test_tui_navigation.py`'s own "m",
#: "\r" -> Milling convention). Unlike Drilling/Turning, `milling.py`'s
#: `rows_for` inserts a `FieldId.SUB_OPERATION` row between Mode and
#: Material type, so reaching Material type from Unit system takes three
#: Downs here, not two (tasks.md T045 -- closes the one operation FR-012/
#: SC-004's "identical across drilling, turning, and milling" claim had no
#: automated coverage for).
_REACH_METAL_MATERIAL_ROW_VIA_MILLING = ["m", _ENTER, "j", "j", "j", " ", "j"]

#: Safely over-provided: closing the dialog (if open) + the operation + the
#: still-expanded Machining tree + exiting from the bare bar is at most 4
#: Escapes; extras are never sent once the app has exited (module docstring).
_TRAILING_CLOSE = [_ESCAPE] * 5


def _run_and_snapshot(interesting: list[str], materials_config_path: str | None = None) -> tuple:
    """Runs ``interesting`` followed by :data:`_TRAILING_CLOSE`, returning
    the snapshot captured immediately after ``interesting`` settles:
    ``(dialog_open, highlighted_name, session_material, query_common)``."""

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(materials_config_path, locale, display_locale)
        holder["ui"] = ui
        holder["view"] = view
        app.run()

    snapshots: list[tuple] = []

    def on_batch() -> None:
        ui = holder.get("ui")
        view = holder.get("view")
        if ui is None:
            return
        picker = view.material_picker
        op = ui.open_operation
        snapshots.append(
            (
                picker is not None,
                picker.highlighted_name if picker is not None else None,
                op.session_state.material if op is not None else None,
                picker.query_common if picker is not None else None,
            )
        )

    run_headless(target, interesting + _TRAILING_CLOSE, on_batch=on_batch)
    return snapshots[len(interesting)]


def test_left_right_space_still_cycle_the_metal_material_row_directly():
    """Direct user feedback: Enter opening the detailed picker MUST NOT
    replace the ordinary one-by-one Left/Right/Space cycle every other
    radio row already has -- both paths stay available side by side."""

    # "l" (Right) selects the first option from unset, matching every other
    # radio row's own nudge_selected behavior; no dialog is ever opened.
    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + ["l"])
    assert snapshot == (False, None, "Mild Steel", None)

    # "l" again cycles forward to the next material.
    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + ["l", "l"])
    assert snapshot == (False, None, "Stainless Steel", None)

    # "h" (Left) cycles backward.
    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + ["l", "l", "h"])
    assert snapshot == (False, None, "Mild Steel", None)


def test_enter_on_the_metal_material_row_opens_the_dialog():
    """FR-001. Nothing was previously selected, so FR-011/Clarification 2
    starts with no row highlighted."""

    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + [_ENTER])

    assert snapshot == (True, None, None, "")


def test_down_moves_the_highlight_onto_the_first_candidate():
    """FR-005, against the full unfiltered list (bundled order: Mild Steel
    first)."""

    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + [_ENTER, _DOWN])

    assert snapshot == (True, "Mild Steel", None, "")


def test_up_and_down_navigate_the_full_list_without_wrapping_at_the_top():
    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + [_ENTER, _DOWN, _DOWN, _UP])

    assert snapshot == (True, "Mild Steel", None, "")


def test_escape_closes_the_dialog_without_changing_the_material():
    """FR-009."""

    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + [_ENTER, _DOWN, _ESCAPE])

    assert snapshot == (False, None, None, None)


def test_enter_confirms_the_highlighted_candidate_and_closes():
    """FR-007. Down twice from the (initially unhighlighted) full list
    lands on the second bundled metal material, Stainless Steel."""

    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + [_ENTER, _DOWN, _DOWN, _ENTER])

    assert snapshot == (False, None, "Stainless Steel", None)


def test_enter_with_nothing_highlighted_is_a_no_op():
    """FR-008: the dialog stays open. Reachable here without an empty
    candidate list -- the very first open (no prior selection) starts with
    nothing highlighted at all (FR-011), the same "no candidate highlighted"
    condition FR-008 describes; pressing Enter immediately must not confirm
    an arbitrary/first candidate on the user's behalf."""

    snapshot = _run_and_snapshot(_REACH_METAL_MATERIAL_ROW + [_ENTER, _ENTER])

    assert snapshot == (True, None, None, "")


def test_reopening_pre_highlights_the_previously_selected_material():
    """FR-011, Clarification 2: reopening after a confirmed selection starts
    with that material's row already highlighted, not the top of the list."""

    interesting = _REACH_METAL_MATERIAL_ROW + [
        _ENTER,
        _DOWN,
        _DOWN,
        _ENTER,  # confirms Stainless Steel
        _ENTER,  # reopens
    ]

    snapshot = _run_and_snapshot(interesting)

    assert snapshot == (True, "Stainless Steel", "Stainless Steel", "")


def test_typing_narrows_the_list_live_and_navigation_operates_on_the_filtered_results():
    """User Story 1 (tasks.md T024): "steel" matches Mild Steel and
    Stainless Steel only; Down/Enter then operate on that filtered pair,
    not the full six-material list."""

    interesting = _REACH_METAL_MATERIAL_ROW + [_ENTER, "steel", _DOWN, _ENTER]

    snapshot = _run_and_snapshot(interesting)

    assert snapshot == (False, None, "Stainless Steel", None)


def test_a_non_matching_query_clears_the_highlight_and_enter_is_a_no_op():
    interesting = _REACH_METAL_MATERIAL_ROW + [_ENTER, "zzz", _ENTER]

    snapshot = _run_and_snapshot(interesting)

    assert snapshot == (True, None, None, "zzz")


def test_backspace_widens_the_filtered_list_again():
    interesting = _REACH_METAL_MATERIAL_ROW + [_ENTER, "zzz", "\x7f\x7f\x7f"]

    snapshot = _run_and_snapshot(interesting)

    assert snapshot == (True, "Mild Steel", None, "")


def _write_material_number_config(tmp_path) -> str:
    """Two new metal materials with distinct `material_number`s/
    `short_notation`s, added alongside the bundled defaults (which have
    neither yet -- tasks.md T035 is a separate data-entry task)."""

    path = tmp_path / "config.toml"
    path.write_text("""
[[materials]]
name = "Chromoly Steel"
material_type = "metal"
reference_cutting_speed = 20.0
reference_feed_per_rev = 0.18
specific_cutting_force = 2100.0
material_number = "1.7225"
short_notation = "42CrMo4+N"

[[materials]]
name = "Tool Steel"
material_type = "metal"
reference_cutting_speed = 15.0
reference_feed_per_rev = 0.12
specific_cutting_force = 2600.0
material_number = "1.2080"
short_notation = "100Cr6"
""")
    return str(path)


def test_switching_to_the_material_number_column_filters_by_number_and_excludes_blanks(tmp_path):
    """User Story 2 (tasks.md T031). "1.72" matches only Chromoly Steel --
    Tool Steel's "1.2080" doesn't contain it, and every bundled material's
    blank `material_number` is excluded outright (FR-010) the moment this
    column's query is non-empty."""

    config_path = _write_material_number_config(tmp_path)
    interesting = _REACH_METAL_MATERIAL_ROW + [_ENTER, "\t", "1.72", _ENTER]

    snapshot = _run_and_snapshot(interesting, materials_config_path=config_path)

    assert snapshot == (False, None, "Chromoly Steel", None)


def test_shift_tab_returns_to_the_common_name_column_preserving_its_text(tmp_path):
    """FR-006: switching columns must not lose the other columns' text."""

    config_path = _write_material_number_config(tmp_path)
    interesting = _REACH_METAL_MATERIAL_ROW + [
        _ENTER,
        "steel",  # typed into the common-name column (active by default)
        "\t",  # switch right to the material-number column
        "1.72",
        "\x1b[Z",  # shift-tab: switch back left to the common-name column
    ]

    snapshot = _run_and_snapshot(interesting, materials_config_path=config_path)

    # query_common still holds "steel", proving it survived the round trip
    # through the material-number column rather than being cleared.
    assert snapshot == (True, "Chromoly Steel", None, "steel")


def test_switching_to_the_shortened_designation_column_filters_by_designation(tmp_path):
    """User Story 3 (tasks.md T034). Two Tabs from the default common-name
    column reach the shortened-designation column (cycling already works
    from User Story 2); "42crmo4" matches only Chromoly Steel."""

    config_path = _write_material_number_config(tmp_path)
    interesting = _REACH_METAL_MATERIAL_ROW + [_ENTER, "\t", "\t", "42crmo4", _ENTER]

    snapshot = _run_and_snapshot(interesting, materials_config_path=config_path)

    assert snapshot == (False, None, "Chromoly Steel", None)


def test_typing_into_all_three_columns_requires_matching_all_three(tmp_path):
    """spec.md User Story 3 Acceptance Scenario 2: only a material matching
    every non-empty query across all three columns simultaneously remains."""

    config_path = _write_material_number_config(tmp_path)
    interesting = _REACH_METAL_MATERIAL_ROW + [
        _ENTER,
        "steel",  # common name: matches Chromoly Steel and Tool Steel
        "\t",
        "1.72",  # material number: narrows to Chromoly Steel alone
        "\t",
        "100cr6",  # shortened designation: matches only Tool Steel instead
        _ENTER,  # nothing satisfies all three at once -> no-op, dialog stays open
    ]

    snapshot = _run_and_snapshot(interesting, materials_config_path=config_path)

    assert snapshot == (True, None, None, "steel")


def test_the_dialog_behaves_identically_from_turning():
    """FR-012/SC-004: opening the dialog from Turning -- a different
    operation with its own `TurningSessionState`, not `DrillingSessionState`
    -- behaves identically (open with no highlight, search narrows, Enter
    confirms and closes), proving the trigger/binding logic in `app.py` is
    genuinely operation-agnostic rather than incidentally Drilling-only.
    Closes a gap the `/speckit-analyze` pass on this feature flagged: every
    other test in this file exercises Drilling exclusively."""

    interesting = _REACH_METAL_MATERIAL_ROW_VIA_TURNING + [_ENTER, "steel", _DOWN, _ENTER]

    snapshot = _run_and_snapshot(interesting)

    assert snapshot == (False, None, "Stainless Steel", None)


def test_the_dialog_behaves_identically_from_milling():
    """FR-012/SC-004 (tasks.md T045): opening the dialog from Milling -- the
    third and last operation, with its own `MillingSessionState` and a row
    order that differs from Drilling/Turning (an extra `SUB_OPERATION` row
    before Material type) -- behaves identically. Closes the gap the
    `/speckit-converge` pass on this feature flagged: only Drilling and
    Turning had automated cross-operation coverage before this test."""

    interesting = _REACH_METAL_MATERIAL_ROW_VIA_MILLING + [_ENTER, "steel", _DOWN, _ENTER]

    snapshot = _run_and_snapshot(interesting)

    assert snapshot == (False, None, "Stainless Steel", None)
