"""Unit tests for configuration loading and default-bound fallback (T017)."""

from mfgparams.config import (
    DEFAULT_MAX_DEPTH_MM,
    DEFAULT_MAX_DIAMETER_MM,
    load_configuration,
)


def test_no_config_path_returns_defaults():
    config = load_configuration(None)
    assert config.max_diameter_mm == DEFAULT_MAX_DIAMETER_MM
    assert config.max_depth_mm == DEFAULT_MAX_DEPTH_MM


def test_nonexistent_file_returns_defaults(tmp_path):
    missing = tmp_path / "does-not-exist.toml"
    config = load_configuration(str(missing))
    assert config.max_diameter_mm == DEFAULT_MAX_DIAMETER_MM
    assert config.max_depth_mm == DEFAULT_MAX_DEPTH_MM


def test_file_overrides_both_bounds(tmp_path):
    config_file = tmp_path / "mfgparams.toml"
    config_file.write_text("max_diameter_mm = 150\nmax_depth_mm = 600\n")

    config = load_configuration(str(config_file))
    assert config.max_diameter_mm == 150.0
    assert config.max_depth_mm == 600.0


def test_file_with_partial_keys_falls_back_for_missing_key(tmp_path):
    config_file = tmp_path / "mfgparams.toml"
    config_file.write_text("max_diameter_mm = 150\n")

    config = load_configuration(str(config_file))
    assert config.max_diameter_mm == 150.0
    assert config.max_depth_mm == DEFAULT_MAX_DEPTH_MM


def test_empty_file_returns_defaults(tmp_path):
    config_file = tmp_path / "mfgparams.toml"
    config_file.write_text("")

    config = load_configuration(str(config_file))
    assert config.max_diameter_mm == DEFAULT_MAX_DIAMETER_MM
    assert config.max_depth_mm == DEFAULT_MAX_DEPTH_MM
