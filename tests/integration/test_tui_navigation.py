"""Integration test: headless navigation shell -- menu bar + Machining tree
(018-tui-splitpane-redesign, spec.md User Story 1, tasks.md T009).

017's `test_tui_app_run.py` drove `NavigationState` push/pop directly, which
no longer exists in that shape (data-model.md's `SessionUI` replaces it);
this drives the real, single persistent `Application` (`app.build_app`)
headlessly instead, using `_tui_test_support.run_headless`'s `on_batch` hook
(research.md #2) to inspect `SessionUI`/`_ViewState` between keystrokes.

Note: the bar's *first* entry is Exit (contract's fixed order), so a bare
Enter at startup opens its confirmation dialog rather than exiting outright
(revision, per direct user feedback: Exit now asks "are you sure?" instead
of exiting immediately) -- every scenario below reaches Machining via its
mnemonic jump key ("m", `app.py`'s per-character bar bindings) rather than
arrow-then-Enter, to avoid that dialog entirely. Pressing "m" a second time in a
row does *not* re-toggle Machining from the bar -- the first "m" already
moved focus onto the tree, so a second "m" is read as the tree's own
mnemonic for Milling instead (contract §4's per-level mnemonic
namespaces); getting back to the bar first needs an explicit Escape.

`run_headless`'s `on_batch` fires once *before* each send (capturing the
state settled by every prior batch -- including one initial call before
anything has been sent at all) plus once more after the final batch
settles. So N key_batches yield N+1 snapshots, and `snapshots[i]` is the
state after exactly `i` batches have been applied (`snapshots[0]` is the
pristine startup state).

Rewritten again (revision, tasks.md T043/Phase 8): Drilling's tree-level
tool-selection shortcut is retired (FR-003) -- both Milling and Drilling
are now flat leaves that open their floating window directly on Enter, no
intermediate toggle step. Snapshots drop `tree.drilling_expanded` (the
field no longer exists); `view.body_mode` no longer takes "drilling"/
"milling" values at all (the floating window is independent of it,
research.md #3), so which operation (if any) is open is read from
`ui.open_operation.operation` directly instead.
"""

from __future__ import annotations

from _tui_test_support import run_headless

import mfgparams.console.tui.app as app_mod
from mfgparams.console.i18n import get_locale
from mfgparams.i18n import get_raw_locale


def _drive(key_batches: list[str]) -> list[tuple]:
    """Runs the real app headlessly, returning one snapshot per settled
    batch: ``(body_mode, tree.expanded, open_operation_kind,
    open_operation is not None)`` -- ``open_operation_kind`` is
    ``ui.open_operation.operation`` (``"drilling"``/``"milling"``) or
    ``None``."""

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["ui"] = ui
        holder["view"] = view
        app.run()

    snapshots: list[tuple] = []

    def on_batch() -> None:
        ui = holder.get("ui")
        view = holder.get("view")
        if ui is None:
            return
        snapshots.append(
            (
                view.body_mode,
                ui.tree.expanded,
                ui.open_operation.operation if ui.open_operation else None,
                ui.open_operation is not None,
            )
        )

    run_headless(target, key_batches, on_batch=on_batch)
    return snapshots


def test_initial_state_shows_nothing_open():
    """Acceptance Scenario 1: the bar is visible on launch, with nothing
    else selected yet -- escape at the root (nothing open) exits."""

    snapshots = _drive(["\x1b"])
    assert snapshots[0] == (None, False, None, False)


def test_selecting_machining_expands_the_tree():
    """Acceptance Scenario 2: the "m" mnemonic jumps to and activates
    Machining directly from the bar."""

    snapshots = _drive(["m", "\x1b", "\x1b"])
    assert snapshots[1] == ("tree", True, None, False)


def test_selecting_drilling_opens_its_floating_window_directly():
    """Acceptance Scenario 3, revised: Drilling is a flat leaf, exactly
    like Milling -- selecting it opens its floating window on Enter, no
    intermediate tree-level toggle."""

    snapshots = _drive(["m", "j", "\r", "\x1b", "\x1b", "\x1b"])
    # m: expand Machining, focus tree (row 0 = Milling); j: move to
    # Drilling (row 1); Enter: opens Drilling directly.
    assert any(s[2] == "drilling" and s[3] is True for s in snapshots)


def test_collapsing_machining_returns_to_its_collapsed_state():
    """Acceptance Scenario 4. Closing the dropdown is now Escape/Up's job
    (`test_escaping_an_open_dropdown_closes_it`) rather than re-selecting
    Machining from the bar: the very first "m"/Down press always focuses
    the tree (there is no longer a way to be back on the bar with the
    tree still counted as expanded -- see `test_reexpanding_machining_
    after_closing_it_needs_only_one_press`), so a *second* bar-level "m"
    can never encounter it already expanded to toggle closed."""

    snapshots = _drive(["m", "\x1b", "\x1b"])
    # m: expand, focus tree; escape: closes the dropdown outright (both
    # body_mode and tree.expanded); final escape: nothing open -> exit
    # (fast enough that the trailing post-batch snapshot isn't reliably
    # captured, so check right after the close instead, at index 2).
    assert snapshots[2] == (None, False, None, False)


def test_reexpanding_machining_after_closing_it_needs_only_one_press():
    """Regression test for a reported bug: after closing the Machining
    dropdown (Escape/Up), `tree.expanded` must go back to `False` in
    lockstep with the dropdown no longer being shown -- not left `True`
    from before closing it, which made the *next* "m"/Down press on the
    bar silently toggle it back to `False` (already invisible, so nothing
    appeared to change) instead of reopening it, requiring a second press
    to actually see the dropdown again."""

    snapshots = _drive(["m", "\x1b", "m", "\x1b", "\x1b"])
    # m: expand, focus tree; escape: closes it (tree.expanded is now False,
    # matching the dropdown's own visibility); m: a single press reopens
    # it -- this is exactly the case that used to need two presses.
    assert snapshots[3] == ("tree", True, None, False)


def test_selecting_a_leaf_opens_the_corresponding_operation_screen():
    """Independent Test: a leaf selection opens the corresponding
    operation screen, independent of what that screen's panes contain."""

    snapshots = _drive(["m", "\r", "\x1b", "\x1b", "\x1b"])  # Machining, then Milling (row 0)
    assert any(s[2] == "milling" and s[3] is True for s in snapshots)


def test_selecting_turning_opens_its_floating_window_directly():
    """specs/019-turning-calculations: Turning is a third flat leaf, below
    Milling (row 0) and Drilling (row 1) -- two "j" presses reach it,
    exercising the real keyboard-driven Application wiring end-to-end
    (not just calling `_open_turning`/`rows_for` directly, which
    test_tui_turning.py already covers)."""

    snapshots = _drive(["m", "j", "j", "\r", "\x1b", "\x1b", "\x1b"])
    assert any(s[2] == "turning" and s[3] is True for s in snapshots)


def test_drilling_opens_on_unit_system_with_no_tree_shortcut_specific_field():
    """Drilling now opens with the same default `selected_field` as
    Milling (`UNIT_SYSTEM`) -- there is no more tree-shortcut-specific
    field to land on (FR-003 retired)."""

    from mfgparams.console.tui.app import FieldId

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["ui"] = ui
        app.run()

    fields_seen = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None or ui.open_operation.operation != "drilling":
            return
        fields_seen.append(ui.open_operation.selected_field)

    run_headless(
        target,
        ["m", "j", "\r", "\x1b", "\x1b", "\x1b"],
        on_batch=on_batch,
    )

    assert fields_seen, "Drilling was never open while inspected"
    assert fields_seen[0] is FieldId.UNIT_SYSTEM


def test_reopening_drilling_after_a_full_close_reuses_the_same_session_state():
    """FR-012's carryover guarantee, re-verified against the current
    interaction model: a full close (`ui.open_operation = None`, e.g. via
    Escape from the operation pane) legitimately creates a *new*
    `OperationScreen` wrapper the next time Drilling is opened --
    `_open_drilling` always creates a fresh one now (a later code-review
    pass on PR #96 found and removed a "reuse the existing OperationScreen
    if Drilling is already open" branch that was already dead code by this
    point, since the only caller requires the tree to have focus, which by
    construction means no operation is open yet). What must survive a full
    close/reopen cycle is the underlying `DrillingSessionState`
    (`SessionUI.drilling_state`), so previously-entered values are still
    there -- verified here by its identity, not the wrapper's."""

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["ui"] = ui
        app.run()

    session_states_seen = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None or ui.open_operation.operation != "drilling":
            return
        session_states_seen.append(ui.open_operation.session_state)

    run_headless(
        target,
        [
            "m",  # expand Machining, focus tree
            "j",  # move to Drilling (row 1)
            "\r",  # open Drilling
            "\x1b",  # closes Drilling; focus returns to the still-open tree
            "\x1b",  # closes the tree; back to the bare bar
            "m",  # re-expand Machining, focus tree again -- a single press
            # suffices (the reported bug this depends on being fixed:
            # `test_reexpanding_machining_after_closing_it_needs_only_one_
            # press`)
            "j",  # move to Drilling (row 1) again
            "\r",  # reopen Drilling
            "\x1b",  # closes Drilling; focus returns to the tree
            "\x1b",  # closes the tree; back to the bare bar
            "\x1b",  # nothing open -> exit
        ],
        on_batch=on_batch,
    )

    assert session_states_seen, "Drilling was never open while inspected"
    ui = holder["ui"]
    assert all(s is ui.drilling_state for s in session_states_seen)


def test_drilling_tool_selection_is_always_present_in_the_left_pane():
    """018-tui-splitpane-redesign tasks.md T018/T043 -- contract §2's own
    invariant, checked at the exact granularity it's stated at: FR-005's
    tool-selection field (not just "some screen is open") must be present
    and reachable in the left pane's row list whenever Drilling is open --
    it was never exclusively tree-resident in the first place.

    Revision: "collapse the tree while Drilling is still open" is no
    longer a reachable key sequence at all (escaping the operation pane
    now closes the operation outright before the bar -- and so "m" -- is
    ever reachable again; see `test_reopening_drilling_preserves_its_
    state_across_a_tree_collapse`), so this checks the field list at the
    point that matters: while the screen is actually open."""

    from mfgparams.console.tui.app import FieldId
    from mfgparams.console.tui.screens.drilling import rows_for

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["ui"] = ui
        holder["view"] = view
        app.run()

    field_id_sets = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None or ui.open_operation.operation != "drilling":
            return
        rows = rows_for(ui.open_operation, None, locale, display_locale)
        field_id_sets.append({row.field_id for row in rows})

    run_headless(
        target,
        [
            "m",  # expand Machining, focus tree
            "j",  # Drilling row
            "\r",  # opens Drilling directly
            "\x1b",  # closes Drilling; focus returns to the tree
            "\x1b",  # closes the tree; back to the bare bar
            "\x1b",  # nothing open -> exit
        ],
        on_batch=on_batch,
    )

    assert field_id_sets, "Drilling was never open while inspected"
    assert all(
        FieldId.TOOL in ids for ids in field_id_sets
    ), "tool selection dropped out of the left pane's row list while Drilling was open"


def test_escaping_an_open_dropdown_closes_it():
    """Per direct user feedback: Escape from an open floating dropdown
    (Machining's tree) must close it, not just move focus back to the bar
    while leaving it visibly open underneath. `tree.expanded` closes right
    along with it (a later revision, also per user feedback -- a reported
    "press Down twice to expand Machining" bug traced to `tree.expanded`
    being left `True` here even though the dropdown was no longer shown)."""

    snapshots = _drive(["m", "\x1b", "\x1b"])
    # index 2 = state after "m" (index 1) and the first escape have both
    # settled -- the escape that returns focus from the tree to the bar.
    assert snapshots[2][0] is None  # body_mode: the dropdown is gone
    assert snapshots[2][1] is False  # tree.expanded closes with it


def test_up_at_the_top_of_the_tree_closes_it_too():
    """The same "Escape closes the dropdown (and `tree.expanded` with it)"
    fix, reached via Up instead -- Up at the first row already returns
    focus to the bar (prior revision); now it also closes the tree,
    matching Escape exactly."""

    snapshots = _drive(["m", "k", "\x1b"])
    assert snapshots[2][0] is None
    assert snapshots[2][1] is False


def test_escaping_an_open_configuration_panel_closes_it():
    """The same fix, for a single-block panel (no navigable rows) rather
    than the tree -- Configuration's own bar mnemonic is "c"."""

    snapshots = _drive(["c", "\x1b", "\x1b"])
    assert snapshots[2][0] is None


def test_escaping_the_operation_pane_closes_it_and_reveals_the_tree_underneath():
    """Per direct user feedback ("each time user exits floating window it
    should be erased/removed", and "when escaping from machining/drilling
    cursor should be back to sub-menu"): a single Escape from the operation
    pane now closes the operation window outright, landing back on the
    still-expanded Machining tree -- focused, ready to navigate again, not
    the bare bar (Acceptance Scenario 5: "land back at the menu bar/tree,
    not a blank body") -- not lingering, unfocused-but-still-open,
    requiring a second Escape the way it did before this fix. A *second*
    Escape from there closes the tree itself and reaches the bar."""

    snapshots = _drive(["m", "\r", "\x1b", "\x1b", "\x1b"])
    # m: expand Machining, focus tree (row 0 = Milling); \r: open Milling;
    # \x1b: closes Milling and reveals the tree (still expanded) again,
    # focused; \x1b: closes the tree itself, back to the bare bar.
    after_first_escape = snapshots[3]
    assert after_first_escape == ("tree", True, None, False)
    after_second_escape = snapshots[4]
    assert after_second_escape == (None, False, None, False)


def _drive_confirm(key_batches: list[str]) -> list[tuple[bool, str]]:
    """Like `_drive`, but for the Exit confirmation dialog's own state
    (`view.confirming_exit`, `view.confirm_selected`) -- not part of
    `_drive`'s own snapshot shape, which every other test in this module
    already depends on."""

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["view"] = view
        app.run()

    snapshots: list[tuple[bool, str]] = []

    def on_batch() -> None:
        view = holder.get("view")
        if view is None:
            return
        snapshots.append((view.confirming_exit, view.confirm_selected))

    run_headless(target, key_batches, on_batch=on_batch)
    return snapshots


def test_selecting_exit_shows_a_confirmation_dialog_instead_of_exiting_immediately():
    """Per direct user feedback ("when exit is selected ask user"): a
    single Enter/Down on the bar's Exit entry no longer exits outright --
    it opens a floating Yes/No confirmation dialog instead, defaulting to
    "No" so a reflexive extra keypress can't itself exit."""

    snapshots = _drive_confirm(["\r", "n", "\x1b"])
    # index 1: after the bare Enter (bar_selected defaults to Exit, the
    # bar's first entry) -- the dialog is open, defaulting to "no".
    assert snapshots[1] == (True, "no")
    # index 2: "n" declines -- the dialog closes without exiting.
    assert snapshots[2] == (False, "no")


def test_confirming_exit_with_the_default_no_does_not_exit():
    """Pressing Enter again while "No" is still highlighted (the default)
    must decline, not exit -- the whole point of defaulting to "No"."""

    snapshots = _drive_confirm(["\r", "\r", "\x1b"])
    assert snapshots[2] == (False, "no")


def test_toggling_to_yes_and_confirming_exits():
    """Left/Right toggle between Yes/No; confirming "Yes" actually exits."""

    run_headless(lambda: app_mod.run(materials_config_path=None), ["\r", "l", "\r"])
    # run_headless's own assertion (the thread completed) is the check:
    # the app exited on its own after confirming "Yes".


def test_pressing_y_exits_the_confirmation_dialog_immediately():
    """ "y" is a direct shortcut for confirming exit, without needing to
    toggle to "Yes" and press Enter separately."""

    run_headless(lambda: app_mod.run(materials_config_path=None), ["\r", "y"])
