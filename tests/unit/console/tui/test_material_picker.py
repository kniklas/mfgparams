"""Unit tests for the material selection window's pure state/logic
(specs/023-material-selector-dialog).

Covers `MaterialPickerState`, `open_state()`, `move_highlight()` (Foundational,
tasks.md T011), and `candidates()`/`cycle_column()` (User Stories 1-3, added
incrementally per story below).
"""

from __future__ import annotations

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.layout.containers import Window, WritePosition
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Screen
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.utils import get_cwidth

from mfgparams.console.i18n import translate
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.material_picker import (
    _COMMON_WIDTH,
    _NUMBER_WIDTH,
    MaterialPickerState,
    candidates,
    cycle_column,
    move_highlight,
    open_state,
    render,
)
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import DrillingSessionState
from mfgparams.registry import WorkpieceMaterial


def _material(name: str, **kwargs) -> WorkpieceMaterial:
    return WorkpieceMaterial(
        name=name,
        reference_cutting_speed_m_min=25.0,
        reference_feed_per_rev_mm=0.20,
        specific_cutting_force_kc=1900.0,
        **kwargs,
    )


_STEEL = _material("Mild Steel", material_number="1.0038", short_notation="S235JR")
_CHROMOLY = _material("Chromoly Steel", material_number="1.7225", short_notation="42CrMo4+N")
_ALLOY = _material("Unlabeled Alloy")
_MATERIALS = [_STEEL, _CHROMOLY, _ALLOY]


class TestOpenState:
    def test_resets_queries_and_active_column(self):
        state = open_state("Mild Steel", _MATERIALS)

        assert state.query_common == ""
        assert state.query_number == ""
        assert state.query_short == ""
        assert state.active_column == "common"

    def test_highlights_the_previously_selected_material_when_present(self):
        state = open_state("Chromoly Steel", _MATERIALS)

        assert state.highlighted_name == "Chromoly Steel"

    def test_no_highlight_when_no_material_was_previously_selected(self):
        state = open_state(None, _MATERIALS)

        assert state.highlighted_name is None

    def test_no_highlight_when_previously_selected_material_is_absent_from_the_list(self):
        state = open_state("Some Other Material", _MATERIALS)

        assert state.highlighted_name is None


class TestMoveHighlight:
    def test_down_moves_to_the_next_candidate(self):
        state = MaterialPickerState(highlighted_name="Mild Steel")

        move_highlight(state, _MATERIALS, 1)

        assert state.highlighted_name == "Chromoly Steel"

    def test_up_moves_to_the_previous_candidate(self):
        state = MaterialPickerState(highlighted_name="Chromoly Steel")

        move_highlight(state, _MATERIALS, -1)

        assert state.highlighted_name == "Mild Steel"

    def test_down_at_the_last_candidate_does_not_wrap(self):
        state = MaterialPickerState(highlighted_name="Unlabeled Alloy")

        move_highlight(state, _MATERIALS, 1)

        assert state.highlighted_name == "Unlabeled Alloy"

    def test_up_at_the_first_candidate_does_not_wrap(self):
        state = MaterialPickerState(highlighted_name="Mild Steel")

        move_highlight(state, _MATERIALS, -1)

        assert state.highlighted_name == "Mild Steel"

    def test_single_candidate_list_stays_on_that_candidate(self):
        state = MaterialPickerState(highlighted_name="Mild Steel")

        move_highlight(state, [_STEEL], 1)
        assert state.highlighted_name == "Mild Steel"

        move_highlight(state, [_STEEL], -1)
        assert state.highlighted_name == "Mild Steel"

    def test_empty_candidate_list_clears_the_highlight(self):
        state = MaterialPickerState(highlighted_name="Mild Steel")

        move_highlight(state, [], 1)

        assert state.highlighted_name is None

    def test_highlight_no_longer_in_the_list_snaps_to_the_first_candidate(self):
        """E.g. after a query edit narrowed the candidate list (data-model.md
        "Edit query" transition) -- the previous highlight may no longer be
        a candidate."""

        state = MaterialPickerState(highlighted_name="Unlabeled Alloy")

        move_highlight(state, [_STEEL, _CHROMOLY], 1)

        assert state.highlighted_name == "Mild Steel"

    def test_none_highlight_snaps_to_the_first_candidate(self):
        state = MaterialPickerState(highlighted_name=None)

        move_highlight(state, _MATERIALS, 1)

        assert state.highlighted_name == "Mild Steel"


class TestCandidatesCommonNameOnly:
    """User Story 1 (tasks.md T020): `candidates()` filters on
    `query_common` only so far -- `query_number`/`query_short` are not yet
    consulted (User Stories 2/3 extend this same function)."""

    def test_empty_query_returns_the_full_list_unfiltered(self):
        state = MaterialPickerState()

        result = candidates(state, _MATERIALS, "en")

        assert result == _MATERIALS

    def test_substring_match_is_case_insensitive(self):
        state = MaterialPickerState(query_common="chromoly")

        result = candidates(state, _MATERIALS, "en")

        assert result == [_CHROMOLY]

    def test_partial_match_narrows_to_every_matching_material(self):
        state = MaterialPickerState(query_common="steel")

        result = candidates(state, _MATERIALS, "en")

        assert result == [_STEEL, _CHROMOLY]

    def test_no_match_returns_an_empty_list(self):
        state = MaterialPickerState(query_common="titanium")

        result = candidates(state, _MATERIALS, "en")

        assert result == []

    def test_matches_against_the_translated_display_name(self):
        """Clarification 1: the common-name column displays and searches
        the translated display name for the active display locale, not
        the canonical English name."""

        translated = WorkpieceMaterial(
            name="Mild Steel",
            reference_cutting_speed_m_min=25.0,
            reference_feed_per_rev_mm=0.20,
            specific_cutting_force_kc=1900.0,
            translations={"de": "Weicher Stahl"},
        )
        state = MaterialPickerState(query_common="weicher")

        result = candidates(state, [translated], "de")

        assert result == [translated]


class TestCandidatesMaterialNumber:
    """User Story 2 (tasks.md T025): `candidates()` also filters on
    `query_number`, combining (AND) with any non-empty `query_common`."""

    def test_substring_match_narrows_correctly(self):
        state = MaterialPickerState(query_number="1.72")

        result = candidates(state, _MATERIALS, "en")

        assert result == [_CHROMOLY]

    def test_material_with_no_material_number_is_excluded_when_searched(self):
        """FR-010: `_ALLOY` has no `material_number`, so a non-empty
        `query_number` excludes it even though it would otherwise match no
        filter at all."""

        state = MaterialPickerState(query_number="1")

        result = candidates(state, _MATERIALS, "en")

        assert _ALLOY not in result

    def test_empty_query_number_does_not_exclude_materials_without_one(self):
        state = MaterialPickerState()

        result = candidates(state, _MATERIALS, "en")

        assert _ALLOY in result

    def test_combines_with_a_non_empty_query_common(self):
        """Both "steel" (common name) and "1.0" (number) match only Mild
        Steel; Chromoly Steel matches "steel" but not "1.0"."""

        state = MaterialPickerState(query_common="steel", query_number="1.0")

        result = candidates(state, _MATERIALS, "en")

        assert result == [_STEEL]


class TestCandidatesShortNotation:
    """User Story 3 (tasks.md T032): `candidates()` also filters on
    `query_short`, combining (AND) with `query_common`/`query_number`."""

    def test_substring_match_narrows_correctly(self):
        state = MaterialPickerState(query_short="42crmo4")

        result = candidates(state, _MATERIALS, "en")

        assert result == [_CHROMOLY]

    def test_material_with_no_short_notation_is_excluded_when_searched(self):
        state = MaterialPickerState(query_short="s2")

        result = candidates(state, _MATERIALS, "en")

        assert _ALLOY not in result

    def test_empty_query_short_does_not_exclude_materials_without_one(self):
        state = MaterialPickerState()

        result = candidates(state, _MATERIALS, "en")

        assert _ALLOY in result

    def test_all_three_queries_simultaneously_require_matching_all_three(self):
        """spec.md User Story 3 Acceptance Scenario 2."""

        state = MaterialPickerState(
            query_common="steel", query_number="1.72", query_short="42crmo4"
        )

        result = candidates(state, _MATERIALS, "en")

        assert result == [_CHROMOLY]

        # Changing just one of the three to something Chromoly Steel does
        # not match empties the result, proving all three are enforced.
        state.query_short = "s235jr"
        assert candidates(state, _MATERIALS, "en") == []


class TestCycleColumn:
    """User Story 2 (tasks.md T026): wraps in both directions among
    common/number/short (research.md Decision 7)."""

    def test_cycles_right_through_all_three_and_wraps(self):
        state = MaterialPickerState(active_column="common")

        cycle_column(state, 1)
        assert state.active_column == "number"

        cycle_column(state, 1)
        assert state.active_column == "short"

        cycle_column(state, 1)
        assert state.active_column == "common"

    def test_cycles_left_through_all_three_and_wraps(self):
        state = MaterialPickerState(active_column="common")

        cycle_column(state, -1)
        assert state.active_column == "short"

        cycle_column(state, -1)
        assert state.active_column == "number"

        cycle_column(state, -1)
        assert state.active_column == "common"


class TestRender:
    """Direct assertions on `render()`'s output text (not just that it
    executes without raising, which the integration suite already covers
    incidentally via 100% line coverage) -- closes a real gap found while
    walking quickstart.md Scenario 3 for tasks.md T041: FR-010's "blank
    cell, not an error" claim was never directly asserted against the
    actual rendered text anywhere in this suite."""

    @staticmethod
    def _text(state: MaterialPickerState, candidate_list: list[WorkpieceMaterial]) -> str:
        fragments = render(state, candidate_list, "en", "en")
        return "".join(text for _style, text in fragments)

    def test_a_material_missing_both_notations_renders_blank_not_none(self):
        text = self._text(MaterialPickerState(), [_ALLOY])

        assert "Unlabeled Alloy" in text
        assert "None" not in text

    def test_a_material_with_both_notations_renders_them(self):
        text = self._text(MaterialPickerState(), [_CHROMOLY])

        assert "1.7225" in text
        assert "42CrMo4+N" in text

    def test_empty_candidates_shows_the_translated_empty_state_message(self):
        text = self._text(MaterialPickerState(), [])

        assert "No matching materials." in text

    def test_two_candidates_with_identical_rows_are_disambiguated_by_name(self):
        """Two different registry entries (different `.name`) can share
        the same translated common name and both leave material_number/
        short_notation blank, rendering an otherwise indistinguishable
        row -- `unique_labels`' "(key)" suffix convention (`forms.py`)
        must kick in here exactly as it already does for radio-row labels
        elsewhere, or a human could not tell which row Up/Down is on. Force
        the collision directly via `translations`, since two *different*
        bundled/configured entries sharing one translated common name is
        exactly the real-world case (e.g. a user's materials-config adding
        a second, differently-sourced "Mild Steel")."""

        twin_a = _material("a", translations={"en": "Mild Steel"})
        twin_b = _material("b", translations={"en": "Mild Steel"})

        text = self._text(MaterialPickerState(), [twin_a, twin_b])

        assert "Mild Steel (a)" in text
        assert "Mild Steel (b)" in text

    def test_a_candidate_whose_raw_name_matches_a_generated_disambiguation_is_still_unique(self):
        """PR #106 review, round 7: two "Foo" candidates ("a"/"b") produce
        "Foo (a)"/"Foo (b)". A *third*, otherwise-unique candidate whose
        raw name happens to already be "Foo (a)" is not itself part of
        that collision group, so comparing only within each candidate's
        own original group (an earlier version of this function did)
        misses that it now collides with what "a" was just disambiguated
        to. All three rendered rows must end up distinct."""

        twin_a = _material("a", translations={"en": "Foo"})
        twin_b = _material("b", translations={"en": "Foo"})
        lookalike = _material("c", translations={"en": "Foo (a)"})

        text = self._text(MaterialPickerState(), [twin_a, twin_b, lookalike])

        rows = [line for line in text.splitlines() if line.strip().startswith("Foo")]
        assert len(rows) == 3
        assert len(set(rows)) == 3

    def test_no_disambiguation_when_rows_are_already_distinct(self):
        text = self._text(MaterialPickerState(), [_STEEL, _CHROMOLY])

        assert "(Mild Steel)" not in text
        assert "(Chromoly Steel)" not in text

    def test_disambiguation_survives_a_name_that_already_fills_the_column(self):
        """A collision on a name already at/near `_COMMON_WIDTH` must not
        have its "(key)" discriminator silently clipped away by
        `_row_text`'s later padding -- the two rows would render
        identically again, defeating the whole point of disambiguating
        (PR #106 review, round 2). The fix reserves the suffix's space by
        shortening the *base* name first, rather than appending the
        suffix and clipping the combined text."""

        long_name = "X" * _COMMON_WIDTH
        twin_a = _material("supplier-a", translations={"en": long_name})
        twin_b = _material("supplier-b", translations={"en": long_name})

        text = self._text(MaterialPickerState(), [twin_a, twin_b])

        assert "(supplier-a)" in text
        assert "(supplier-b)" in text

    def test_disambiguation_falls_back_to_an_ordinal_when_the_key_itself_is_too_wide(self):
        """A `.name` long enough that even ``" (name)"`` alone exceeds
        `_COMMON_WIDTH` cannot be reserved room for -- shortening the base
        name to zero still wouldn't fit the suffix. The fallback must
        still render the two colliding rows distinctly (PR #106 review,
        round 3), via a short " #N" ordinal instead of the unfitting key
        -- starting at " #2" for the *first* colliding row too, mirroring
        `unique_labels`'s own ordinal convention exactly (round 7)."""

        long_name = "X" * (_COMMON_WIDTH + 10)
        twin_a = _material(long_name + "-a", translations={"en": long_name})
        twin_b = _material(long_name + "-b", translations={"en": long_name})

        text = self._text(MaterialPickerState(), [twin_a, twin_b])

        assert "#2" in text
        assert "#3" in text
        rows = [line for line in text.splitlines() if line.strip().startswith("X")]
        assert len(rows) == 2
        assert rows[0] != rows[1]

    def test_the_highlighted_row_carries_the_selected_style(self):
        state = MaterialPickerState(highlighted_name="Mild Steel")

        fragments = render(state, [_STEEL, _CHROMOLY], "en", "en")

        highlighted = [(style, text) for style, text in fragments if "Mild Steel" in text]
        assert highlighted and highlighted[0][0] == "class:selected"

    def test_the_highlighted_row_carries_a_set_cursor_position_marker(self):
        """A candidate list taller than the dialog's viewport must keep the
        highlighted row scrolled into view as Up/Down moves it (spec.md
        Edge Cases). Tags the row with prompt_toolkit's own documented
        `("[SetCursorPosition]", "")` fragment so the enclosing `Window`'s
        native scroll-to-cursor logic does this without app.py tracking a
        scroll offset by hand."""

        state = MaterialPickerState(highlighted_name="Chromoly Steel")

        fragments = render(state, [_STEEL, _CHROMOLY], "en", "en")

        marker_index = next(
            i for i, (style, _text) in enumerate(fragments) if style == "[SetCursorPosition]"
        )
        # The marker must sit immediately before the highlighted row's own
        # fragment, not anywhere else in the output.
        assert "Chromoly Steel" in fragments[marker_index + 1][1]

    def test_no_cursor_position_marker_when_nothing_is_highlighted(self):
        fragments = render(MaterialPickerState(), [_STEEL, _CHROMOLY], "en", "en")

        assert all(style != "[SetCursorPosition]" for style, _text in fragments)

    def test_column_headers_are_translated_not_hardcoded(self):
        text = self._text(MaterialPickerState(), [_STEEL])

        assert "Material No." in text
        assert "Short" in text

    def test_a_name_longer_than_its_column_does_not_overflow_the_row(self):
        """A translated common name (or a long material_number/short_notation
        from a user-supplied materials config) longer than its fixed column
        width must be clipped, not expand the row -- otherwise the dialog
        can overflow the 80-column floor (022-tui-min-size-25x80)."""

        long_name = "X" * (_COMMON_WIDTH + 10)
        material = _material(long_name, material_number="Y" * (_NUMBER_WIDTH + 10))

        fragments = render(MaterialPickerState(), [material], "en", "en")
        row_text = next(text for _style, text in fragments if long_name[0] in text)

        # The row is "<common> <number> <short>\n" -- the line up to (and
        # not including) the trailing newline must be exactly the three
        # fixed column widths plus the two single-space separators.
        assert len(row_text.rstrip("\n")) == _COMMON_WIDTH + 1 + _NUMBER_WIDTH + 1 + 14

    def test_a_query_longer_than_its_column_does_not_overflow_the_search_row(self):
        state = MaterialPickerState(query_common="X" * (_COMMON_WIDTH + 10))

        fragments = render(state, [_STEEL], "en", "en")
        query_fragment_text = fragments[1][1]

        assert len(query_fragment_text) == _COMMON_WIDTH

    def test_clipping_counts_display_columns_not_code_points(self):
        """A wide (e.g. CJK) character occupies two display columns per
        `get_cwidth` -- clipping/padding by code-point *count* alone (a
        naive `:<N`) would let such a name overflow its column by up to
        double its intended width, since each character both under-counts
        the clip point and over-counts the padding needed."""

        # Each "あ" is 2 display columns wide; 15 of them is a 30-column
        # string that must clip to exactly 10 of them (20 columns) plus
        # zero padding -- not naively truncate to 20 *characters* (which
        # would still be 40 display columns).
        wide_name = "あ" * 15
        material = _material(wide_name)

        fragments = render(MaterialPickerState(), [material], "en", "en")
        row_text = next(text for _style, text in fragments if "あ" in text)
        common_cell = row_text.split(" ", 1)[0]

        assert common_cell == "あ" * 10
        assert sum(get_cwidth(char) for char in common_cell) == _COMMON_WIDTH


class TestPaneHint:
    """FR-014 (tasks.md T044): `split_pane.render_bottom_bar` swaps in a
    hint naming Enter's detailed-search behavior specifically when the
    metal Material row is selected and the dialog is closed (research.md
    Decision 9) -- otherwise it shows the pre-existing generic hint/status
    exactly as before this feature."""

    @staticmethod
    def _text(screen: OperationScreen) -> str:
        fragments = split_pane.render_bottom_bar(screen, "en")
        return "".join(text for _style, text in fragments)

    def test_metal_material_row_selected_shows_the_picker_hint(self):
        screen = OperationScreen(
            operation="drilling",
            session_state=DrillingSessionState(material_type="metal"),
            selected_field=FieldId.MATERIAL,
        )

        text = self._text(screen)

        assert text == translate("en", "tui.material_picker.pane_hint")

    def test_non_metal_material_type_shows_the_generic_hint(self):
        screen = OperationScreen(
            operation="drilling",
            session_state=DrillingSessionState(material_type="wood"),
            selected_field=FieldId.MATERIAL,
        )

        text = self._text(screen)

        assert text == translate("en", "tui.pane.hint")

    def test_a_different_selected_field_shows_the_generic_hint(self):
        screen = OperationScreen(
            operation="drilling",
            session_state=DrillingSessionState(material_type="metal"),
            selected_field=FieldId.MATERIAL_TYPE,
        )

        text = self._text(screen)

        assert text == translate("en", "tui.pane.hint")

    def test_a_pending_status_message_still_wins_over_the_picker_hint(self):
        """FR-006b's unparseable-number status is unrelated to material
        selection, but must not be masked if the two ever coincide."""

        screen = OperationScreen(
            operation="drilling",
            session_state=DrillingSessionState(material_type="metal"),
            selected_field=FieldId.MATERIAL,
            status="some pending validation message",
        )

        text = self._text(screen)

        assert text == "some pending validation message"


class TestScrollIntoView:
    """End-to-end proof that `render()`'s `[SetCursorPosition]` marker
    (`TestRender` above only checks the marker is present in the fragment
    list, not that prompt_toolkit actually *acts* on it) really does keep
    a highlighted row scrolled into view, against a real `Window`/
    `FormattedTextControl` pair rather than prompt_toolkit's source read
    alone (raised again as a HIGH finding in PR #106 review round 2,
    against `app.py`'s `Window(content=material_picker_control, ...)`
    line, despite the marker already existing in `render()` -- app.py's
    own Window has no scroll code of its own to point to, since
    prompt_toolkit's built-in mechanism is what handles it; this test is
    the durable, repo-side evidence for that claim rather than a one-off
    interactive check)."""

    @staticmethod
    def _vertical_scroll_after_render(
        candidate_count: int, highlighted_index: int, viewport_height: int
    ) -> tuple[int, int]:
        """Render `candidate_count` synthetic materials with the one at
        `highlighted_index` highlighted, through a real `Window` bounded
        to `viewport_height` rows, and return
        ``(window.vertical_scroll, last_visible_line)``."""

        materials = [_material(f"Material {i}") for i in range(candidate_count)]
        state = MaterialPickerState(highlighted_name=materials[highlighted_index].name)

        with (
            create_pipe_input() as pipe_input,
            create_app_session(input=pipe_input, output=DummyOutput()),
        ):
            control = FormattedTextControl(
                lambda: render(state, materials, "en", "en"), show_cursor=False
            )
            window = Window(content=control, wrap_lines=True)
            wp = WritePosition(xpos=0, ypos=0, width=60, height=viewport_height)
            window._write_to_screen_at_index(Screen(), MouseHandlers(), wp, "", True)
            assert window.render_info is not None
            return window.vertical_scroll, window.render_info.last_visible_line()

    def test_a_highlight_below_the_fold_scrolls_the_window_down(self):
        """20 candidates, a 6-row viewport, highlight on the last one --
        without scrolling, row 19 would render far past row 6 and never
        appear on screen at all."""

        vertical_scroll, last_visible_line = self._vertical_scroll_after_render(
            candidate_count=20, highlighted_index=19, viewport_height=6
        )

        assert vertical_scroll > 0
        assert last_visible_line >= 19 + 4  # +4 for the title/header lines render() adds

    def test_a_highlight_within_the_first_viewport_does_not_scroll(self):
        vertical_scroll, _last_visible_line = self._vertical_scroll_after_render(
            candidate_count=20, highlighted_index=0, viewport_height=6
        )

        assert vertical_scroll == 0
