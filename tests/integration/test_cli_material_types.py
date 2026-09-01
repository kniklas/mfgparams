"""Integration tests: two-step material selection in the CLI.

Covers the user-facing half of specs/008-material-categorization — the user
picks a material *type* first, then a material within it (008 US1, US2) —
plus category switching, data-driven category labels, and stale-selection
handling (008 FR-001, FR-002, FR-004, FR-010, FR-011).
"""

from __future__ import annotations

import builtins
import logging

import pytest

from mfgparams import i18n
from mfgparams.console.cli import run


def _feed(monkeypatch, answers):
    """Feed ``answers`` to ``input()``, echoing each prompt so it is captured."""

    iterator = iter(answers)

    def _input(prompt=""):
        print(prompt, end="")
        return next(iterator)

    monkeypatch.setattr(builtins, "input", _input)


def _write_config(tmp_path, body: str) -> str:
    path = tmp_path / "user-materials.toml"
    path.write_text(body, encoding="utf-8")
    return str(path)


class TestTypeThenMaterialFlow:
    """US1 + US2: the type prompt precedes and scopes the material prompt."""

    def test_type_prompt_precedes_material_prompt(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal",
                "Mild Steel",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        assert "Material type (Metal, Wood)" in out
        assert out.index("Material type") < out.index("Material (")
        assert "Spindle speed:" in out

    def test_material_prompt_lists_only_the_chosen_category(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            ["drilling", "metric", "standard", "Wood", "Oak", "Carbide", "10", "25", "", "n"],
        )

        run()

        out = capsys.readouterr().out
        assert "Material (Oak, Maple, Pine, Spruce, Fir, Plywood, MDF)" in out
        assert "Mild Steel" not in out

    def test_selecting_metal_excludes_wood_materials(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            ["drilling", "metric", "standard", "Metal", "Titanium", "Carbide", "10", "25", "", "n"],
        )

        run()

        out = capsys.readouterr().out
        assert "Material (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium)" in out
        assert "Oak" not in out

    def test_material_from_another_category_is_rejected_and_reprompted(self, monkeypatch, capsys):
        """Choosing "Wood" must not accept a metal (008 FR-002)."""

        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Wood",
                "Mild Steel",
                "Oak",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        assert "Please choose one of" in out
        assert "Spindle speed:" in out

    def test_invalid_type_is_reprompted(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Ceramic",
                "Metal",
                "Mild Steel",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        assert "Please choose one of: Metal, Wood" in out
        assert "Spindle speed:" in out


class TestCategorySwitchingOnLoopRerun:
    """Re-running the REPL loop remembers, or correctly clears, the selection."""

    def test_unchanged_type_reuses_previous_material_default(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            [
                "drilling",  # machining operation (009 FR-001)
                "metric",
                "standard",
                "Metal",
                "Mild Steel",
                "HSS",
                "10",
                "25",
                "",
                "y",
                # Second pass: blank type reuses "Metal", blank material reuses
                # "Mild Steel"; only the tool changes.
                "drilling",  # machining operation (009 FR-001)
                "metric",
                "standard",
                "",
                "",
                "Carbide",
                "",
                "",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        assert out.count("Spindle speed:") == 2

    def test_switching_type_does_not_offer_a_cross_category_default(self, monkeypatch, capsys):
        """After switching to Wood, the metal default must not be reusable (008 FR-011).

        The second pass answers the material prompt with a blank line. If the
        remembered "Mild Steel" were still offered as this category's default,
        the blank would silently select it; instead the prompt must reject the
        blank and reprompt until a wood is named.
        """

        _feed(
            monkeypatch,
            [
                "drilling",  # machining operation (009 FR-001)
                "metric",
                "standard",
                "Metal",
                "Mild Steel",
                "Carbide",
                "10",
                "25",
                "",
                "y",
                "drilling",  # machining operation (009 FR-001)
                "metric",
                "standard",
                "Wood",
                "",  # blank must NOT resolve to the remembered "Mild Steel"
                "Oak",  # an explicit in-category choice is required
                "",
                "",
                "",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        second_pass = out[out.index("Run another calculation?") :]
        assert "Please choose one of" in second_pass
        assert "(Mild Steel)" not in second_pass
        assert out.count("Spindle speed:") == 2


class TestDataDrivenCategories:
    """A category added by configuration alone is fully usable (008 FR-004)."""

    def test_new_category_appears_and_is_selectable(self, monkeypatch, capsys, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Portland Cement"
material_type = "cement"
reference_cutting_speed = 30.0
reference_feed_per_rev = 0.15
specific_cutting_force = 1400.0
""",
        )
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Cement",
                "Portland Cement",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        # "cement" has no catalog entry; the label falls back to title case.
        assert "Material type (Metal, Wood, Cement)" in out
        assert "Material (Portland Cement)" in out
        assert "Spindle speed:" in out

    def test_multi_word_category_id_is_title_cased(self, monkeypatch, capsys, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "CFRP"
material_type = "composite-fibre"
reference_cutting_speed = 60.0
reference_feed_per_rev = 0.10
specific_cutting_force = 900.0
""",
        )
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Composite Fibre",
                "CFRP",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        assert "Composite Fibre" in out
        assert "Spindle speed:" in out

    def test_uncategorized_materials_are_still_selectable(self, monkeypatch, capsys, tmp_path):
        """A pre-008 config file's new material remains reachable (008 FR-011)."""

        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Uncategorized",
                "Bronze",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        assert "Material type (Metal, Wood, Uncategorized)" in out
        assert "Spindle speed:" in out


class TestCategoryLabelLocalization:
    """Category labels go through the message catalog (Constitution VIII)."""

    @pytest.fixture(autouse=True)
    def _reset_catalog(self):
        yield
        i18n.clear_catalog_cache()

    def test_unsupported_locale_falls_back_to_english_labels(self, monkeypatch, capsys):
        monkeypatch.setenv("MFGPARAMS_LOCALE", "xx-no-catalog")
        i18n.clear_catalog_cache()
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal",
                "Mild Steel",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        assert "Material type (Metal, Wood)" in out
        assert "material_type.metal" not in out


class TestDuplicateLabelDisambiguation:
    """Distinct type ids that render the same label stay individually reachable.

    Type ids are free-form and case-sensitive, but labels are not: a
    user-defined ``material_type = "Metal"`` title-cases to ``"Metal"``,
    which is exactly what the bundled ``metal`` resolves to via the message
    catalog. Without disambiguation the reverse lookup would collapse them
    and make one category unreachable (008 FR-006a).
    """

    CONFIG = """
[[materials]]
name = "Bronze"
material_type = "Metal"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
"""

    def test_colliding_labels_are_suffixed_with_their_canonical_id(
        self, tmp_path, monkeypatch, capsys
    ):
        config_path = _write_config(tmp_path, self.CONFIG)
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal (metal)",
                "Aluminum",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        assert "Material type (Metal (metal), Wood, Metal (Metal))" in out

    def test_bundled_category_stays_reachable_when_a_label_collides(
        self, tmp_path, monkeypatch, capsys
    ):
        config_path = _write_config(tmp_path, self.CONFIG)
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal (metal)",
                "Aluminum",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        # The bundled `metal` members are offered, not the single user "Metal" one.
        assert "Material (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium)" in out
        assert "Bronze" not in out

    def test_user_category_stays_reachable_when_a_label_collides(
        self, tmp_path, monkeypatch, capsys
    ):
        config_path = _write_config(tmp_path, self.CONFIG)
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal (Metal)",
                "Bronze",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        assert "Material (Bronze)" in out
        assert "Spindle speed:" in out

    def test_labels_are_not_suffixed_when_there_is_no_collision(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal",
                "Mild Steel",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        assert "Material type (Metal, Wood)" in out
        assert "(metal)" not in out

    def test_suffixed_labels_that_collide_again_stay_distinct(self, tmp_path, monkeypatch, capsys):
        """A generated suffix must not collide with a literal id of the same shape.

        `metal`, `Metal` and `Metal (Metal)` all render as some form of
        "Metal": the first two collide on "Metal", and disambiguating
        `Metal` produces "Metal (Metal)" — which is exactly what the third
        id renders as on its own. Every id must still be reachable.
        """
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "Metal"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0

[[materials]]
name = "Pewter"
material_type = "Metal (Metal)"
reference_cutting_speed = 60.0
reference_feed_per_rev = 0.22
specific_cutting_force = 400.0
""",
        )
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal (Metal)",
                "Bronze",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        prompt = out[out.index("Material type (") : out.index("Material (")]
        labels = prompt[prompt.index("(") + 1 : prompt.rindex(")")].split(", ")
        assert len(labels) == len(set(labels)), f"duplicate labels offered: {labels}"
        # The chosen label resolves to the `Metal` id (Bronze), not `Metal (Metal)` (Pewter).
        assert "Material (Bronze)" in out

    def test_leading_punctuation_type_id_stays_selectable(self, tmp_path, monkeypatch, capsys):
        """A type id whose label normalises to leading whitespace must be typeable.

        `-metal` title-cases to " Metal"; because `_prompt_choice` strips the
        user's input before matching, an option with leading whitespace could
        never be entered. It also collides with the bundled `metal` label once
        stripped, so it must additionally be disambiguated.
        """
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "-metal"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "Metal (-metal)",
                "Bronze",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        prompt = out[out.index("Material type (") : out.index("Material (")]
        labels = prompt[prompt.index("(") + 1 : prompt.rindex(")")].split(", ")
        assert all(label == label.strip() for label in labels), labels
        assert all(label.strip() for label in labels), labels
        assert "Material (Bronze)" in out

    def test_type_id_with_no_printable_label_falls_back_to_raw_id(
        self, tmp_path, monkeypatch, capsys
    ):
        """An id that normalises to nothing printable falls back to the raw id."""
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "-"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        _feed(
            monkeypatch,
            ["drilling", "metric", "standard", "-", "Bronze", "Carbide", "10", "25", "", "n"],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        assert "Material (Bronze)" in out


class TestMaterialsConfigLoadCaching:
    """The startup notice must not defeat the merge cache (008 Principle IV)."""

    def test_startup_notice_reuses_the_registry_merge_cache(self, tmp_path, monkeypatch, capsys):
        """A CLI startup must parse each materials TOML file only once.

        `registry` loads materials with its sticky-field tuple, so the startup
        notice lookup must use the same tuple; a different one is a different
        `functools.cache` key and silently rereads and reparses both the
        bundled and the user file a second time.
        """
        from mfgparams import registry_config

        registry_config.clear_cache()
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "metal"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        calls: list[tuple[object, ...]] = []
        original = registry_config._load_and_merge_uncached
        monkeypatch.setattr(
            registry_config,
            "_load_and_merge_uncached",
            lambda *args: (calls.append(args), original(*args))[1],
        )
        _feed(
            monkeypatch,
            ["drilling", "metric", "standard", "Metal", "Bronze", "Carbide", "10", "25", "", "n"],
        )

        run(materials_config_path=config_path)
        capsys.readouterr()

        materials_loads = [args for args in calls if args[3] == "materials"]
        assert (
            len(materials_loads) == 1
        ), f"materials config parsed {len(materials_loads)}x, expected 1: {materials_loads}"


class TestBraceContainingTypeId:
    """`translate()` formats the fallback key, so braces need care (FR-004)."""

    def test_brace_id_uses_title_case_fallback_not_the_catalog_key(
        self, tmp_path, monkeypatch, capsys
    ):
        """A brace-containing id must not leak the raw message-catalog key.

        `translate()` runs `str.format()` even when the key is its own
        fallback, so `material_type.{{alloy}}` comes back as
        `material_type.{alloy}`. Comparing the result against the unformatted
        key reads that as a catalog hit and prints the key to the user.
        """
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "{{alloy}}"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        _feed(
            monkeypatch,
            [
                "drilling",
                "metric",
                "standard",
                "{{Alloy}}",
                "Bronze",
                "Carbide",
                "10",
                "25",
                "",
                "n",
            ],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        prompt = out[out.index("Material type (") : out.index("Material (")]
        assert "material_type." not in prompt, prompt
        assert "{{Alloy}}" in prompt, prompt
        assert "Material (Bronze)" in out

    def test_single_brace_id_uses_title_case_fallback(self, tmp_path, monkeypatch, capsys):
        """An id with unbalanced braces makes `str.format()` raise, not substitute.

        `material_type.al{o}y` raises `KeyError('o')`, which `translate()`
        swallows and returns unformatted, so the sentinel used to detect a
        catalog miss has to tolerate the same failure.
        """
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "al{o}y"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        _feed(
            monkeypatch,
            ["drilling", "metric", "standard", "Al{O}Y", "Bronze", "Carbide", "10", "25", "", "n"],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        prompt = out[out.index("Material type (") : out.index("Material (")]
        assert "material_type." not in prompt, prompt
        assert "Material (Bronze)" in out

    def test_brace_id_does_not_emit_an_i18n_warning(self, tmp_path, monkeypatch, capsys, caplog):
        """Valid free-form ids must not produce i18n diagnostics.

        `main()` configures WARNING logging, so routing a dynamic id through
        `translate()`'s formatting path made every material-type prompt print
        a spurious warning for otherwise valid configuration.
        """
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "al{o}y"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        _feed(
            monkeypatch,
            ["drilling", "metric", "standard", "Al{O}Y", "Bronze", "Carbide", "10", "25", "", "n"],
        )

        with caplog.at_level(logging.WARNING, logger="mfgparams.i18n"):
            run(materials_config_path=config_path)

        capsys.readouterr()
        assert [record.getMessage() for record in caplog.records] == []
