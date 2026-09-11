"""The collapsible Machining tree (018-tui-splitpane-redesign FR-002),
replacing the old full-screen Machining submenu.

Rendering + row-model only, mirroring `menu.py`: `app.py` owns the actual
`Layout`/key-binding wiring and decides what each row's selection *does*
(opens an operation's floating window) -- this module only knows how to
lay the tree out and which rows currently exist.

Revised via `/speckit-clarify` (reopened after implementation, per user
feedback on PR #96 preferring the pre-plan prototype's UI): Drilling's
tree-level tool-selection sub-expansion is retired (FR-003). Both Milling
and Drilling are now flat leaves that open their floating window directly
-- the tree's row list no longer depends on anything beyond the fact that
it's being shown at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import translate
from mfgparams.console.tui.app import MachiningTree
from mfgparams.console.tui.menu import MenuEntry, _assign_mnemonics

#: A row's `action` names what selecting it does (app.py dispatches on
#: this): every action opens an operation's floating window directly
#: (FR-004) -- there is no longer a toggle/shortcut action, since
#: Drilling's tree-level tool-selection sub-expansion is retired (FR-003).
#: `open_turning` added by specs/019-turning-calculations, following the
#: identical flat-leaf pattern.
RowAction = Literal["open_milling", "open_drilling", "open_turning"]


@dataclass(frozen=True)
class TreeRow:
    label_key: str
    action: RowAction
    indent: int


def tree_rows(tree: MachiningTree) -> list[TreeRow]:
    """The tree's rows, in display order -- Milling, Drilling, and Turning,
    all flat leaves (FR-002/FR-003; specs/019-turning-calculations adds the
    third). ``tree`` is accepted for interface symmetry with the
    tree-state-dependent shape this had before the revision, and in case a
    future operation's own presence ever needs to depend on `SessionUI`
    state; today it's unused."""

    del tree
    return [
        TreeRow("tui.machining_menu.milling", "open_milling", indent=0),
        TreeRow("tui.machining_menu.drilling", "open_drilling", indent=0),
        TreeRow("tui.machining_menu.turning", "open_turning", indent=0),
    ]


def tree_mnemonics(rows: list[TreeRow], locale: str) -> list[str | None]:
    """One accelerator character per row, pairwise-unique *within the
    tree* (contract §4: "every menu bar entry and tree leaf" gets one) --
    a separate namespace from the bar's own mnemonics, reusing
    `menu._assign_mnemonics` unchanged (research.md) by wrapping each row's
    translated label in a throwaway `MenuEntry`."""

    entries = [MenuEntry(row.action, translate(locale, row.label_key)) for row in rows]
    return _assign_mnemonics(entries)


def render_tree(
    tree: MachiningTree,
    selected_index: int,
    locale: str,
    *,
    focused: bool,
) -> StyleAndTextTuples:
    """The tree's rows, most-recently-selected row reverse-video
    highlighted only while ``focused`` (same convention as
    `menu.render_menu_bar`), each row's mnemonic underlined the same way
    the bar's own entries are."""

    rows = tree_rows(tree)
    mnemonics = tree_mnemonics(rows, locale)
    fragments: StyleAndTextTuples = [
        ("class:pane-title", f"{translate(locale, 'tui.machining_menu.title')}\n")
    ]
    for index, (row, mnemonic) in enumerate(zip(rows, mnemonics)):
        style = "class:selected" if focused and index == selected_index else ""
        indent = "  " * (row.indent + 1)
        label = translate(locale, row.label_key)
        fragments.append((style, f"{indent}"))
        if mnemonic is None:
            fragments.append((style, label))
        else:
            pos = label.lower().index(mnemonic)
            before, marked, after = label[:pos], label[pos : pos + 1], label[pos + 1 :]
            fragments.append((style, before))
            fragments.append((f"{style} class:mnemonic", marked))
            fragments.append((style, after))
        fragments.append((style, "\n"))
    return fragments
