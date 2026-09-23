"""Integration test: `tui/app.py`'s `run()` end-to-end -- the actual entry
point every other test in this suite exercises one layer below, by calling
`build_app`/screen functions directly (018-tui-splitpane-redesign, tasks.md
T033). Drives the real menu bar -> Machining tree -> Drilling (a flat
leaf) -> a completed calculation -> back to the menu bar -> exit, through
the real, single persistent `Application`, not a chain of dialogs.

Revision note (rebuilt a second time to match the pre-plan prototype
exactly, retiring the Phase-8/Tab-and-`RadioList`-style design this file
previously exercised -- see `split_pane.py`'s module docstring): Drilling's
tree-level tool-selection shortcut is retired (FR-003) -- it now opens
directly, landing on Unit system (like Milling). A radio field is always a
single `Label: value` line, never an expanded option list, so Up/Down
(`j`/`k`) always move field-to-field regardless of type -- there is no Tab
binding any more. Left/Right/Space (`h`/`l`/Space) cycle a radio field's
value with wraparound, committing it immediately; a numeric field's typed
text lives in `field_buffer` only and commits to `session_state` when the
user navigates away from it (Up/Down), not on every keystroke and not on
Escape.

Revision note (specs/023-material-selector-dialog): once Material type is
"metal", the Material row also opens a dedicated selection window on
Enter, alongside its existing Left/Right/Space cycling (both stay
available, per direct user feedback -- Enter does not replace the cycle).
This file exercises the Enter/dialog path below purely as one more scripted
route to a committed material, not because Left/Right/Space stopped
working; see `test_tui_material_picker.py` for a direct test of the cycle
still working on this row. The raw ANSI Down arrow (`\x1b[B`, not `j`,
since the dialog accepts free-text search input that must not swallow the
letter "j") highlights the first candidate; Enter confirms and closes it.
"""

from __future__ import annotations

from _tui_test_support import run_headless

from mfgparams.console.tui.app import run

_OPEN_DRILLING_COMPLETE_AND_EXIT = [
    "m",  # bar mnemonic: Machining -- expands the tree, focuses it
    "j",  # tree: Milling -> Drilling
    "\r",  # opens Drilling directly, selected on Unit system
    "j",
    "j",  # Down twice: Unit system -> Mode -> Material type
    "l",  # cycles Material type to its first option ("metal"), committing
    # immediately (no separate confirm step for radio fields)
    "j",  # Down to Material (now present, since Material type is set)
    "\r",  # opens the metal material selection window (023-material-selector-dialog)
    "\x1b[B",  # highlights the first candidate ("Mild Steel")
    "\r",  # confirms it, closing the window
    "j",  # Down to Tool
    "l",  # cycles Tool to its first option ("HSS"), committing
    "j",  # Down to Diameter
    "10",  # instant-edit buffer (FR-016) -- not yet committed
    "j",  # Down to Depth -- commits Diameter (10) on navigating away
    "20",
    "j",  # Down to Available power (optional) -- commits Depth (20)
    "\x1b",  # focus back to the bar; the operation stays open (FR-005a)
    "\x1b",  # closes the operation, back at the menu bar/tree
    "\x1b",  # nothing open -> exit
]


def test_full_session_completes_one_drilling_calculation_then_exits(monkeypatch):
    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    run_headless(lambda: run(materials_config_path=None), _OPEN_DRILLING_COMPLETE_AND_EXIT)
    # run_headless's own assertion (the thread completed) is the real check:
    # `run()` returned on its own after the final Escape, rather than
    # hanging or raising.


def test_changing_an_input_recomputes_without_leaving_the_screen(monkeypatch):
    """Acceptance Scenario 4 (User Story 3): the user can run another
    calculation from the same screen -- editing an already-complete
    screen's input, not a return-to-menu round trip."""

    from mfgparams.console.i18n import get_locale
    from mfgparams.console.tui import app as app_mod
    from mfgparams.i18n import get_raw_locale

    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    holder: dict = {}

    def target() -> None:
        application, ui, view = app_mod.build_app(None, get_locale(), get_raw_locale())
        holder["ui"] = ui
        application.run()

    results = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None:
            return
        results.append(ui.open_operation.last_result)

    run_headless(
        target,
        # `[:-3]` stops right after landing on Available power (the last
        # navigation step before the three closing Escapes). "k","k" moves
        # back up to Diameter, re-syncing its buffer to the committed "10";
        # appending "0" (buffer becomes "100" -- still a valid diameter,
        # unlike e.g. "105", which exceeds HSS/Mild Steel's 100mm maximum
        # and would make `calculate()` return an error result instead of a
        # comparable `spindle_speed_rpm`) and then navigating away ("j", to
        # Depth) commits a distinct diameter and forces a fresh
        # `calculate()` call, without ever leaving the operation screen.
        _OPEN_DRILLING_COMPLETE_AND_EXIT[:-3] + ["k", "k", "0", "j", "\x1b", "\x1b", "\x1b"],
        on_batch=on_batch,
    )
    # A distinct diameter must produce a distinct (freshly computed, not
    # stale-cached) result once the screen re-settles as complete again.
    # `>= 2` -- not `>= 1`, which a single stale cached value would also
    # satisfy -- is the actual claim: diameter 10 and diameter 100 must
    # have produced two different `spindle_speed_rpm` values between them,
    # proving the second edit was genuinely recomputed rather than served
    # from a cache still keyed on the pre-edit diameter.
    non_none = [r for r in results if r is not None]
    assert non_none
    assert len({r.spindle_speed_rpm for r in non_none if r.error is None}) >= 2


def test_toggling_milling_sub_operation_twice_correctly_alternates(monkeypatch):
    """Regression test for a bug a round-2 code-review pass on PR #96 found
    in `app.py`'s `_current_pane_rows()` memoization cache (added to fix a
    round-1 performance finding): the cache's original key snapshotted
    `session_state`'s field *values*, not the object's *identity*. Since a
    fresh `MillingSessionState` for either sub-operation starts with
    identical default field values, switching from End Milling to Face
    Milling (which reassigns `screen.session_state` to a *different*
    object, `milling.py`'s `_set_sub_operation`, while `op.selected_field`
    stays on Sub-operation throughout) didn't change the cache key, so the
    left pane's very next render reused a stale, pre-switch row list --
    whose Sub-operation row still reported `value="end_milling"`. Pressing
    Right a second time then read that stale value, not the real current
    selection, and cycled to "face_milling" *again* instead of correctly
    alternating back to "end_milling" -- silently getting stuck on Face
    Milling no matter how many more times the field is cycled."""

    from mfgparams.console.i18n import get_locale
    from mfgparams.console.tui import app as app_mod
    from mfgparams.i18n import get_raw_locale
    from mfgparams.models import MillingSubOperation

    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    holder: dict = {}

    def target() -> None:
        application, ui, view = app_mod.build_app(None, get_locale(), get_raw_locale())
        holder["ui"] = ui
        application.run()

    states_after_each_batch = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None:
            return
        states_after_each_batch.append(ui.open_operation.session_state)

    run_headless(
        target,
        [
            "m",  # expand Machining, focus tree (row 0 = Milling)
            "\r",  # opens Milling directly, selected on Unit system
            "j",  # Down to Mode
            "j",  # Down to Sub-operation
            "l",  # cycles End Milling -> Face Milling, swapping session_state
            "l",  # cycles again, staying on the same field the whole time --
            # correctly alternates back to End Milling only if the row
            # used to compute this second cycle reflects the just-made
            # switch, not a stale, pre-switch snapshot of it
            "\x1b",  # closes Milling; focus returns to the still-open tree
            "\x1b",  # closes the tree; back to the bare bar
            "\x1b",  # nothing open -> exit
        ],
        on_batch=on_batch,
    )

    ui = holder["ui"]
    end_milling_state = ui.milling_states[MillingSubOperation.END_MILLING]
    face_milling_state = ui.milling_states[MillingSubOperation.FACE_MILLING]
    # The last snapshot captured before the operation closed reflects the
    # state right after the second "l" -- it must have alternated back to
    # End Milling, not gotten stuck on Face Milling.
    assert states_after_each_batch[-1] is end_milling_state
    assert face_milling_state.material_type is None
    assert end_milling_state.material_type is None
