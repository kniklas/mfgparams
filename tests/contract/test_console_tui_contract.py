"""Contract test: menu bar + Machining tree structure and mnemonic
uniqueness (contracts/console-tui-splitpane-contract.md §2/§4,
data-model.md's MenuEntry validation rule).

018-tui-splitpane-redesign, tasks.md T008: rewritten in place against the
new contract (research.md's consolidated decisions table) -- 017's version
tested a 4-item top-level menu and a separate full-screen Machining
submenu, both replaced by the persistent bar (5 items, Exit added) and the
collapsible tree respectively.

Rewritten again (revision, tasks.md T042/Phase 8): Drilling's tree-level
tool-selection shortcut is retired (FR-003) -- the tree is now exactly two
flat leaves, Milling and Drilling, with no further sub-expansion under
either.
"""

from __future__ import annotations

from mfgparams.console.i18n import translate
from mfgparams.console.tui import machining_menu
from mfgparams.console.tui.app import MachiningTree
from mfgparams.console.tui.menu import MenuEntry, _assign_mnemonics, default_entries


def test_menu_bar_entries_match_the_contract():
    """§2's invariant: Exit, Machining, Configuration, About, Help, in
    that exact order -- a closed set."""

    entries = [entry.value for entry in default_entries("en")]
    assert entries == ["exit", "machining", "configuration", "about", "help"]

    labels = [entry.label for entry in default_entries("en")]
    assert labels == ["Exit", "Machining", "Configuration", "About", "Help"]


def test_menu_bar_mnemonics_are_pairwise_unique_and_complete():
    entries = default_entries("en")
    mnemonics = _assign_mnemonics(entries)
    non_none = [m for m in mnemonics if m is not None]
    assert len(non_none) == len(set(non_none)), f"mnemonic collision in {mnemonics}"
    assert None not in mnemonics, "every bar entry should get a mnemonic (E/M/C/A/H)"


def test_machining_tree_structure_matches_the_contract():
    """§2's invariant: Milling, Drilling, and Turning are Machining's only
    children, all flat leaves -- there is no further sub-expansion under
    any of them (FR-003 retired via `/speckit-clarify`, reopened after
    implementation; Turning added by specs/019-turning-calculations
    following the same flat-leaf pattern), so the tree's content no longer
    depends on any state beyond whether it's shown at all."""

    rows = machining_menu.tree_rows(MachiningTree())
    labels = [translate("en", row.label_key) for row in rows]
    assert labels == ["Milling", "Drilling", "Turning"]


def test_machining_tree_mnemonics_are_pairwise_unique():
    tree = MachiningTree(expanded=True)
    rows = machining_menu.tree_rows(tree)
    mnemonics = machining_menu.tree_mnemonics(rows, "en")
    non_none = [m for m in mnemonics if m is not None]
    assert len(non_none) == len(set(non_none)), f"mnemonic collision in {mnemonics}"
    assert None not in mnemonics, "every tree row should get a mnemonic (M/D)"


def test_bar_and_tree_mnemonics_are_separate_namespaces():
    """Contract §4: the bar and tree each get their own pairwise-unique
    set -- e.g. both "Machining" (bar) and "Milling" (tree) may use "m",
    since a tree row's mnemonic is only ever active while the tree itself
    has focus (app.py's `tree_focused` condition), not simultaneously with
    the bar's."""

    bar_mnemonics = _assign_mnemonics(default_entries("en"))
    tree_mnemonics = machining_menu.tree_mnemonics(machining_menu.tree_rows(MachiningTree()), "en")
    assert "m" in bar_mnemonics  # Machining
    assert "m" in tree_mnemonics  # Milling -- same character, different namespace, no conflict


def test_mnemonic_assignment_falls_back_when_first_letters_collide():
    """Two labels starting with the same letter must not silently collide --
    the assigner should find the next free character in the second one."""

    entries = [MenuEntry("a", "Milling"), MenuEntry("b", "Machining")]
    mnemonics = _assign_mnemonics(entries)
    assert mnemonics[0] == "m"
    assert mnemonics[1] is not None
    assert mnemonics[1] != "m"


def test_a_fully_exhausted_label_gets_no_mnemonic_rather_than_colliding():
    entries = [MenuEntry("a", "Aa"), MenuEntry("b", "Aa")]
    mnemonics = _assign_mnemonics(entries)
    assert mnemonics[0] == "a"
    assert mnemonics[1] is None
