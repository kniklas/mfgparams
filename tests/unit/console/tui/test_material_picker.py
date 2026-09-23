"""Unit tests for the material selection window's pure state/logic
(specs/023-material-selector-dialog).

Covers `MaterialPickerState`, `open_state()`, `move_highlight()` (Foundational,
tasks.md T011), and `candidates()`/`cycle_column()` (User Stories 1-3, added
incrementally per story below).
"""

from __future__ import annotations

from mfgparams.console.i18n import translate
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.material_picker import (
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

    def test_the_highlighted_row_carries_the_selected_style(self):
        state = MaterialPickerState(highlighted_name="Mild Steel")

        fragments = render(state, [_STEEL, _CHROMOLY], "en", "en")

        highlighted = [
            (style, text) for style, text in fragments if "Mild Steel" in text
        ]
        assert highlighted and highlighted[0][0] == "class:selected"

    def test_column_headers_are_translated_not_hardcoded(self):
        text = self._text(MaterialPickerState(), [_STEEL])

        assert "Material No." in text
        assert "Short" in text


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
