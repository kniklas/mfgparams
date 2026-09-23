"""UI-state entities and application wiring for the text GUI
(018-tui-splitpane-redesign).

See data-model.md's `SessionUI`/`MachiningTree`/`OperationScreen` entities.
Unlike 017's dialog chain (a sequence of short-lived, separately-constructed
`Application`s, one per screen), `run()` below constructs a single
persistent `Application`/`Layout` for the whole session: the menu bar, the
Machining tree, and an open operation screen are all fields on one
`SessionUI` object rather than a "current screen" stack, and can coexist
(FR-005a) rather than being mutually exclusive.

Note on FR-013a (terminal resize): 017's `NavigationState`-based module
docstring reasoned that prompt-toolkit's own resize handling needed no
opt-in, since no screen there ever constructed a *new* `Application`
mid-resize. That reasoning doesn't carry over unexamined here -- this
feature's single, long-lived `Application` is a materially different shape
(constructed once, not per screen), so whether in-progress left-pane input
survives a resize needs re-verifying against *this* shape specifically
(tasks.md T029), not assumed from 017's now-superseded architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal, cast

from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.utils import get_cwidth

from mfgparams.console.i18n import get_locale
from mfgparams.console.tui.material_picker import MaterialPickerState
from mfgparams.console.tui.menu import MenuEntry
from mfgparams.i18n import get_raw_locale
from mfgparams.i18n import translate as _translate_core
from mfgparams.models import CalculationResult, MillingSubOperation
from mfgparams.registry_config import RegistryConfigError

if TYPE_CHECKING:
    # Deferred to type-checking only: `screens/drilling.py`/`screens/milling.py`
    # import `FieldId`/`OperationScreen` *from this module* at their own
    # module level (T022/T023), so importing them back here eagerly would be
    # a circular import. Safe as a type-only import because
    # `from __future__ import annotations` (above) means `OperationScreen`'s
    # `session_state` annotation below is never evaluated at runtime.
    from prompt_toolkit.application import Application

    from mfgparams.console.tui.screens.drilling import DrillingSessionState
    from mfgparams.console.tui.screens.milling import MillingSessionState
    from mfgparams.console.tui.screens.turning import TurningSessionState


# -- 018-tui-splitpane-redesign: UI-state entities (data-model.md) --------
#
# Supersedes 017's `ScreenId`/`NavigationState`, which modeled a mutually-
# exclusive, one-screen-at-a-time dialog chain (each screen its own
# short-lived `Application`). This feature's single persistent `Application`
# can show the menu bar, the Machining tree, and an open operation screen
# all at once, so `SessionUI` below is the single source of truth for that
# instead -- not a stack of "current screen"s.


class FieldId(Enum):
    """Every left-pane field either operation can present (FR-005/FR-009),
    the union across Drilling and Milling -- a screen's own field order
    (data-model.md's `OperationScreen`) selects the subset relevant to its
    operation and current mode, mirroring the pre-plan prototype's own
    field-ordering approach (spec's Recommended Next Steps)."""

    UNIT_SYSTEM = "unit_system"
    MODE = "mode"
    MATERIAL_TYPE = "material_type"
    MATERIAL = "material"
    TOOL = "tool"
    SUB_OPERATION = "sub_operation"
    DIAMETER = "diameter"
    DEPTH = "depth"
    AXIAL_DEPTH_OF_CUT = "axial_depth_of_cut"
    RADIAL_ENGAGEMENT = "radial_engagement"
    FEED_PER_TOOTH = "feed_per_tooth"
    NUMBER_OF_TEETH = "number_of_teeth"
    LENGTH_OF_CUT = "length_of_cut"
    DEPTH_OF_CUT = "depth_of_cut"
    TARGET_RPM = "target_rpm"
    AVAILABLE_POWER = "available_power"
    TARGET_FEED_RATE = "target_feed_rate"


@dataclass(frozen=True)
class MenuBar:
    """FR-001's persistent horizontal bar -- a fixed, closed entry set
    (unlike 017's `run_top_level_menu`, which built a *fresh* entry list per
    screen instance; this one never changes at runtime). Reuses `menu.py`'s
    existing `MenuEntry(value, label)` shape rather than inventing a new
    entry type."""

    entries: tuple[MenuEntry, ...]


@dataclass
class MachiningTree:
    """FR-002's collapsible Milling/Drilling navigation, replacing
    `machining_menu.py`'s full-screen submenu.

    Revised via `/speckit-clarify` (reopened after implementation, per user
    feedback on PR #96 preferring the pre-plan prototype's UI): Drilling's
    tree-level tool-selection sub-expansion is retired (FR-003). Both
    Milling and Drilling are flat leaves -- `expanded` (whether Machining's
    own children are shown at all) is this entity's only field now.
    """

    expanded: bool = False

    def toggle_machining(self) -> None:
        """Acceptance Scenarios 2/4: expand if collapsed; collapse if
        expanded."""

        self.expanded = not self.expanded


@dataclass
class OperationScreen:
    """FR-004's left/right split-pane screen for whichever operation
    (Drilling or Milling, FR-009's identical pattern) is currently open.

    `last_result`/`last_result_key` implement FR-006's "MUST NOT display a
    result computed from a different, no-longer-current set of inputs" as
    a cache keyed on the exact input tuple that produced it (mirroring the
    pre-plan prototype's own `_last_result_key` pattern), not a bare flag.

    `status` mirrors the prototype's own `UI.status`: a transient
    bottom-status-bar message (FR-006b's unparseable-number indication),
    set only when the user tries to navigate away from a field whose typed
    text doesn't parse (`split_pane._commit_current`) -- `None` means show
    the ordinary keyboard hint instead.
    """

    operation: Literal["drilling", "milling", "turning"]
    session_state: DrillingSessionState | MillingSessionState | TurningSessionState
    selected_field: FieldId
    field_buffer: str = ""
    status: str | None = None
    last_result: CalculationResult | None = None
    last_result_key: tuple[object, ...] | None = None


@dataclass
class SessionUI:
    """The single persistent session object `run()` owns for the whole run
    (018-tui-splitpane-redesign), replacing `NavigationState`. `tree` and
    `open_operation` are deliberately independent fields with no code path
    writing both from the same handler (FR-005a's invariant, enforced by
    construction -- see `test_session_ui.py`): collapsing/expanding the
    tree never affects which operation screen is open, and vice versa.
    """

    menu_bar: MenuBar
    tree: MachiningTree = field(default_factory=MachiningTree)
    open_operation: OperationScreen | None = None
    drilling_state: DrillingSessionState = field(default_factory=lambda: _default_drilling_state())
    milling_states: dict[MillingSubOperation, MillingSessionState] = field(
        default_factory=lambda: _default_milling_states()
    )
    turning_state: TurningSessionState = field(default_factory=lambda: _default_turning_state())
    locale: str = "en"
    materials_config_path: str | None = None


def _default_drilling_state() -> DrillingSessionState:
    """Deferred import (see the `TYPE_CHECKING` block above): only called at
    `SessionUI()` construction time, well after both modules have finished
    importing, so this cannot hit the drilling.py<->app.py import cycle a
    module-level import of `DrillingSessionState` would."""

    from mfgparams.console.tui.screens.drilling import DrillingSessionState

    return DrillingSessionState()


def _default_milling_states() -> dict[MillingSubOperation, MillingSessionState]:
    from mfgparams.console.tui.screens.milling import MillingSessionState

    return {sub: MillingSessionState() for sub in MillingSubOperation}


def _default_turning_state() -> TurningSessionState:
    """Deferred import, mirroring `_default_drilling_state` -- turning has
    no sub-operations, so (like drilling) this is a single state object,
    not a dict keyed by sub-operation the way milling's is."""

    from mfgparams.console.tui.screens.turning import TurningSessionState

    return TurningSessionState()


def _resolve_materials_config(materials_config_path: str | None, locale: str) -> None:
    """Validate ``materials_config_path`` once at startup. Ported unchanged
    from `console/cli.py`'s `_resolve_materials_config` (research.md #3):
    raises `SystemExit` (after printing a translated error) if the file
    exists but is malformed, prints a translated non-fatal notice and
    proceeds with bundled defaults if the path is missing/unreadable, and
    does nothing if ``materials_config_path`` is ``None``.
    """

    from mfgparams import (
        list_end_mill_tools,
        list_face_mill_tools,
        list_materials,
        list_tools,
        list_turning_tools,
    )
    from mfgparams.registry import materials_load_notice

    if materials_config_path is None:
        return

    try:
        list_materials(config_path=materials_config_path)
        list_tools(config_path=materials_config_path)
        list_end_mill_tools(config_path=materials_config_path)
        list_face_mill_tools(config_path=materials_config_path)
        list_turning_tools(config_path=materials_config_path)
    except RegistryConfigError as exc:
        print(_translate_core(locale, exc.message_key, **exc.kwargs))
        raise SystemExit(1) from exc

    notice_key, notice_kwargs = materials_load_notice(materials_config_path)
    if notice_key:
        print(_translate_core(locale, notice_key, **dict(notice_kwargs)))


@dataclass
class _ViewState:
    """Which background body is currently shown and which row is
    highlighted within it -- pure UI-presentation state, deliberately
    *not* part of :class:`SessionUI` (which holds session/business state
    that survives a body change, per FR-012). ``body_mode`` names what the
    background body currently renders; it is independent of
    ``SessionUI.tree.expanded``/``open_operation`` (FR-005a) -- e.g.
    selecting Configuration from the bar sets ``body_mode="configuration"``
    without touching either.

    Revised via `/speckit-clarify` (reopened after implementation): an open
    operation screen is no longer a `body_mode` value. It renders as a
    floating window (FR-004, research.md #3) layered *above* the bar/
    background -- entirely independent of `body_mode`.

    Revised again (per direct user feedback on this feature's shipped
    color scheme and bar interaction): `body_mode` no longer selects
    content rendered *inline* below the bar either. Each non-`None` value
    now selects which bar entry's own **floating dropdown/panel** is shown
    -- Machining's tree, Configuration, About, or Help -- positioned just
    under that entry (`build_app`'s per-entry `Float`s), matching a
    typical menu-bar TUI's dropdown behavior, rather than replacing a
    shared inline body area. `None` means no dropdown is open; the bar and
    the blue desktop behind it are all that's shown.
    """

    body_mode: Literal["tree", "configuration", "about", "help"] | None = None
    #: The metal Material selection window's own state (023-material-
    #: selector-dialog), or `None` when it is closed. Lives here rather than
    #: on `OperationScreen` -- it is dialog-open UI state, not session/
    #: business state (mirroring `confirming_exit`/`confirm_selected` above),
    #: and `OperationScreen` is the exact input to `_current_pane_rows`'s own
    #: memoization cache key, which a new field here would have to be added
    #: to as well (research.md Decision 1).
    material_picker: MaterialPickerState | None = None
    bar_selected: int = 0
    tree_selected: int = 0
    #: Whether the Exit confirmation dialog ("Are you sure you want to
    #: exit? Yes/No", per direct user feedback) is currently shown --
    #: independent of `body_mode` since it's triggered by the bar's own
    #: Exit entry, not a dropdown/panel entry.
    confirming_exit: bool = False
    #: Which option is currently highlighted in that dialog; defaults to
    #: "no" so a reflexive Enter/Down press right after selecting Exit
    #: does not itself exit.
    confirm_selected: Literal["yes", "no"] = "no"


def _open_milling(ui: SessionUI, materials_config_path: str | None, display_locale: str) -> None:
    """Opens with whichever sub-operation's state was last active
    (defaulting to End Milling, FR-009a). No longer touches `_ViewState`
    (revision): the floating window's presence is `SessionUI.open_operation`
    alone, independent of what the background body shows (FR-005a)."""

    from mfgparams.console.tui.screens import milling, split_pane

    state = ui.milling_states[MillingSubOperation.END_MILLING]
    screen = OperationScreen(
        operation="milling", session_state=state, selected_field=FieldId.UNIT_SYSTEM
    )
    ui.open_operation = screen
    rows = milling.rows_for(ui, screen, materials_config_path, ui.locale, display_locale)
    split_pane.sync_buffer(rows, screen)


def _open_drilling(
    ui: SessionUI, materials_config_path: str | None, display_locale: str
) -> OperationScreen:
    """Opens on Unit system by default, exactly like Milling (FR-009's
    identical-pattern requirement) -- revised via `/speckit-clarify`: the
    tree no longer has a tool-selection shortcut to land a *different*
    default field on (FR-003 retired). Always creates a fresh
    ``OperationScreen`` wrapper, matching `_open_milling`: the only caller,
    `_activate_tree_row`, requires the tree itself to have focus, which --
    since escaping the operation pane closes it (`ui.open_operation =
    None`) before returning focus to the tree -- means `ui.open_operation`
    is always `None` here already (a code-review pass on PR #96 found the
    previous "reuse if already open" branch this replaced was accordingly
    dead code, with a docstring describing a code path that could no
    longer run). FR-012's actual carryover guarantee lives one level down,
    in `session_state=ui.drilling_state` below: that object -- not this
    wrapper -- is what persists a field's value across a close/reopen."""

    from mfgparams.console.tui.screens import drilling, split_pane

    assert ui.open_operation is None, "Drilling opened while another operation was still open"
    screen = OperationScreen(
        operation="drilling",
        session_state=ui.drilling_state,
        selected_field=FieldId.UNIT_SYSTEM,
    )
    ui.open_operation = screen
    rows = drilling.rows_for(screen, materials_config_path, ui.locale, display_locale)
    split_pane.sync_buffer(rows, screen)
    return screen


def _open_turning(
    ui: SessionUI, materials_config_path: str | None, display_locale: str
) -> OperationScreen:
    """Opens on Unit system by default, identical to Drilling/Milling
    (FR-009's identical-pattern requirement). Structurally identical to
    `_open_drilling` -- turning is a single-subtype process with no
    sub-operation dict to key into (specs/019-turning-calculations
    data-model.md "Structure Decision")."""

    from mfgparams.console.tui.screens import split_pane, turning

    assert ui.open_operation is None, "Turning opened while another operation was still open"
    screen = OperationScreen(
        operation="turning",
        session_state=ui.turning_state,
        selected_field=FieldId.UNIT_SYSTEM,
    )
    ui.open_operation = screen
    rows = turning.rows_for(screen, materials_config_path, ui.locale, display_locale)
    split_pane.sync_buffer(rows, screen)
    return screen


#: `Frame`'s own left+right border columns, added on top of whatever a
#: dropdown's content `Window` requests when computing how much horizontal
#: space it actually needs (`Shadow` draws its shadow marks *outside* the
#: requested box, per its own `__init__`, so it adds nothing to the
#: request). See `_dropdown_float`'s docstring for the underflow this
#: matters for.
_DROPDOWN_FRAME_BORDER_COLUMNS = 2

#: Width bounds for `_dropdown_float`'s four bar-entry-anchored floats
#: (Machining tree, Configuration, About, Help), named at module level --
#: rather than inline at each call site -- specifically so
#: `tests/unit/console/tui/test_dropdown_layout.py`
#: (022-tui-min-size-25x80) can assert each one's `min`, plus
#: `_DROPDOWN_FRAME_BORDER_COLUMNS`, fits within the space actually
#: available at `terminal_capability.MIN_COLUMNS` from that entry's fixed
#: bar offset. Help's `min` is narrower than the other three (36, not 40)
#: because it is the *rightmost* bar entry: manual verification on a real
#: 80x25 terminal found the old `min=40` underflowed by exactly one column
#: at that position, rendering a near-empty dropdown with no legible
#: content -- 36 restores a safety margin rather than merely closing the
#: gap to zero.
_MACHINING_TREE_DROPDOWN_WIDTH = D(min=14, max=22, preferred=18)
_CONFIGURATION_DROPDOWN_WIDTH = D(min=44, max=70, preferred=60)
_ABOUT_DROPDOWN_WIDTH = D(min=40, max=64, preferred=58)
_HELP_DROPDOWN_WIDTH = D(min=36, max=64, preferred=56)


def _bar_entry_offsets(entries: list[MenuEntry]) -> list[int]:
    """The column each bar entry starts at, once rendered by
    `menu.render_menu_bar` -- that function joins entries with a two-space
    separator before every entry but the first, so this mirrors that exact
    spacing. Used to position a bar entry's own dropdown `Float` directly
    under it (`build_app`), the way a typical menu-bar TUI does.

    Uses `get_cwidth` (prompt-toolkit's own per-character display-column
    width, the same measure the terminal renderer uses to lay out each
    fragment) rather than `len()` (a Unicode code-point count): the two
    diverge for wide characters -- CJK glyphs render two columns wide --
    so a translated bar label containing one would make a code-point count
    under-measure that entry's on-screen width, misplacing every dropdown
    to its right by however many wide characters preceded it."""

    offsets: list[int] = []
    x = 0
    for index, entry in enumerate(entries):
        if index > 0:
            x += 2
        offsets.append(x)
        x += sum(get_cwidth(char) for char in entry.label)
    return offsets


def build_app(  # noqa: C901
    materials_config_path: str | None, locale: str, display_locale: str
) -> tuple[Application[None], SessionUI, _ViewState]:
    """Construct the persistent `Application` plus its `SessionUI`/
    `_ViewState`, without running it -- split out from `run()` so tests can
    drive the returned `Application` headlessly (`_tui_test_support.py`'s
    `on_batch` hook, research.md #2) while asserting directly against the
    returned `ui`/`view` objects via pure inspection, not by trying to
    capture rendered terminal output.

    Focus model (018-tui-splitpane-redesign; no direct 017 precedent, and
    iterated several times since on direct user feedback -- see the
    current shape below, not the individual revision history in git blame):
    the bar, each bar entry's own floating dropdown/panel (Machining's
    tree, Configuration, About, Help, each its own `Float`, not a shared
    inline body), the Drilling/Milling operation window, and the Exit
    confirmation dialog are all separate focus regions in one persistent
    `Layout`, not separate `Application`s. Escape closes whichever
    floating window currently has focus and steps focus back exactly one
    level:
    - From a dropdown/panel (or the Exit dialog) -> the bar.
    - From the operation window -> the Machining tree, *focused*, if it is
      still expanded (FR-005a: closing the operation must not touch
      `tree.expanded`) -- "going back" from the operation means going back
      *to* the dropdown it was opened from, not past it to the bare bar,
      per direct user feedback. A second Escape from there closes the
      tree itself and *then* reaches the bar. If the tree was not
      expanded, this step goes straight to the bar instead.
    Up does the same as Escape the instant it would otherwise move within
    a dropdown but there is nowhere left to move to (the top row of
    Machining's tree, or anywhere in a single-block panel like
    Configuration/About/Help, which has no rows to navigate at all) --
    an additional, more direct path back than Escape alone, per user
    feedback. Escape from the bar itself is a defensive fallback for state
    that should no longer be reachable by the time focus gets there (see
    `_escape_bar`'s own comment) and otherwise exits the app (mirroring
    017's own Escape-at-the-root-exits precedent). The bar's own Exit
    entry opens a confirmation dialog rather than exiting directly, per
    user feedback ("ask user... Yes/No").

    Color scheme (revised twice on direct user feedback comparing this
    feature's shipped look to standard/typical blue TUI tools, most
    recently Midnight Commander specifically): the persistent bar
    (`"class:bar"`, cyan) and the desktop behind it (`"class:background"`,
    a distinct, darker blue) are the only two colors that differ from each
    other. Every floating window -- the four dropdowns, the Exit dialog,
    and the Drilling/Milling operation window alike -- shares one
    identical cyan-on-black scheme matching the bar
    (`"class:dialog"`/`"class:dialog.body"`/`"frame.border"`/
    `"frame.label"`, all explicitly redefined below, deliberately
    overriding prompt-toolkit's own built-in defaults), with a solid black
    drop shadow (`"class:shadow"`) under each one. This is a deliberate,
    explicit color-scheme preference for the whole application shell, not
    a prototype-fidelity question -- the pre-plan prototype this feature
    otherwise matches exactly never had a persistent bar/background to be
    consistent with in the first place.
    """

    # noqa: C901 justification -- this is a composition root, not deep
    # logic: it wires ~30 independently-trivial key-binding handlers (each
    # a few lines, no nested branching of its own) around one persistent
    # `Application`'s `ui`/`view`/`app`/`bar_control`/`left_control`/
    # `right_control` closures. Every self-contained decision block that
    # *was* extractable without fragmenting that shared closure state
    # already has been (`split_pane.power_and_rpm_rows`,
    # `milling._tool_registry_for`, the top-level
    # `_open_milling`/`_open_drilling`/`_bar_entry_offsets` helpers, and the
    # per-dropdown render closures declared next to their own controls).
    # Extracting the key-binding registrations themselves would require
    # threading 6+ shared mutable references through new top-level
    # functions (or a mutable-`Application`-ref indirection, since `app`
    # does not exist until after the bindings that close over it are
    # defined) -- net less readable than the current flat,
    # docstring-annotated registration, not more.
    from prompt_toolkit.application import Application
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import (
        ConditionalContainer,
        Float,
        FloatContainer,
        HSplit,
        Layout,
        VSplit,
        Window,
    )
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.dimension import AnyDimension
    from prompt_toolkit.styles import Style
    from prompt_toolkit.widgets import Box, Frame, Shadow

    from mfgparams import list_materials
    from mfgparams.console.i18n import translate
    from mfgparams.console.tui import forms, machining_menu, material_picker
    from mfgparams.console.tui.menu import _assign_mnemonics, default_entries, render_menu_bar
    from mfgparams.console.tui.screens import drilling, milling, split_pane, turning
    from mfgparams.console.tui.screens.about import render_about
    from mfgparams.console.tui.screens.configuration import render_configuration
    from mfgparams.console.tui.screens.help import render_help
    from mfgparams.registry import WorkpieceMaterial, get_material

    bar_entries = default_entries(locale)
    bar_mnemonics = _assign_mnemonics(bar_entries)
    # Static for the whole session (labels/order are fixed once `locale` is
    # resolved at startup, unaffected by anything the user does at
    # runtime): used below to position each dropdown-opening entry's own
    # `Float` directly under it, the way a typical menu-bar TUI does.
    bar_offsets = _bar_entry_offsets(bar_entries)
    bar_entry_index = {entry.value: index for index, entry in enumerate(bar_entries)}
    ui = SessionUI(
        menu_bar=MenuBar(entries=tuple(bar_entries)),
        locale=locale,
        materials_config_path=materials_config_path,
    )
    view = _ViewState()

    # "error"/"pane-title" match the prototype's own `_STYLE` exactly
    # (`prototype_drilling_splitpane.py`/`prototype_milling_splitpane.py`).
    # Everything else here is this feature's own color scheme, revised per
    # direct user feedback to match a typical blue-scheme TUI. Every
    # floating window -- the four bar-entry dropdowns, the Exit
    # confirmation dialog, and the Drilling/Milling operation window alike
    # -- now shares one identical cyan-on-black scheme, matching the bar's
    # own shade (per user feedback: "milling and drilling floating windows
    # ... should follow the same colour scheme as sub-menu drop downs");
    # only the blue desktop behind the bar stays a distinct, darker shade.
    style = Style.from_dict(
        {
            "mnemonic": "fg:#ffff00 underline bold",
            "selected": "reverse",
            "hint": "italic",
            "error": "fg:ansired bold",
            "pane-title": "bold underline",
            # The desktop behind the bar -- everything not covered by the
            # bar itself or a floating window.
            "background": "bg:#0000aa fg:#ffffff",
            # The persistent bar row, and (below) every floating window --
            # one shared shade, per direct user feedback.
            "bar": "bg:#00aaaa fg:#000000",
            # Every floating window (the four bar-entry dropdowns, the Exit
            # confirmation dialog, and the Drilling/Milling operation
            # window): "dialog" is the thin outer margin `Box` draws around
            # the operation window when centered (only it uses `Box`; the
            # rest skip it for a snugger fit); "dialog.body"/
            # "frame.border"/"frame.label" are `Frame`'s own
            # body/border/title classes, shared by all of them.
            "dialog": "bg:#00aaaa",
            "dialog.body": "bg:#00aaaa fg:#000000",
            "frame.border": "fg:#000000 bg:#00aaaa",
            "frame.label": "fg:#ffff00 bg:#00aaaa bold",
            # A crisp, dark drop-shadow beneath every floating window --
            # Midnight-Commander-style, per direct user feedback -- rather
            # than a shade too close to the surrounding blue/cyan to read
            # clearly as a shadow.
            "shadow": "bg:#000000",
        }
    )

    # `show_cursor=False` on every focusable control below: without it, a
    # focusable `FormattedTextControl` parks the real terminal cursor at
    # (0, 0) of its own text by default -- landing on each one's first
    # character and rendering as a stray highlighted cell (the same
    # artifact already fixed for `left_control`, and per user feedback:
    # "first character is highlighted -- remove it").
    bar_control = FormattedTextControl(
        lambda: render_menu_bar(bar_entries, bar_mnemonics, view.bar_selected, focused=on_bar()),
        focusable=True,
        show_cursor=False,
    )

    def _render_tree() -> StyleAndTextTuples:
        return machining_menu.render_tree(
            ui.tree, view.tree_selected, ui.locale, focused=app.layout.has_focus(tree_control)
        )

    def _render_configuration() -> StyleAndTextTuples:
        return render_configuration(ui.materials_config_path, ui.locale, display_locale)

    def _render_about() -> StyleAndTextTuples:
        return render_about(ui.locale)

    def _render_help() -> StyleAndTextTuples:
        return render_help(ui.locale)

    def _render_exit_confirm() -> StyleAndTextTuples:
        message = translate(ui.locale, "tui.exit_confirm.message")
        yes_label = translate(ui.locale, "tui.exit_confirm.yes")
        no_label = translate(ui.locale, "tui.exit_confirm.no")
        yes_style = "class:selected" if view.confirm_selected == "yes" else ""
        no_style = "class:selected" if view.confirm_selected == "no" else ""
        return [
            ("", f"{message}\n\n"),
            (yes_style, f" {yes_label} "),
            ("", "   "),
            (no_style, f" {no_label} "),
        ]

    # Each bar entry that opens a dropdown/panel (Machining, Configuration,
    # About, Help) gets its own focusable control and, below, its own
    # `Float` positioned just under that entry (revision: these used to
    # share one inline `body_control` below the bar; now each is a
    # standalone floating window, matching a typical menu-bar TUI's
    # dropdown behavior per direct user feedback). Exit's own confirmation
    # dialog (per direct user feedback: "are you sure? Yes/No") is built
    # the same way, positioned under the Exit entry itself.
    tree_control = FormattedTextControl(_render_tree, focusable=True, show_cursor=False)
    configuration_control = FormattedTextControl(
        _render_configuration, focusable=True, show_cursor=False
    )
    about_control = FormattedTextControl(_render_about, focusable=True, show_cursor=False)
    help_control = FormattedTextControl(_render_help, focusable=True, show_cursor=False)
    exit_confirm_control = FormattedTextControl(
        _render_exit_confirm, focusable=True, show_cursor=False
    )

    def on_bar() -> bool:
        return app.layout.has_focus(bar_control)

    def on_pane() -> bool:
        """Whether the floating operation window's left pane specifically
        has focus -- distinct from `on_bar()`'s negation, since
        `_ViewState.body_mode` can independently be `"tree"` *while* an
        operation is open (the float doesn't touch it, revision), so
        `not on_bar()` alone can no longer tell the tree and the float
        apart the way it could when they were mutually exclusive
        `body_mode` values."""

        return app.layout.has_focus(left_control)

    def _current_tree_row_count() -> int:
        return len(machining_menu.tree_rows(ui.tree))

    # `_current_pane_rows()`'s single-entry cache below: a code-review pass
    # on PR #96 found this getting called up to 5x per keystroke in the
    # operation pane (once or twice per key-binding `Condition` filter
    # checked for that key -- `pane_radio_focused`/`pane_numeric_focused`
    # each call it independently -- once by whichever handler matches, and
    # twice more from the subsequent left/right pane re-renders), each call
    # rebuilding the full row list (registry lookups, `translate()` calls,
    # `unique_labels()`). None of those calls happen concurrently with a
    # mutation (state only ever changes inside a key-binding handler, never
    # during filter evaluation or rendering), so caching by a cheap
    # fingerprint of everything the row list can depend on is safe: a full
    # close/reopen creates a new `OperationScreen` (`id(op)` changes), and
    # any in-place change to `selected_field`/`field_buffer`/a
    # `session_state` field/`ui.locale` changes the key too. `id(op.
    # session_state)` is included *in addition to* a value snapshot of its
    # fields, not instead of one: a round-2 code-review pass on PR #96
    # found that a value-only key misses Milling's own sub-operation switch
    # (`screens/milling.py`'s `_set_sub_operation` reassigns
    # `screen.session_state` to a *different* `MillingSessionState` object
    # -- End Milling's vs. Face Milling's own -- and the two start with
    # identical default field values, so a value-only snapshot couldn't
    # tell them apart and kept serving the stale sub-operation's rows).
    _pane_rows_cache_key: object = None
    _pane_rows_cache_value: list[split_pane.Row] = []

    def _current_pane_rows() -> list[split_pane.Row]:
        """The open operation's `split_pane.Row` list -- a row's presence/
        options can depend on another row's just-committed value (T021's
        `rows_for` docstring), so this must still reflect the *current*
        state on every call; it just avoids recomputing when nothing that
        could change the result has changed since the last call."""

        nonlocal _pane_rows_cache_key, _pane_rows_cache_value
        op = ui.open_operation
        if op is None:
            return []
        cache_key = (
            id(op),
            id(op.session_state),
            op.selected_field,
            op.field_buffer,
            tuple(vars(op.session_state).items()),
            ui.locale,
        )
        if cache_key == _pane_rows_cache_key:
            return _pane_rows_cache_value
        if op.operation == "drilling":
            rows = drilling.rows_for(op, materials_config_path, ui.locale, display_locale)
        elif op.operation == "turning":
            rows = turning.rows_for(op, materials_config_path, ui.locale, display_locale)
        else:
            rows = milling.rows_for(ui, op, materials_config_path, ui.locale, display_locale)
        _pane_rows_cache_key = cache_key
        _pane_rows_cache_value = rows
        return rows

    def _render_left_pane() -> StyleAndTextTuples:
        op = ui.open_operation
        assert op is not None
        return split_pane.render_left_pane(
            _current_pane_rows(),
            op,
            translate(ui.locale, "tui.pane.inputs"),
            ui.locale,
            focused=on_pane(),
        )

    def _render_bottom_bar() -> StyleAndTextTuples:
        op = ui.open_operation
        assert op is not None
        return split_pane.render_bottom_bar(op, ui.locale)

    def _calculate_current_operation() -> CalculationResult:
        op = ui.open_operation
        assert op is not None
        if op.operation == "drilling":
            return drilling.calculate_result(
                cast("DrillingSessionState", op.session_state), materials_config_path, ui.locale
            )
        if op.operation == "turning":
            return turning.calculate_result(
                cast("TurningSessionState", op.session_state), materials_config_path, ui.locale
            )
        return milling.calculate_result(
            ui, cast("MillingSessionState", op.session_state), materials_config_path, ui.locale
        )

    def _render_right_pane() -> StyleAndTextTuples:
        op = ui.open_operation
        assert op is not None
        labels = forms.UNIT_LABELS[op.session_state.unit_system]
        placeholder_key = {
            "drilling": "tui.drilling.placeholder",
            "milling": "tui.milling.placeholder",
            "turning": "tui.turning.placeholder",
        }[op.operation]
        return split_pane.render_right_pane(
            _current_pane_rows(),
            op,
            _calculate_current_operation,
            labels,
            ui.locale,
            placeholder=translate(ui.locale, placeholder_key),
        )

    # `show_cursor=False`: a focusable `FormattedTextControl` otherwise parks
    # the real terminal cursor at (0,0) of its own text by default, landing
    # on the first letter of "Inputs" and rendering as a stray highlighted
    # character -- selection is already shown via the reverse-video row
    # style, and a typed number's cursor via `render_left_pane`'s own
    # trailing "_" (matching the prototype's `main()` exactly).
    left_control = FormattedTextControl(_render_left_pane, focusable=True, show_cursor=False)
    right_control = FormattedTextControl(_render_right_pane, focusable=False)
    bottom_control = FormattedTextControl(_render_bottom_bar)

    def _operation_title() -> str:
        # Asserting (rather than falling back to "") is safe, not merely
        # convenient: `operation_window` only ever renders inside the
        # `ConditionalContainer` below, filtered on `ui.open_operation is
        # not None`, and `ConditionalContainer.write_to_screen`/
        # `preferred_width`/`preferred_height` all check that filter
        # *before* ever descending into its content -- verified against
        # prompt-toolkit's own source, not assumed -- so this callable is
        # never invoked while `ui.open_operation` is `None`. (A round-2
        # code-review pass on PR #96 flagged an earlier "return ''"
        # fallback here as ineffective for its own stated purpose anyway:
        # `Frame`'s `has_title` Condition checks `bool(self.title)` against
        # this *callable itself*, which is always truthy, regardless of
        # what calling it would return -- so an empty-string fallback could
        # never have made `has_title()` false in the first place. Since the
        # only reachable case is `ui.open_operation is not None`, where the
        # title is always genuinely non-empty, `has_title() == True` is
        # simply correct here, not a mismatch to work around.)
        op = ui.open_operation
        assert op is not None
        key = {
            "drilling": "tui.drilling.title",
            "milling": "tui.milling.title",
            "turning": "tui.turning.title",
        }[op.operation]
        return translate(ui.locale, key)

    # FR-004 (revised via `/speckit-clarify`, reopened after implementation,
    # rebuilt to match the pre-plan prototype's `main()` exactly): a
    # centered, bordered, shadowed floating window over the persistent bar
    # and background body (research.md #3's `FloatContainer`/`Float`
    # construction) -- not an embedded pane replacing them.
    #
    # Combined width floored at 75 chars (30 + divider + 45 at minimum),
    # split 40/60 between the two panes throughout the whole min-max range
    # -- the prototype's own `left_width`/`right_width` `Dimension`s.
    # Milling's taller field list needs a taller panes row than Drilling's,
    # so this doesn't fix a `height` here the way the prototype's two
    # separate scripts each did with their own single `D(...)` -- the height
    # is left to each pane's own preferred size instead.
    panes = VSplit(
        [
            Window(content=left_control, width=D(min=30, max=36, preferred=30), wrap_lines=True),
            Window(width=1, char="│"),
            # FR-018: prompt-toolkit's own `Window` default is
            # `wrap_lines=False` -- without this, a result line longer than
            # the pane's width would overflow/truncate instead of wrapping.
            Window(content=right_control, width=D(min=45, max=54, preferred=45), wrap_lines=True),
        ]
    )
    # The status/hint row: its own full-width row below a horizontal
    # divider, spanning both columns -- a merged cell under the two-column
    # table, not part of either pane (matching the prototype's `render_bottom`
    # placement exactly). Capped at 2 lines so it can't stretch to soak up
    # leftover vertical space; it only ever needs 1.
    operation_body = HSplit(
        [
            panes,
            Window(height=1, char="─"),
            Window(content=bottom_control, height=D(min=1, max=2, preferred=1), wrap_lines=True),
        ]
    )
    # `title=_operation_title` passes the callable itself, not its return
    # value: `Frame`'s title `Label` re-invokes whatever `self.title` holds
    # fresh on every render (`AnyFormattedText` supports a zero-argument
    # callable, resolved by `to_formatted_text`/`Template.format` at draw
    # time). Fixes a real staleness bug an earlier revision had: mutating
    # `operation_window.title = _operation_title()` from inside
    # `_render_left_pane` set the string too late, since `Frame` draws its
    # title row *before* descending into the body's `DynamicContainer`
    # that contains the left pane -- the title bar showed the *previous*
    # render's value (blank on first open) for one frame every time.
    operation_window = Frame(body=operation_body, title=_operation_title, style="class:dialog.body")

    # Windows for the panels that can outgrow the screen (Configuration in
    # particular: a user-supplied `--materials-config` can register far
    # more categories/materials than fit in one terminal height) are kept
    # here, keyed by `body_mode`, so the Up/Down bindings below can reach
    # each one's own `vertical_scroll` -- a plain mutable `int` attribute
    # prompt-toolkit clamps to the content's actual extent during its own
    # `write_to_screen` pass, so scrolling past either end is a no-op
    # rather than something this code has to bound itself.
    scrollable_dropdown_windows: dict[str, Window] = {}

    def _dropdown_float(
        control: FormattedTextControl,
        mode: str,
        bar_value: str,
        *,
        width: AnyDimension = None,
    ) -> Float:
        """One bar entry's own floating dropdown/panel -- positioned just
        under that entry (`bar_offsets[bar_entry_index[bar_value]]`), shown
        only while `body_mode` equals `mode` (`bar_value` and `mode` differ
        for Machining: the bar entry is `"machining"`, but `body_mode`'s
        value for its tree is `"tree"`, unchanged from before this
        revision). Deliberately skips the operation window's outer `Box`
        margin (below) for a snugger, more typical dropdown fit.

        022-tui-min-size-25x80: the docstring here previously claimed this
        stays trigger-relative-`left`-anchored width "never overflows even
        on an 80-column terminal". Manual verification at exactly 80
        columns (this feature's own floor) found that claim false for
        Help specifically: Help is the *rightmost* bar entry, so its
        float's `left` (its bar offset, 39) leaves only 41 columns before
        the screen edge, and `Frame`'s own left+right border adds exactly
        2 more columns of overhead on top of whatever `width` asks for
        (`Shadow` draws outside the requested box and adds nothing to the
        request) -- with the old `width=D(min=40, ...)`, that is 42
        columns needed against 41 available, an underflow by exactly one
        column, and the window rendered squeezed to near-nothing with no
        legible content.

        An earlier revision of this fix right-aligned Help's float to the
        screen's right edge unconditionally -- Copilot review on this PR
        correctly flagged that as trading one bug for another: on any
        terminal wider than ~80 columns, that pinned Help's dropdown to
        the far right edge regardless of the bar entry's own (unmoved,
        left-packed) position, visibly detaching the dropdown from its
        trigger for every terminal above the floor, not just fixing the
        one at it. Since this float only ever anchors via a fixed `left`
        (never conditionally repositioned) and a wider terminal only ever
        *increases* the space to its right, the true minimum-columns case
        is the only one that can underflow; each call site's own `width`
        floor is chosen so the requested minimum (its `min` plus this
        function's constant +2 `Frame`-border overhead) fits within the
        space actually available at `MIN_COLUMNS` (80) from that entry's
        fixed offset -- Help's alone had to shrink (see its call site
        below) since it is the only one close enough to the right edge to
        matter; the position itself never has to move, at any width."""

        window = Window(content=control, wrap_lines=True, width=width)
        scrollable_dropdown_windows[mode] = window
        return Float(
            left=bar_offsets[bar_entry_index[bar_value]],
            # Row 1 -- directly below the bar (row 0), per direct user
            # feedback: "top horizontal line of floating sub-menu window
            # should be just below menu". There is no divider row between
            # them any more (the one that used to occupy row 1 is removed
            # below, also per feedback), so row 1 is the first free row.
            top=1,
            content=ConditionalContainer(
                content=Shadow(Frame(body=window, style="class:dialog.body")),
                filter=Condition(lambda: view.body_mode == mode),
            ),
        )

    # The metal Material selection window (023-material-selector-dialog,
    # FR-001/FR-012): centered, bordered, shadowed, matching
    # `operation_window`'s own centering pattern -- unlike the bar-entry
    # dropdowns/Exit-confirm above, it is not anchored to a bar entry, since
    # it opens from a row *inside* the already-open operation window.
    def _open_metal_materials() -> list[WorkpieceMaterial]:
        """The current operation's metal-material list, mirroring
        `drilling.py`'s own Material-row option-building exactly. Assumes an
        operation is open -- only ever called from contexts already gated
        that way (`pane_material_picker_trigger`/`material_picker_focused`)."""

        names = list_materials(materials_config_path, material_type="metal")
        materials = [get_material(name, materials_config_path) for name in names]
        return [item for item in materials if item is not None]

    def _material_picker_candidates() -> list[WorkpieceMaterial]:
        """The dialog's current candidate list: `_open_metal_materials()`
        filtered by `material_picker.candidates()` against whichever
        queries are wired up so far (User Story 1 onward, tasks.md T022)."""

        state = view.material_picker
        assert state is not None
        return material_picker.candidates(state, _open_metal_materials(), display_locale)

    def _render_material_picker() -> StyleAndTextTuples:
        state = view.material_picker
        assert state is not None
        return material_picker.render(
            state, _material_picker_candidates(), ui.locale, display_locale
        )

    material_picker_control = FormattedTextControl(
        _render_material_picker, focusable=True, show_cursor=False
    )
    material_picker_float = Float(
        content=ConditionalContainer(
            content=Box(
                body=Shadow(
                    Frame(
                        body=Window(content=material_picker_control, wrap_lines=True),
                        style="class:dialog.body",
                    )
                ),
                style="class:dialog",
            ),
            filter=Condition(lambda: view.material_picker is not None),
        )
    )

    # Exit's own confirmation dialog -- "are you sure you want to exit?
    # Yes/No", per direct user feedback, shown instead of exiting
    # immediately. Positioned under the Exit entry itself, the same way
    # every other bar entry's own floating window is.
    exit_confirm_float = Float(
        left=bar_offsets[bar_entry_index["exit"]],
        top=1,
        content=ConditionalContainer(
            content=Shadow(
                Frame(
                    body=Window(
                        content=exit_confirm_control, width=D(min=30, max=40), wrap_lines=True
                    ),
                    style="class:dialog.body",
                )
            ),
            filter=Condition(lambda: view.confirming_exit),
        ),
    )

    root = FloatContainer(
        content=HSplit(
            [
                Window(content=bar_control, height=1, style="class:bar"),
                # No divider row here (removed per direct user feedback:
                # "remove horizontal line below the menu") -- the blue
                # desktop below starts immediately under the bar. Every
                # bar-entry dropdown/panel is a `Float` layered above this
                # desktop Window, not inline content here, so it carries no
                # content control of its own, only the background
                # fill/style.
                Window(style="class:background", char=" "),
            ],
            style="class:background",
        ),
        floats=[
            # Machining's tree is the one dropdown with its own navigable
            # rows, so it stays narrow/compact (`Milling`/`Drilling`).
            # About/Help/Configuration are each one block of prose/listing
            # text with no pre-wrapped line breaks of their own (Help in
            # particular is a single ~220-character paragraph) -- an
            # explicit width bound here gives each a readable, book-page-ish
            # wrap rather than stretching edge-to-edge to whatever's left of
            # the screen, which unbounded auto-sizing would otherwise do.
            _dropdown_float(
                tree_control, "tree", "machining", width=_MACHINING_TREE_DROPDOWN_WIDTH
            ),
            _dropdown_float(
                configuration_control,
                "configuration",
                "configuration",
                width=_CONFIGURATION_DROPDOWN_WIDTH,
            ),
            _dropdown_float(about_control, "about", "about", width=_ABOUT_DROPDOWN_WIDTH),
            _dropdown_float(help_control, "help", "help", width=_HELP_DROPDOWN_WIDTH),
            exit_confirm_float,
            Float(
                content=ConditionalContainer(
                    content=Box(body=Shadow(operation_window), style="class:dialog"),
                    filter=Condition(lambda: ui.open_operation is not None),
                )
            ),
            material_picker_float,
        ],
    )

    def _activate_bar_entry() -> None:
        entry = bar_entries[view.bar_selected]
        if entry.value == "exit":
            # Per direct user feedback: confirm before exiting, rather than
            # exiting immediately.
            view.confirming_exit = True
            view.confirm_selected = "no"
            app.layout.focus(exit_confirm_control)
        elif entry.value == "machining":
            ui.tree.toggle_machining()
            if ui.tree.expanded:
                view.body_mode = "tree"
                view.tree_selected = 0
                app.layout.focus(tree_control)
            elif view.body_mode == "tree":
                view.body_mode = None
        elif entry.value == "configuration":
            view.body_mode = "configuration"
            app.layout.focus(configuration_control)
        elif entry.value == "about":
            view.body_mode = "about"
            app.layout.focus(about_control)
        elif entry.value == "help":
            view.body_mode = "help"
            app.layout.focus(help_control)

    def _activate_tree_row() -> None:
        """Both tree leaves open their floating window directly (FR-002/
        FR-003 retired) -- no more toggle/shortcut action to dispatch on.

        `view.body_mode = None` below hides the Machining tree dropdown
        (whose own visibility is gated on `body_mode == "tree"`,
        `_dropdown_float`) once an operation opens; the Escape handlers'
        existing restore logic brings it back on exit unchanged. See
        specs/021-turning-combined-constraints research.md #9 for the
        full rationale."""

        rows = machining_menu.tree_rows(ui.tree)
        row = rows[view.tree_selected]
        if row.action == "open_milling":
            _open_milling(ui, materials_config_path, display_locale)
        elif row.action == "open_turning":
            _open_turning(ui, materials_config_path, display_locale)
        else:
            _open_drilling(ui, materials_config_path, display_locale)
        view.body_mode = None
        app.layout.focus(left_control)

    bindings = KeyBindings()

    @bindings.add("escape", filter=Condition(on_bar))
    def _escape_bar(event) -> None:
        # By the time any escape reaches the bar, `_escape_body` below has
        # already closed whatever floating window (operation or dropdown)
        # was open on the way here, and -- since closing the operation now
        # returns focus to the tree rather than the bar when the tree is
        # still expanded (see `_escape_body`) -- `body_mode` can no longer
        # be `"tree"` while focus is already on the bar either. This `if`
        # is now a defensive fallback for that invariant, not a normally-
        # reached path; kept rather than deleted since it is still correct
        # if ever reached.
        if ui.open_operation is not None:
            ui.open_operation = None
            view.body_mode = "tree" if ui.tree.expanded else None
        else:
            event.app.exit()

    # Excludes the Exit confirmation dialog and the metal Material selection
    # window: both get their own dedicated Escape binding
    # (`_exit_confirm_cancel`/`_material_picker_cancel`), distinct from
    # every other floating window since neither has a `body_mode`/
    # `on_pane()` state of its own to fall back on -- just
    # `view.confirming_exit`/`view.material_picker` (research.md Decision 4:
    # without this exclusion, Escape inside the material picker would hit
    # this handler's `else` branch and jump focus all the way to the bar,
    # past the still-open operation window underneath).
    @bindings.add(
        "escape",
        filter=Condition(
            lambda: not on_bar() and not view.confirming_exit and view.material_picker is None
        ),
    )
    def _escape_body(event) -> None:
        # Escaping any open floating window -- the Drilling/Milling
        # operation window, or a bar entry's own dropdown/panel (Machining's
        # tree, Configuration, About, Help) -- closes/erases it outright,
        # per direct user feedback ("each time user exits floating window
        # it should be erased/removed"): a single Escape now closes it, not
        # just moves focus off it while it lingers, unfocused, underneath.
        if on_pane():
            ui.open_operation = None
            # Acceptance Scenario 5: "land back at the menu bar/tree", not a
            # blank body -- if the tree is still expanded (FR-005a: closing
            # the operation must not touch that), "going back" from the
            # operation means going back *to* the still-open Machining
            # dropdown, focused and ready to navigate again -- not past it
            # to the bare bar (per direct user feedback: "when escaping
            # from machining/drilling cursor should be back to sub-menu").
            # A second Escape from there (now `tree_focused`, handled
            # below) closes the dropdown itself and *then* reaches the bar.
            if ui.tree.expanded:
                view.body_mode = "tree"
                event.app.layout.focus(tree_control)
                return
            view.body_mode = None
        else:
            # Closing a bar entry's own dropdown/panel outright. For the
            # Machining tree specifically, this also collapses
            # `tree.expanded` back to its default -- keeping it in lockstep
            # with whether the dropdown is actually visible, so a later
            # "m"/Down on the bar reopens it in one press rather than
            # silently toggling an already-invisible "expanded" flag closed
            # first (the reported "press Down twice to expand Machining"
            # bug: `toggle_machining()` flipped `tree.expanded` True->False
            # on the first press, since it had been left `True` here even
            # though the dropdown was no longer shown, so nothing visibly
            # happened until a second press flipped it back to `True`).
            if view.body_mode == "tree":
                ui.tree.expanded = False
            view.body_mode = None
        event.app.layout.focus(bar_control)

    exit_confirm_focused = Condition(
        lambda: view.confirming_exit and app.layout.has_focus(exit_confirm_control)
    )

    @bindings.add("escape", filter=exit_confirm_focused)
    @bindings.add("n", filter=exit_confirm_focused)
    def _exit_confirm_cancel(event) -> None:
        view.confirming_exit = False
        event.app.layout.focus(bar_control)

    @bindings.add("y", filter=exit_confirm_focused)
    def _exit_confirm_yes(event) -> None:
        event.app.exit()

    @bindings.add("left", filter=exit_confirm_focused)
    @bindings.add("h", filter=exit_confirm_focused)
    @bindings.add("right", filter=exit_confirm_focused)
    @bindings.add("l", filter=exit_confirm_focused)
    def _exit_confirm_toggle(event) -> None:
        view.confirm_selected = "no" if view.confirm_selected == "yes" else "yes"

    @bindings.add("enter", filter=exit_confirm_focused)
    @bindings.add(" ", filter=exit_confirm_focused)
    def _exit_confirm_activate(event) -> None:
        if view.confirm_selected == "yes":
            event.app.exit()
        else:
            view.confirming_exit = False
            event.app.layout.focus(bar_control)

    @bindings.add("left", filter=Condition(on_bar))
    @bindings.add("h", filter=Condition(on_bar))
    def _bar_left(event) -> None:
        view.bar_selected = (view.bar_selected - 1) % len(bar_entries)

    @bindings.add("right", filter=Condition(on_bar))
    @bindings.add("l", filter=Condition(on_bar))
    def _bar_right(event) -> None:
        view.bar_selected = (view.bar_selected + 1) % len(bar_entries)

    @bindings.add("enter", filter=Condition(on_bar))
    @bindings.add("down", filter=Condition(on_bar))
    @bindings.add("j", filter=Condition(on_bar))
    def _bar_enter(event) -> None:
        # Down/j activates the highlighted bar entry exactly like Enter --
        # per user feedback, the natural "descend into" gesture for a
        # horizontal menu bar (matching typical menu-bar TUIs/GUIs, where
        # Down opens the highlighted top-level item's own dropdown).
        _activate_bar_entry()

    for index, mnemonic in enumerate(bar_mnemonics):
        if mnemonic is None:
            continue

        def _bar_jump(event, target_index: int = index) -> None:
            view.bar_selected = target_index
            _activate_bar_entry()

        bindings.add(mnemonic, filter=Condition(on_bar))(_bar_jump)

    tree_focused = Condition(
        lambda: view.body_mode == "tree" and app.layout.has_focus(tree_control)
    )

    @bindings.add("up", filter=tree_focused)
    @bindings.add("k", filter=tree_focused)
    def _tree_up(event) -> None:
        # Up at the first row returns focus to the bar (per user feedback)
        # rather than wrapping to the last row -- the same convention a
        # typical dropdown menu uses; Down at the last row still wraps
        # (unchanged, below), so wraparound isn't lost entirely, only the
        # "escape upward" direction gets this more direct path back out.
        # Also closes the dropdown (matching `_escape_body` above) so it
        # disappears rather than lingering unfocused-but-visible, and
        # collapses `tree.expanded` in step with it (same "press Down
        # twice to reopen" bug `_escape_body`'s comment explains).
        if view.tree_selected == 0:
            ui.tree.expanded = False
            view.body_mode = None
            app.layout.focus(bar_control)
            return
        view.tree_selected -= 1

    @bindings.add("down", filter=tree_focused)
    @bindings.add("j", filter=tree_focused)
    def _tree_down(event) -> None:
        view.tree_selected = (view.tree_selected + 1) % _current_tree_row_count()

    @bindings.add("enter", filter=tree_focused)
    def _tree_enter(event) -> None:
        _activate_tree_row()

    @bindings.add(Keys.Any, filter=tree_focused)
    def _tree_mnemonic(event) -> None:
        """Contract §4: tree leaves get mnemonics too, same as the bar's
        own entries -- but unlike the bar's fixed entry set, this can't be
        a fixed per-character binding assigned once at startup the way the
        bar's are (the tree's own rows are recomputed fresh every render,
        matching every other row-based widget in this module); it
        re-derives the current rows'/mnemonics' mapping on every keypress
        and only acts if the pressed key matches one."""

        rows = machining_menu.tree_rows(ui.tree)
        mnemonics = machining_menu.tree_mnemonics(rows, ui.locale)
        pressed = event.data.lower()
        for index, mnemonic in enumerate(mnemonics):
            if mnemonic == pressed:
                view.tree_selected = index
                _activate_tree_row()
                return

    # Configuration/About/Help have no navigable rows of their own -- each
    # is a single static block -- so Down scrolls further into it while
    # there's more to see, and Up scrolls back up while there's scroll
    # position to give up. Only once a panel is already scrolled to its
    # very top does Up fall through to "get back to the menu bar" (the
    # same request the tree's own top-row Up above satisfies), closing the
    # panel on the way out (matching `_escape_body`/`_tree_up`). This
    # matters in practice for Configuration: a user-supplied
    # `--materials-config` can list more categories/materials than fit in
    # one terminal height, and Up closing the panel immediately (its
    # original behavior) left no way to read the rest of a long listing.
    configuration_focused = Condition(
        lambda: view.body_mode == "configuration" and app.layout.has_focus(configuration_control)
    )
    about_focused = Condition(
        lambda: view.body_mode == "about" and app.layout.has_focus(about_control)
    )
    help_focused = Condition(
        lambda: view.body_mode == "help" and app.layout.has_focus(help_control)
    )

    @bindings.add("down", filter=configuration_focused)
    @bindings.add("down", filter=about_focused)
    @bindings.add("down", filter=help_focused)
    def _dropdown_scroll_down(event) -> None:
        assert view.body_mode is not None
        scrollable_dropdown_windows[view.body_mode].vertical_scroll += 1

    @bindings.add("up", filter=configuration_focused)
    @bindings.add("up", filter=about_focused)
    @bindings.add("up", filter=help_focused)
    def _dropdown_up_to_bar(event) -> None:
        assert view.body_mode is not None
        window = scrollable_dropdown_windows[view.body_mode]
        if window.vertical_scroll > 0:
            window.vertical_scroll -= 1
            return
        view.body_mode = None
        event.app.layout.focus(bar_control)

    def _pane_is_focused() -> bool:
        return ui.open_operation is not None and on_pane()

    pane_focused = Condition(_pane_is_focused)

    def _current_pane_row() -> split_pane.Row | None:
        if ui.open_operation is None:
            return None
        return split_pane.selected_row(_current_pane_rows(), ui.open_operation)

    def _is_metal_material_row(row: split_pane.Row | None) -> bool:
        """Whether `row` is the metal Material row (023-material-selector-
        dialog): Enter opens the dedicated selection window on it, *in
        addition to* Left/Right/Space still cycling it one-by-one like any
        other radio row (per direct user feedback -- both paths stay
        available, rather than Enter replacing the cycle entirely)."""

        if not isinstance(row, split_pane.RadioRow) or row.field_id is not FieldId.MATERIAL:
            return False
        op = ui.open_operation
        return op is not None and op.session_state.material_type == "metal"

    pane_radio_focused = Condition(
        lambda: _pane_is_focused() and isinstance(_current_pane_row(), split_pane.RadioRow)
    )
    pane_numeric_focused = Condition(
        lambda: _pane_is_focused() and isinstance(_current_pane_row(), split_pane.NumberRow)
    )
    pane_material_picker_trigger = Condition(
        lambda: _pane_is_focused() and _is_metal_material_row(_current_pane_row())
    )

    # Up/Down (and j/k) always move between fields, unconditionally,
    # regardless of the current field's type -- matching the prototype's
    # `move_selection` exactly. There is no "expanded radio" state to
    # navigate within any more (radio fields are always a single line,
    # cycled with Left/Right/Space below), so no per-type dispatch is
    # needed here at all.
    @bindings.add("up", filter=pane_focused)
    @bindings.add("k", filter=pane_focused)
    def _pane_up(event) -> None:
        assert ui.open_operation is not None
        split_pane.move_selection(_current_pane_rows(), ui.open_operation, -1, ui.locale)

    @bindings.add("down", filter=pane_focused)
    @bindings.add("j", filter=pane_focused)
    def _pane_down(event) -> None:
        assert ui.open_operation is not None
        split_pane.move_selection(_current_pane_rows(), ui.open_operation, 1, ui.locale)

    # Left/Right (bare arrow keys) act on whichever field is selected --
    # cycling a radio field's value, or nudging a numeric one -- matching
    # the prototype's two separately-filtered bindings for the same keys.
    # h/l/Space are radio-only (the prototype's own comment: "Space has no
    # numeric-field meaning").
    @bindings.add("left", filter=pane_radio_focused)
    @bindings.add("h", filter=pane_radio_focused)
    def _pane_cycle_left(event) -> None:
        assert ui.open_operation is not None
        split_pane.nudge_selected(_current_pane_rows(), ui.open_operation, -1)

    @bindings.add("right", filter=pane_radio_focused)
    @bindings.add("l", filter=pane_radio_focused)
    @bindings.add(" ", filter=pane_radio_focused)
    def _pane_cycle_right(event) -> None:
        assert ui.open_operation is not None
        split_pane.nudge_selected(_current_pane_rows(), ui.open_operation, 1)

    @bindings.add("left", filter=pane_numeric_focused)
    def _pane_nudge_down(event) -> None:
        assert ui.open_operation is not None
        split_pane.nudge_selected(_current_pane_rows(), ui.open_operation, -1)

    @bindings.add("right", filter=pane_numeric_focused)
    def _pane_nudge_up(event) -> None:
        assert ui.open_operation is not None
        split_pane.nudge_selected(_current_pane_rows(), ui.open_operation, 1)

    @bindings.add("backspace", filter=pane_numeric_focused)
    def _pane_backspace(event) -> None:
        assert ui.open_operation is not None
        split_pane.backspace_selected(_current_pane_rows(), ui.open_operation)

    @bindings.add(Keys.Any, filter=pane_numeric_focused)
    def _pane_char(event) -> None:
        """FR-016: typing a digit (or `.`/`-`) immediately edits the
        selected numeric field's buffer -- matching the prototype's own
        per-digit-character bindings."""

        assert ui.open_operation is not None
        data = event.data
        if data and (data.isdigit() or data in ".-"):
            split_pane.edit_selected(_current_pane_rows(), ui.open_operation, data)

    # The metal Material selection window's own bindings (023-material-
    # selector-dialog). `enter` on the metal Material row (FR-001) opens it;
    # every binding below is gated on `material_picker_focused` instead of
    # `pane_focused` once it's open, mirroring the Exit-confirmation
    # dialog's own dedicated-focus-state pattern.
    @bindings.add("enter", filter=pane_material_picker_trigger)
    def _open_material_picker(event) -> None:
        op = ui.open_operation
        assert op is not None
        materials = _open_metal_materials()
        view.material_picker = material_picker.open_state(op.session_state.material, materials)
        event.app.layout.focus(material_picker_control)

    material_picker_focused = Condition(
        lambda: view.material_picker is not None
        and app.layout.has_focus(material_picker_control)
    )

    @bindings.add("up", filter=material_picker_focused)
    def _material_picker_up(event) -> None:
        state = view.material_picker
        assert state is not None
        material_picker.move_highlight(state, _material_picker_candidates(), -1)

    @bindings.add("down", filter=material_picker_focused)
    def _material_picker_down(event) -> None:
        state = view.material_picker
        assert state is not None
        material_picker.move_highlight(state, _material_picker_candidates(), 1)

    @bindings.add("escape", filter=material_picker_focused)
    def _material_picker_cancel(event) -> None:
        """FR-009: closes without changing the operation's material."""

        view.material_picker = None
        event.app.layout.focus(left_control)

    @bindings.add("enter", filter=material_picker_focused)
    def _material_picker_confirm(event) -> None:
        state = view.material_picker
        assert state is not None
        if state.highlighted_name is None:
            # FR-008: no candidate highlighted (e.g. an empty filtered
            # list) -- no-op, dialog stays open.
            return
        op = ui.open_operation
        assert op is not None
        op.session_state.material = state.highlighted_name
        view.material_picker = None
        event.app.layout.focus(left_control)

    def _material_picker_requery() -> None:
        """Re-derives `state.highlighted_name` against the freshly-filtered
        candidate list after a query edit (data-model.md "Edit query"
        transition, tasks.md T023): the first candidate, or `None` if the
        list is now empty -- the previously-highlighted material may no
        longer be a candidate."""

        state = view.material_picker
        assert state is not None
        remaining = _material_picker_candidates()
        state.highlighted_name = remaining[0].name if remaining else None

    #: `MaterialPickerState.active_column` -> the query field it names,
    #: used by the char/backspace bindings below to edit whichever column
    #: currently has focus (FR-006, tasks.md T030) instead of always
    #: `query_common` (User Story 1's interim behavior).
    _MATERIAL_PICKER_QUERY_ATTR = {
        "common": "query_common",
        "number": "query_number",
        "short": "query_short",
    }

    @bindings.add("left", filter=material_picker_focused)
    @bindings.add("s-tab", filter=material_picker_focused)
    def _material_picker_cycle_left(event) -> None:
        state = view.material_picker
        assert state is not None
        material_picker.cycle_column(state, -1)

    @bindings.add("right", filter=material_picker_focused)
    @bindings.add("tab", filter=material_picker_focused)
    def _material_picker_cycle_right(event) -> None:
        state = view.material_picker
        assert state is not None
        material_picker.cycle_column(state, 1)

    @bindings.add("backspace", filter=material_picker_focused)
    def _material_picker_backspace(event) -> None:
        state = view.material_picker
        assert state is not None
        attr = _MATERIAL_PICKER_QUERY_ATTR[state.active_column]
        setattr(state, attr, getattr(state, attr)[:-1])
        _material_picker_requery()

    @bindings.add(Keys.Any, filter=material_picker_focused)
    def _material_picker_char(event) -> None:
        """FR-003/FR-004: typing immediately edits the active column's
        query and re-filters."""

        data = event.data
        if not data or len(data) != 1 or not data.isprintable():
            return
        state = view.material_picker
        assert state is not None
        attr = _MATERIAL_PICKER_QUERY_ATTR[state.active_column]
        setattr(state, attr, getattr(state, attr) + data)
        _material_picker_requery()

    app: Application[None] = Application(
        layout=Layout(root, focused_element=bar_control),
        key_bindings=bindings,
        style=style,
        full_screen=True,
    )
    return app, ui, view


def run(materials_config_path: str | None = None) -> None:
    """Run the text GUI until the user exits from the menu bar.

    Resolves the active locale exactly once, at startup (mirrors the REPL's
    same FR-019c guarantee), and holds one session-lifetime state object per
    operation (drilling, and one per milling sub-operation) so revisiting a
    screen after a calculation offers the previous answers as defaults,
    exactly as the REPL's loop did (FR-002, SC-005 parity) -- Acceptance
    Scenario 3: the user can start another calculation without exiting and
    relaunching the text GUI. See `build_app` for the actual wiring.
    """

    locale = get_locale()
    display_locale = get_raw_locale()
    _resolve_materials_config(materials_config_path, locale)
    app, _ui, _view = build_app(materials_config_path, locale, display_locale)
    app.run()
