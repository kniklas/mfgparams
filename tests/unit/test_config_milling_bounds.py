"""Tests for the configurable milling validation bounds (T011d, FR-018).

The milling bounds live in the *same* configuration file as the existing
drilling bounds (research.md #8), so these tests check both that raising a
milling bound takes effect and that doing so leaves the drilling bounds
alone.
"""

import pytest

from mfgparams import calculate, calculate_end_milling
from mfgparams.config import (
    DEFAULT_MAX_DEPTH_MM,
    DEFAULT_MAX_DEPTH_OF_CUT_MM,
    DEFAULT_MAX_DIAMETER_MM,
    DEFAULT_MAX_LENGTH_OF_CUT_MM,
    DEFAULT_MAX_MILL_DIAMETER_MM,
    load_configuration,
)


def _write_config(tmp_path, body: str) -> str:
    path = tmp_path / "bounds.toml"
    path.write_text(body)
    return str(path)


def test_documented_defaults_apply_with_no_configuration_file():
    config = load_configuration(None)

    assert config.max_mill_diameter_mm == DEFAULT_MAX_MILL_DIAMETER_MM == 200.0
    assert config.max_depth_of_cut_mm == DEFAULT_MAX_DEPTH_OF_CUT_MM == 50.0
    assert config.max_length_of_cut_mm == DEFAULT_MAX_LENGTH_OF_CUT_MM == 1000.0


def _end_milling(config_path=None, **overrides):
    kwargs = {
        "diameter": 10.0,
        "axial_depth_of_cut": 2.0,
        "radial_depth_of_cut": 5.0,
        "feed_per_tooth": 0.05,
        "number_of_teeth": 4,
        "length_of_cut": 100.0,
        "material": "Mild Steel",
        "tool": "Carbide",
        "config_path": config_path,
    }
    kwargs.update(overrides)
    return calculate_end_milling(**kwargs)


@pytest.mark.parametrize(
    "field,over_default,key,raised,over_raised,code",
    [
        (
            "diameter",
            250.0,
            "max_mill_diameter_mm",
            300.0,
            350.0,
            "INVALID_DIAMETER",
        ),
        (
            "axial_depth_of_cut",
            60.0,
            "max_depth_of_cut_mm",
            80.0,
            90.0,
            "INVALID_DEPTH_OF_CUT",
        ),
        (
            "length_of_cut",
            1500.0,
            "max_length_of_cut_mm",
            2000.0,
            2500.0,
            "INVALID_LENGTH_OF_CUT",
        ),
    ],
)
def test_each_milling_bound_is_configurable(
    tmp_path, field, over_default, key, raised, over_raised, code
):
    rejected = _end_milling(**{field: over_default})
    assert rejected.error is not None
    assert rejected.error.code == code

    config_path = _write_config(tmp_path, f"{key} = {raised}\n")

    accepted = _end_milling(config_path=config_path, **{field: over_default})
    assert accepted.error is None
    assert accepted.material_removal_rate is not None

    still_rejected = _end_milling(config_path=config_path, **{field: over_raised})
    assert still_rejected.error is not None
    assert still_rejected.error.code == code


def test_raising_milling_bounds_leaves_drilling_bounds_untouched(tmp_path):
    config_path = _write_config(
        tmp_path,
        "max_mill_diameter_mm = 300.0\nmax_depth_of_cut_mm = 80.0\nmax_length_of_cut_mm = 2000.0\n",
    )

    config = load_configuration(config_path)

    assert config.max_diameter_mm == DEFAULT_MAX_DIAMETER_MM
    assert config.max_depth_mm == DEFAULT_MAX_DEPTH_MM

    # And a drilling calculation beyond drilling's own (unraised) bound is
    # still rejected, i.e. the milling override did not leak across.
    result = calculate(
        diameter=DEFAULT_MAX_DIAMETER_MM + 1,
        depth=10.0,
        material="Mild Steel",
        tool="Carbide",
        config_path=config_path,
    )
    assert result.error is not None
    assert result.error.code == "INVALID_DIAMETER"


def test_drilling_and_milling_bounds_coexist_in_one_file(tmp_path):
    config_path = _write_config(tmp_path, "max_diameter_mm = 120.0\nmax_mill_diameter_mm = 300.0\n")

    config = load_configuration(config_path)

    assert config.max_diameter_mm == 120.0
    assert config.max_mill_diameter_mm == 300.0
    # Untouched keys keep their documented defaults.
    assert config.max_depth_of_cut_mm == DEFAULT_MAX_DEPTH_OF_CUT_MM
