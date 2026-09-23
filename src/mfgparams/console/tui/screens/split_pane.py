"""Shared left/right split-pane engine for the Drilling and Milling operation
screens (018-tui-splitpane-redesign FR-004/FR-005/FR-009).

Instant-edit numeric fields (FR-016), Left/Right nudge (FR-017), and the
right pane's result state (FR-006/FR-006a) live here once;
`screens/drilling.py`/`screens/milling.py` (T022/T023) each supply only
their own field list (`rows_for`, mirroring `machining_menu.tree_rows`'
"recompute every render" approach, since a later row's visibility can
depend on an earlier row's value -- e.g. `material` only appears once
`material_type` is chosen, `target_rpm` only in Fixed RPM mode) and their
own `calculate()` call, per FR-009's identical-pattern requirement.

FR-006a's design collapses cleanly here: unlike the old dialog chain (which
pre-validated each field with e.g. `validate_diameter_mm` before ever
calling `calculate()`), this module does no range validation of its own --
`calculate()`/`calculate_end_milling()`/`calculate_face_milling()` already
re-validate every field internally regardless of caller (confirmed in
spec.md's FR-006a rationale), so once a field parses as a number this
module's only job is to call `calculate()` and display whatever `ErrorInfo`
it returns.

**Rebuilt to match the pre-plan prototype exactly** (`prototype_drilling_
splitpane.py`/`prototype_milling_splitpane.py`, both still present at the
paths named in spec.md's Carried-Over Items table -- consulted directly
after the shipped implementation's earlier interaction models turned out
not to match user expectations set by that prototype). The governing
behaviors, all taken from the prototype's own code, not reinvented:

- A radio field is always a single `Label: value` line -- never an
  expanded option list. Left/Right/Space cycle it and commit immediately
  (`_cycle`/`cycle_field` in the prototype).
- Up/Down (and j/k) always move between fields, unconditionally, regardless
  of a field's type -- there is no per-field-type dispatch to reason about.
- A numeric field's typed/nudged text lives in `field_buffer` only;
  `session_state` is **not** touched until the user navigates away from the
  field (`commit_current`/`move_selection` in the prototype) -- typing and
  nudging never commit immediately. An unparseable buffer, discovered only
  at that commit attempt, is discarded (not written to `session_state`) and
  surfaces via `OperationScreen.status`, a transient bottom-status-bar
  message (`ui.status` in the prototype) -- not a right-pane state, and not
  shown while still actively editing the field.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Union

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import translate
from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.models import CalculationResult

#: FR-017: "a small fixed step" -- 1 display unit (already in the field's
#: current unit system, e.g. 1 mm or 1 in for a length field), matching the
#: prototype's own validated step size (spec's Recommended Next Steps).
NUDGE_STEP = 1.0


@dataclass(frozen=True)
class RadioRow:
    """One FR-005 radio field (unit system, mode, material type, material,
    tool, milling sub-operation). `options` is the ordered
    ``(value, display_label)`` set currently available -- callers rebuild it
    every render since a later row's options can depend on an earlier row's
    value (e.g. `material`'s options depend on `material_type`).
    `on_select` commits the chosen value immediately -- matching the
    prototype's `cycle_field`, which calls `setattr` synchronously on every
    Left/Right/Space, with no separate confirm step."""

    field_id: FieldId
    label: str
    options: list[tuple[str, str]]
    value: str | None
    on_select: Callable[[str], None]


@dataclass(frozen=True)
class NumberRow:
    """One FR-005/FR-016 plain numeric field. `required` distinguishes a
    field that gates FR-006's readiness (diameter, depth, ...) from one
    that's present but optional (available power outside Power-Constrained
    mode) -- both are simultaneously visible/editable per FR-005, but only
    the former blocks the right pane's result state.

    `on_commit` is called only when the user navigates away from this field
    (`move_selection`), with the fully-parsed value (`None` for a blank
    buffer) -- matching the prototype's `commit_current`. Typing
    (`edit_selected`) and nudging (`nudge_selected`) only ever touch
    `OperationScreen.field_buffer`, never call this directly.

    `step` (specs/020-turning-feed-per-rotation FR-011/research.md #7):
    the amount `nudge_selected` adds/subtracts per Left/Right press.
    Defaults to the shared `NUDGE_STEP` (1 display unit); a row MAY
    override it with a smaller value for a field where that default is too
    coarse (e.g. turning's feed-rate-per-rotation field)."""

    field_id: FieldId
    label: str
    unit: str
    value: float | None
    required: bool
    on_commit: Callable[[float | None], None]
    step: float = NUDGE_STEP


Row = Union[RadioRow, NumberRow]


def power_and_rpm_rows(
    *,
    power_constrained: bool,
    fixed_rpm: bool,
    feed_rate_constrained: bool = False,
    rotation_and_feed_constrained: bool = False,
    power_and_feed_constrained: bool = False,
    power_row: Callable[[str, bool], NumberRow],
    rpm_row: Callable[[], NumberRow],
    feed_rate_row: Callable[[], NumberRow] | None = None,
) -> list[Row]:
    """The mode-dependent trailing rows Drilling and Milling both build the
    same way (FR-009's identical-pattern requirement, applied to this one
    previously-duplicated branch): Power-Constrained needs available power
    (required); Fixed RPM needs target RPM (required) plus available power
    (optional); Standard needs only available power (optional). Callers
    supply small factories (`power_row(label_key, required)`, `rpm_row()`)
    since the row's label/unit/current value/commit closures are
    screen-specific.

    `feed_rate_constrained`/`feed_rate_row` (specs/020-turning-feed-per-
    rotation) are turning-only additions: needs feed rate per rotation
    (required) plus available power (optional).

    `rotation_and_feed_constrained`/`power_and_feed_constrained`
    (specs/021-turning-combined-constraints) are further turning-only
    additions, both reusing the same `rpm_row()`/`feed_rate_row()`/
    `power_row()` factories: the former needs target spindle speed
    (required) plus feed rate per rotation (required) plus available power
    (optional, FR-006); the latter needs feed rate per rotation (required)
    plus available power (required, FR-004) -- no spindle-speed row, since
    it is solved for rather than supplied.

    Every new parameter here defaults so Drilling's and Milling's existing
    call sites -- which never pass them -- are unaffected."""

    if power_constrained:
        return [power_row("tui.label.power_required", True)]
    if fixed_rpm:
        return [rpm_row(), power_row("tui.label.power", False)]
    if feed_rate_constrained:
        if feed_rate_row is None:
            raise ValueError("feed_rate_row is required when feed_rate_constrained=True")
        return [feed_rate_row(), power_row("tui.label.power", False)]
    if rotation_and_feed_constrained:
        if feed_rate_row is None:
            raise ValueError("feed_rate_row is required when rotation_and_feed_constrained=True")
        return [rpm_row(), feed_rate_row(), power_row("tui.label.power", False)]
    if power_and_feed_constrained:
        if feed_rate_row is None:
            raise ValueError("feed_rate_row is required when power_and_feed_constrained=True")
        return [feed_rate_row(), power_row("tui.label.power_required", True)]
    return [power_row("tui.label.power", False)]


def is_complete(rows: list[Row]) -> bool:
    """FR-006's readiness gate: every row in the *current* row list either
    holds a value, or is an optional `NumberRow` (an operation-dependent
    row list is how a caller expresses "not applicable right now" -- e.g.
    the specific-material row is simply absent until `material_type` has a
    value, rather than present-but-required)."""

    for row in rows:
        if isinstance(row, RadioRow) and row.value is None:
            return False
        if isinstance(row, NumberRow) and row.required and row.value is None:
            return False
    return True


def selected_row(rows: list[Row], screen: OperationScreen) -> Row | None:
    for row in rows:
        if row.field_id is screen.selected_field:
            return row
    return None


def _format(value: float | None) -> str:
    """Matches the prototype's `_format_number`: `.4g`, not a bare `g` --
    e.g. `10` stays `10`, `0.05` stays `0.05`, but a longer float rounds to
    4 significant digits rather than however many `repr` would show.

    Display only -- an unselected `NumberRow`'s read-only listing in
    `render_left_pane` -- never `field_buffer`. `field_buffer` is live,
    re-editable, re-committable text (FR-016/FR-017), so it needs
    `_buffer_text`'s round-trippable representation instead; reusing this
    lossy one there was a CRITICAL bug a round-3 code-review pass on PR #96
    found (`_buffer_text`'s own docstring has the concrete example)."""

    if value is None:
        return ""
    return f"{value:.4g}"


def _buffer_text(value: float) -> str:
    """`field_buffer`'s own formatter -- unlike `_format` above, this must
    round-trip exactly (`float(_buffer_text(x)) == x` for every finite
    `x`), since the buffer it populates is parsed straight back by
    `_commit_current`/`nudge_selected` on the very next keystroke, with no
    further edit required to trigger it. `_format`'s 4-significant-digit
    rounding silently corrupted a committed value on nothing more than
    revisiting the field: a fixed RPM of `12345` synced to a buffer of
    `1.234e+04` (`_format`'s `.4g` output), which reparses as `12340.0` --
    simply leaving the field (no edit at all) changed the committed value.
    Nudging compounded it further: `nudge_selected` adds `NUDGE_STEP` to
    whatever the buffer currently parses as, so nudging Right from that
    already-corrupted `12340` buffer landed on `12341`, not the correct
    `12346`, changing the calculation the user never asked to change.
    `repr`'s shortest round-tripping form fixes this (Python's `float`
    `repr` has round-tripped exactly since 3.1); integral values drop the
    trailing `.0` so a typed `12345` reads back as `12345`, not a
    surprising `12345.0`, matching what the user actually typed."""

    if value == int(value):
        return str(int(value))
    return repr(value)


def sync_buffer(rows: list[Row], screen: OperationScreen) -> None:
    """Re-syncs `field_buffer` to the currently-selected row's own
    committed value -- called whenever selection changes (including when a
    screen is first opened), so a numeric field is immediately typable
    from what's actually on screen (FR-016), not a buffer left over from a
    previously-selected field. Matches the prototype's `_load_buffer`:
    radio fields don't use `field_buffer` at all (they have no editable
    "raw text" state -- Left/Right/Space act on `row.value` directly)."""

    row = selected_row(rows, screen)
    screen.field_buffer = (
        _buffer_text(row.value) if isinstance(row, NumberRow) and row.value is not None else ""
    )


def _commit_current(rows: list[Row], screen: OperationScreen, locale: str) -> None:
    """The prototype's `commit_current`: parses `field_buffer` into the
    currently-selected `NumberRow`'s value, called automatically whenever
    selection is about to move off it (`move_selection`) -- there is no
    other trigger. A blank buffer commits `None` (unset). An unparseable,
    non-blank buffer commits nothing (the field's last-committed value is
    left untouched) and records `OperationScreen.status` instead -- FR-006b,
    surfaced as a transient bottom-status-bar message, not a right-pane
    state, and only once the user actually tries to leave the field, not
    while still typing on it. A no-op (clearing any stale status) on
    anything but a `NumberRow`."""

    row = selected_row(rows, screen)
    if not isinstance(row, NumberRow):
        screen.status = None
        return
    text = screen.field_buffer.strip()
    if not text:
        row.on_commit(None)
        screen.status = None
        return
    try:
        row.on_commit(float(text))
        screen.status = None
    except ValueError:
        screen.status = translate(locale, "tui.validation.unparseable_number", text=text)


def move_selection(rows: list[Row], screen: OperationScreen, delta: int, locale: str) -> None:
    """Moves `screen.selected_field` to the next/previous row (wrapping),
    committing the field being left first (`_commit_current`) -- matching
    the prototype's `move_selection` exactly: Up/Down always does this,
    unconditionally, regardless of the current or next row's type."""

    if not rows:
        return
    _commit_current(rows, screen, locale)
    ids = [row.field_id for row in rows]
    try:
        index = ids.index(screen.selected_field)
    except ValueError:
        index = 0
    screen.selected_field = ids[(index + delta) % len(ids)]
    sync_buffer(rows, screen)


def edit_selected(rows: list[Row], screen: OperationScreen, char: str) -> None:
    """FR-016: typing immediately edits the selected numeric field's
    buffer -- no separate "start editing" action, and no commit to
    `session_state` either (that only happens on navigating away,
    `move_selection`) -- matching the prototype's digit key handlers,
    which only ever append to `ui.buffer`. A no-op on a `RadioRow` (radios
    only ever change via `nudge_selected`, never free text)."""

    row = selected_row(rows, screen)
    if not isinstance(row, NumberRow):
        return
    screen.field_buffer += char


def backspace_selected(rows: list[Row], screen: OperationScreen) -> None:
    row = selected_row(rows, screen)
    if not isinstance(row, NumberRow):
        return
    screen.field_buffer = screen.field_buffer[:-1]


def nudge_selected(rows: list[Row], screen: OperationScreen, direction: int) -> None:
    """FR-017 on a `NumberRow`: adjusts `field_buffer` by `row.step`
    (defaults to `NUDGE_STEP`; specs/020-turning-feed-per-rotation
    research.md #7), falling back to the row's last-committed value (or 0)
    if the buffer doesn't currently parse -- matching the prototype's
    `adjust_numeric` exactly, including that this only ever touches the
    buffer, never committing to `session_state` directly (`move_selection`
    still does that). A nudge that would land at or below zero clears the
    buffer to unset rather than going negative (contract §4's
    implementation detail).

    On a `RadioRow`, cycles `value` with wraparound and commits
    immediately via `on_select` -- matching the prototype's `cycle_field`
    (no buffering, no separate confirm step for radios)."""

    row = selected_row(rows, screen)
    if row is None:
        return
    if isinstance(row, NumberRow):
        text = screen.field_buffer.strip()
        try:
            current = float(text) if text else 0.0
        except ValueError:
            current = row.value if row.value is not None else 0.0
        # Decimal-safe addition: `row.step` values below 1.0 (e.g. 0.1
        # mm/rev, 0.005 in/rev -- specs/020-turning-feed-per-rotation
        # research.md #7) are not exactly representable in binary
        # floating-point, so plain `float` addition accumulates visible
        # drift (0.1 + 0.1 + 0.1 == 0.30000000000000004) that
        # `_buffer_text`'s exact-round-trip `repr()` would otherwise show
        # to the user verbatim. `Decimal(str(x))` reconstructs the exact
        # decimal value `x`'s own shortest round-tripping representation
        # already denotes (the same digits `repr`/`str` would print), so
        # the addition itself introduces no binary rounding error --
        # unlike blanket-rounding the result (an earlier version of this
        # fix, caught by Copilot review: it truncated a pre-existing
        # high-precision buffer on every other field too, e.g. nudging
        # `1.123456789` by the default step to `2.123457` instead of the
        # exact `2.123456789`).
        current_decimal = Decimal(str(current))
        step_decimal = Decimal(str(row.step))
        new_value = float(current_decimal + direction * step_decimal)
        screen.field_buffer = "" if new_value <= 0 else _buffer_text(new_value)
        return
    if not row.options:
        return
    values = [value for value, _ in row.options]
    if row.value in values:
        new_index = (values.index(row.value) + direction) % len(values)
    else:
        # From an unset field, land on a sensible edge instead of cycling
        # from a sentinel index: Right/l/Space (direction > 0) selects the
        # first option, Left/h (direction < 0) wraps straight to the last
        # one. A sentinel of -1 here (the previous approach) made Right
        # correct by coincidence ((-1 + 1) % n == 0) but Left land one
        # short of the last option instead of wrapping to it -- an
        # asymmetry a code-review pass on PR #96 caught empirically (the
        # very first Left press on an unset Tool/Material field selected
        # the second-to-last option, not the last).
        new_index = 0 if direction > 0 else len(values) - 1
    row.on_select(values[new_index])


def render_left_pane(
    rows: list[Row], screen: OperationScreen, title: str, locale: str, *, focused: bool
) -> StyleAndTextTuples:
    """FR-005's simultaneously-visible-and-editable left pane -- one
    compact `Label: value` line per field, every field always a single
    line (matching the prototype's `render_left`: no radio field ever
    expands into an option list). The selected `NumberRow` shows the live,
    possibly-mid-edit `field_buffer` with a trailing `_` cursor (FR-016);
    an unselected, unset `NumberRow` shows `--`, not a blank string."""

    fragments: StyleAndTextTuples = [("class:pane-title", f"{title}\n\n")]
    for row in rows:
        is_selected = row.field_id is screen.selected_field
        style = "class:selected" if focused and is_selected else ""
        if isinstance(row, RadioRow):
            checked_label = next(
                (label for value, label in row.options if value == row.value), "--"
            )
            fragments.append((style, f"{row.label}: {checked_label}\n"))
        else:
            unit_suffix = f" {row.unit}" if row.unit else ""
            if is_selected:
                value_text = f"{screen.field_buffer}_{unit_suffix}"
            else:
                value_text = f"{_format(row.value)}{unit_suffix}" if row.value is not None else "--"
            fragments.append((style, f"{row.label}: {value_text}\n"))
    return fragments


def render_bottom_bar(screen: OperationScreen, locale: str) -> StyleAndTextTuples:
    """The status/hint row spanning the full floating window beneath both
    panes -- matches the prototype's `render_bottom` exactly: an ordinary
    keyboard hint by default, replaced by `OperationScreen.status` (FR-006b's
    unparseable-number message, set only by `_commit_current`) when one is
    pending.

    When the currently-selected field is the metal Material row
    (023-material-selector-dialog), the generic hint is swapped for one
    naming Enter's extra behavior there (opening the detailed multi-column
    search window) -- Left/Right/Space still cycle it like any other radio
    row, so that part of the generic hint remains true and isn't repeated."""

    if screen.status:
        return [("class:error", screen.status)]
    if screen.selected_field is FieldId.MATERIAL and screen.session_state.material_type == "metal":
        return [("class:hint", translate(locale, "tui.material_picker.pane_hint"))]
    return [("class:hint", translate(locale, "tui.pane.hint"))]


def render_right_pane(
    rows: list[Row],
    screen: OperationScreen,
    calculate: Callable[[], CalculationResult],
    labels: dict[str, str],
    locale: str,
    *,
    placeholder: str,
) -> StyleAndTextTuples:
    """FR-006/FR-006a's two-state machine (placeholder while incomplete;
    a result or `calculate()`-rejected error once complete), memoized
    against the exact input tuple that produced it
    (`OperationScreen.last_result_key`) so an unrelated re-render doesn't
    recompute (SC-006). FR-006b's unparseable-text state is *not* one of
    these -- it surfaces via `render_bottom_bar` instead, only once the
    user tries to navigate away from the offending field (matching the
    prototype, which never second-guesses the right pane over what's still
    being typed). `placeholder` is the already-translated, operation-
    specific message (`tui.drilling.placeholder`/`tui.milling.placeholder`)
    -- matching the prototype's own per-screen default text, not a single
    generic one."""

    if not is_complete(rows):
        return [("class:hint", placeholder)]

    calculation_key = tuple(row.value for row in rows)
    if screen.last_result is None or screen.last_result_key != calculation_key:
        screen.last_result = calculate()
        screen.last_result_key = calculation_key

    result = screen.last_result
    is_error = result.error is not None
    title_key = "tui.result.error.title" if is_error else "tui.result.title"
    style = "class:error" if is_error else ""
    return [
        ("class:pane-title", f"{translate(locale, title_key)}\n\n"),
        (style, forms.format_result(result, labels, locale)),
    ]
