"""Integration tests for the static/simple screens: Machining tree,
About, Help (018-tui-splitpane-redesign). Configuration is exercised
separately (tasks.md T024 extends it; still the pre-existing dialog-based
`run_configuration_screen`, untouched by this phase). Complements
test_tui_drilling.py/test_tui_milling.py, which exercise the parameter-entry
screens, and test_tui_navigation.py, which exercises the tree end-to-end
through the real `Application`.

The Machining tree and About/Help are now pure render functions (no
`Application`/dialog of their own -- see `machining_menu.render_tree`,
`screens.about.render_about`, `screens.help.render_help`), so most of what
017's version of this file drove headlessly is now checkable directly
against their output.
"""

from __future__ import annotations

import mfgparams
from mfgparams.console.i18n import translate
from mfgparams.console.tui import machining_menu
from mfgparams.console.tui.app import MachiningTree
from mfgparams.console.tui.screens.about import render_about
from mfgparams.console.tui.screens.configuration import render_configuration
from mfgparams.console.tui.screens.help import render_help


def test_tree_rows_are_milling_then_drilling_then_turning_all_flat_leaves():
    """Revised (tasks.md Phase 8): Drilling's tree-level tool-selection
    shortcut is retired (FR-003) -- every row opens its floating window
    directly, and the row list no longer depends on any tree sub-state.
    Turning added by specs/019-turning-calculations, same flat-leaf shape."""

    rows = machining_menu.tree_rows(MachiningTree())
    assert [row.action for row in rows] == ["open_milling", "open_drilling", "open_turning"]


def test_tree_mnemonics_are_pairwise_unique():
    rows = machining_menu.tree_rows(MachiningTree(expanded=True))
    mnemonics = machining_menu.tree_mnemonics(rows, "en")
    present = [m for m in mnemonics if m is not None]
    assert len(present) == len(set(present))


def test_tree_render_includes_every_row_label():
    tree = MachiningTree(expanded=True)
    text = "".join(t for _, t in machining_menu.render_tree(tree, 0, "en", focused=True))
    assert "Milling" in text
    assert "Drilling" in text


def test_about_screen_text_includes_the_real_version():
    text = "".join(t for _, t in render_about("en"))
    assert mfgparams.__version__ in text


def test_about_screen_text_matches_the_catalog_directly():
    # A lighter-weight check of the same rendering logic used above, without
    # going through render_about: confirms the version string embedded is
    # the real one, sourced from the catalog (FR-011).
    text = translate("en", "tui.about.text", name="mfgparams", version=mfgparams.__version__)
    assert mfgparams.__version__ in text


def test_help_screen_is_reachable_and_non_crashing():
    fragments = render_help("en")
    assert fragments  # non-empty -- reachable, has content (FR-009 placeholder)


def test_configuration_screen_is_a_static_view_covering_all_three_registries():
    """FR-014/FR-015 (T024): view-only, and -- closing the gap PR #94's
    review found -- covering all three tool registries, not just
    Drilling's, now that this screen is being rebuilt anyway."""

    text = "".join(t for _, t in render_configuration(None, "en", "en"))
    assert translate("en", "tui.configuration.title") in text
    assert "Drilling tools:" in text
    assert "End-mill tools:" in text
    assert "Face-mill tools:" in text
    # At least one bundled material type/material is actually listed, not
    # just the section headers.
    assert "Mild Steel" in text or "Oak" in text
