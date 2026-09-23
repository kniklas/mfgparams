"""The metal Material selection window (specs/023-material-selector-dialog),
implementing spec.md's "Material Selection Window" entity: a floating dialog
offering three side-by-side, independently searchable identifiers for a
metal `WorkpieceMaterial` -- common name, EN material number, and shortened
designation -- sharing one row highlight.

Rendering + state-transition logic only, mirroring `machining_menu.py`: this
module owns how the dialog lays out and how its state changes; `app.py` owns
the actual `Float`/key-binding wiring and decides when to open/close it.

`candidates()` (added by 023's User Story 1, extended by User Story 2/3) is
the one function each of the three columns' search behavior is layered onto
in place, rather than being duplicated per column (Constitution I; research.md
Decision 3) -- until it exists, every call site here operates on the full,
unfiltered material list directly (023 tasks.md T013's note).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import translate
from mfgparams.registry import WorkpieceMaterial

#: Fixed column widths for the three-column table (render() below). Chosen
#: to comfortably fit the 80-column floor (022-tui-min-size-25x80) alongside
#: the dialog's Frame/Shadow border overhead.
_COMMON_WIDTH = 20
_NUMBER_WIDTH = 12
_SHORT_WIDTH = 14

ColumnName = Literal["common", "number", "short"]

#: Cycling order for `cycle_column()` (research.md Decision 7).
_COLUMN_ORDER: tuple[ColumnName, ...] = ("common", "number", "short")


@dataclass
class MaterialPickerState:
    """Transient dialog state (data-model.md "New entity"). Lives on
    `app.py`'s `_ViewState.material_picker`, `None` when the dialog is
    closed (research.md Decision 1)."""

    query_common: str = ""
    query_number: str = ""
    query_short: str = ""
    active_column: ColumnName = "common"
    highlighted_name: str | None = None


def open_state(
    current_material_name: str | None, materials: list[WorkpieceMaterial]
) -> MaterialPickerState:
    """Construct the dialog's initial state (FR-011, Clarification 2): all
    three search fields empty, the common-name column active, and the row
    for ``current_material_name`` pre-highlighted if it is present in
    ``materials`` (the full, unfiltered list) -- otherwise no row is
    highlighted."""

    known_names = {material.name for material in materials}
    highlighted = current_material_name if current_material_name in known_names else None
    return MaterialPickerState(highlighted_name=highlighted)


def move_highlight(
    state: MaterialPickerState, candidates: list[WorkpieceMaterial], delta: int
) -> None:
    """Move ``state.highlighted_name`` to the previous (``delta=-1``) or
    next (``delta=1``) entry in ``candidates`` (FR-005). No wraparound: a
    highlight already at either end is left unchanged. A highlight that is
    ``None`` or no longer present in ``candidates`` (e.g. after a query
    edit narrowed the list) snaps to the first candidate, or stays ``None``
    if ``candidates`` is empty."""

    if not candidates:
        state.highlighted_name = None
        return

    names = [material.name for material in candidates]
    if state.highlighted_name is None:
        state.highlighted_name = names[0]
        return
    try:
        index = names.index(state.highlighted_name)
    except ValueError:
        state.highlighted_name = names[0]
        return

    new_index = index + delta
    if 0 <= new_index < len(names):
        state.highlighted_name = names[new_index]


def cycle_column(state: MaterialPickerState, delta: int) -> None:
    """Move ``state.active_column`` one step left (``delta=-1``) or right
    (``delta=1``) among common/number/short, wrapping (FR-006, research.md
    Decision 7)."""

    index = _COLUMN_ORDER.index(state.active_column)
    state.active_column = _COLUMN_ORDER[(index + delta) % len(_COLUMN_ORDER)]


def candidates(
    state: MaterialPickerState, materials: list[WorkpieceMaterial], display_locale: str
) -> list[WorkpieceMaterial]:
    """Filter ``materials`` to those matching every non-empty query
    (FR-004): a material is included only if, for each non-empty query, its
    corresponding column value both exists and contains that query as a
    case-insensitive substring. This is the one function each of User
    Stories 1-3 extends in place, rather than duplicating per column
    (Constitution I; research.md Decision 3).

    The common-name column matches against ``display_name(display_locale)``
    (Clarification 1), the same translated text FR-002's rendering shows.
    ``material_number``/``short_notation`` are opaque strings (research.md
    #6): a material missing one is excluded the moment the corresponding
    query is non-empty (FR-010), since a missing value cannot contain any
    non-empty substring."""

    query_common = state.query_common.strip().lower()
    query_number = state.query_number.strip().lower()
    query_short = state.query_short.strip().lower()

    def _matches(material: WorkpieceMaterial) -> bool:
        if query_common and query_common not in material.display_name(display_locale).lower():
            return False
        if query_number:
            if material.material_number is None:
                return False
            if query_number not in material.material_number.lower():
                return False
        if query_short:
            if material.short_notation is None:
                return False
            if query_short not in material.short_notation.lower():
                return False
        return True

    return [material for material in materials if _matches(material)]


def render(
    state: MaterialPickerState,
    candidates: list[WorkpieceMaterial],
    locale: str,
    display_locale: str,
) -> StyleAndTextTuples:
    """Three-column table: common name (translated per ``display_locale``,
    Clarification 1), EN material number, shortened designation (FR-002).
    The active search column's own query text is shown reverse-video
    (matching `split_pane.render_left_pane`'s "class:selected" convention
    for "this is the thing that currently receives input"); the highlighted
    row is shown the same way (FR-005). A missing `material_number`/
    `short_notation` renders as a blank cell (FR-010). Translated
    column headers and empty-state text are sourced from the message
    catalog (FR-013)."""

    def _row_text(common: str, number: str, short: str) -> str:
        return f"{common:<{_COMMON_WIDTH}} {number:<{_NUMBER_WIDTH}} {short:<{_SHORT_WIDTH}}"

    fragments: StyleAndTextTuples = [
        ("class:pane-title", f"{translate(locale, 'tui.material_picker.title')}\n\n")
    ]

    column_style = {
        column: "class:selected" if state.active_column == column else ""
        for column in _COLUMN_ORDER
    }
    fragments.append((column_style["common"], f"{state.query_common:<{_COMMON_WIDTH}}"))
    fragments.append(("", " "))
    fragments.append((column_style["number"], f"{state.query_number:<{_NUMBER_WIDTH}}"))
    fragments.append(("", " "))
    fragments.append((column_style["short"], f"{state.query_short:<{_SHORT_WIDTH}}\n"))

    header = _row_text(
        translate(locale, "tui.material_picker.column_common"),
        translate(locale, "tui.material_picker.column_number"),
        translate(locale, "tui.material_picker.column_short"),
    )
    fragments.append(("class:pane-title", f"{header}\n"))

    if not candidates:
        fragments.append(("class:hint", translate(locale, "tui.material_picker.empty")))
        return fragments

    for material in candidates:
        style = "class:selected" if material.name == state.highlighted_name else ""
        row_text = _row_text(
            material.display_name(display_locale),
            material.material_number or "",
            material.short_notation or "",
        )
        fragments.append((style, f"{row_text}\n"))

    return fragments
