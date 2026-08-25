"""Registry isolation between drilling and milling tool tables (T011c).

Users supply a *single* configuration file for the whole application
(contracts/milling-tools-config-schema.md "Section isolation"), so the three
tool registries must be keyed on distinct TOML tables: drilling's ``tools``,
end milling's ``end_mill_tools`` and face milling's ``face_mill_tools``.

This matters beyond tidiness: drilling tool entries require a ``feed_factor``
that milling entries deliberately do not have (research.md #3, #4). If the
registries shared a table key, adding a milling tool would either inject an
invalid entry into the drilling registry or raise ``RegistryConfigError``
from a drilling call — breaking already-shipped drilling behaviour (FR-002,
SC-005).
"""

import pytest

from mfgparams import calculate, list_end_mill_tools, list_face_mill_tools, list_tools
from mfgparams.registry_config import clear_cache


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    clear_cache()
    yield
    clear_cache()


def _write(tmp_path, body: str) -> str:
    path = tmp_path / "config.toml"
    path.write_text(body)
    return str(path)


BUNDLED_DRILLING_TOOLS = list_tools()
BUNDLED_END_MILL_TOOLS = list_end_mill_tools()
BUNDLED_FACE_MILL_TOOLS = list_face_mill_tools()


def test_milling_only_config_leaves_the_drilling_registry_untouched(tmp_path):
    path = _write(
        tmp_path,
        """
        [[end_mill_tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0

        [[face_mill_tools]]
        name = "PCD"
        cutting_speed_factor = 8.0
        """,
    )

    assert list_tools(config_path=path) == BUNDLED_DRILLING_TOOLS
    assert "Ceramic" in list_end_mill_tools(path)
    assert "PCD" in list_face_mill_tools(path)
    # ... and the milling tables do not leak into each other either.
    assert "PCD" not in list_end_mill_tools(path)
    assert "Ceramic" not in list_face_mill_tools(path)


def test_drilling_still_calculates_with_a_milling_only_config(tmp_path):
    """A milling tool entry has no ``feed_factor``; drilling must not see it."""

    path = _write(
        tmp_path,
        """
        [[end_mill_tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0
        """,
    )

    result = calculate(
        diameter=10.0,
        depth=25.0,
        material="Mild Steel",
        tool="Carbide",
        materials_config_path=path,
    )

    assert result.error is None
    assert result.spindle_speed_rpm is not None
    # Drilling results never carry a material removal rate (research.md #7).
    assert result.material_removal_rate is None


def test_legacy_drilling_only_config_adds_nothing_to_the_milling_registries(tmp_path):
    path = _write(
        tmp_path,
        """
        [[materials]]
        name = "Inconel"
        reference_cutting_speed = 15.0
        reference_feed_per_rev = 0.1
        specific_cutting_force = 2700.0

        [[tools]]
        name = "Ceramic Drill"
        cutting_speed_factor = 4.0
        feed_factor = 0.9
        """,
    )

    assert "Ceramic Drill" in list_tools(config_path=path)
    assert list_end_mill_tools(path) == BUNDLED_END_MILL_TOOLS
    assert list_face_mill_tools(path) == BUNDLED_FACE_MILL_TOOLS


def test_a_single_file_may_extend_all_three_registries_at_once(tmp_path):
    path = _write(
        tmp_path,
        """
        [[tools]]
        name = "Ceramic Drill"
        cutting_speed_factor = 4.0
        feed_factor = 0.9

        [[end_mill_tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0

        [[face_mill_tools]]
        name = "PCD"
        cutting_speed_factor = 8.0
        """,
    )

    assert "Ceramic Drill" in list_tools(config_path=path)
    assert "Ceramic" in list_end_mill_tools(path)
    assert "PCD" in list_face_mill_tools(path)
    # Same-named entries in different tables stay independent.
    assert "Ceramic Drill" not in list_end_mill_tools(path)


def test_same_tool_name_in_different_tables_keeps_its_own_values(tmp_path):
    path = _write(
        tmp_path,
        """
        [[end_mill_tools]]
        name = "Carbide"
        cutting_speed_factor = 4.0

        [[face_mill_tools]]
        name = "Carbide"
        cutting_speed_factor = 6.0
        """,
    )

    from mfgparams.operations.milling.end_milling.tools import get_end_mill_tool
    from mfgparams.operations.milling.face_milling.tools import get_face_mill_tool

    assert get_end_mill_tool("Carbide", path).cutting_speed_factor == 4.0
    assert get_face_mill_tool("Carbide", path).cutting_speed_factor == 6.0
    # Drilling's own "Carbide" is unaffected by either override.
    from mfgparams.operations.drilling.tools import get_tool

    assert get_tool("Carbide", path).cutting_speed_factor == 2.5


def test_the_three_registries_use_distinct_table_keys():
    """Guard the invariant directly, not just its observable consequences."""

    from mfgparams.operations.drilling import tools as drilling_tools
    from mfgparams.operations.milling.end_milling import tools as end_tools
    from mfgparams.operations.milling.face_milling import tools as face_tools

    keys = {
        drilling_tools._TABLE_KEY,
        end_tools._TABLE_KEY,
        face_tools._TABLE_KEY,
    }
    assert len(keys) == 3
