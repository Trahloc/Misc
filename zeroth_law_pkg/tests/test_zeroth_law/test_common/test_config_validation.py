# File: tests/test_config_validation.py
"""Tests for configuration validation using Pydantic."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add parent directory to sys.path to allow import of config_loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# from zeroth_law.config_loader import DEFAULT_CONFIG  # noqa: E402
# from zeroth_law.config_validation import ConfigModel, ViolationRule, validate_config  # noqa: E402
from zeroth_law.common.config_loader import DEFAULT_CONFIG  # noqa: E402
from zeroth_law.common.config_validation import ConfigModel, ViolationRule, validate_config  # noqa: E402


def test_config_model_basic_validation():
    """Test basic validation of the config model."""
    # Valid config should pass validation
    valid_config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
        "ignore_rules": ["HEADER_LINE_1_MISMATCH", "FOOTER_MISSING"],
        "exclude_dirs": ["venv", "__pycache__"],
        "exclude_files": ["setup.py"],
    }

    config_model = ConfigModel.model_validate(valid_config)
    assert config_model.max_complexity == 10
    assert config_model.max_parameters == 5
    assert config_model.max_statements == 50
    assert config_model.max_lines == 100
    assert "HEADER_LINE_1_MISMATCH" in config_model.ignore_rules
    assert "venv" in config_model.exclude_dirs
    assert "setup.py" in config_model.exclude_files


@pytest.mark.parametrize(
    "invalid_config,expected_error_substr",
    [
        (
            {"max_complexity": -1},  # Negative value not allowed
            "Input should be greater than or equal to 0",
        ),
        (
            {"max_complexity": "not_a_number"},  # Wrong type
            "Input should be a valid integer",
        ),
        (
            {"ignore_rules": ["INVALID_RULE"]},  # Invalid rule name
            "Input should be 'HEADER_LINE_1_MISMATCH', 'HEADER_MISSING_FILE_LINE'",
        ),
        (
            {"exclude_dirs": 123},  # Wrong type for list
            "Input should be a valid list",
        ),
    ],
    ids=[
        "negative_value",
        "wrong_type_for_number",
        "invalid_rule_name",
        "wrong_type_for_list",
    ],
)
def test_config_model_invalid_values(invalid_config, expected_error_substr):
    """Test validation fails with proper error for invalid configs."""
    with pytest.raises(ValidationError) as excinfo:
        ConfigModel.model_validate(invalid_config)

    assert expected_error_substr in str(excinfo.value)


def test_validate_config_wrapper_function():
    """Test the validate_config wrapper function."""
    # Valid config should pass validation and return a ConfigModel
    valid_config = {
        "max_complexity": 10,
        "max_parameters": 5,
        "max_statements": 50,
        "max_lines": 100,
    }

    validated = validate_config(valid_config)
    assert isinstance(validated, ConfigModel)
    assert validated.max_complexity == 10
    assert validated.max_parameters == 5

    # Invalid config should raise ValidationError
    invalid_config = {"max_complexity": -10}
    with pytest.raises(ValidationError):
        validate_config(invalid_config)

    # Empty config should use default values
    empty_config = {}
    default_validated = validate_config(empty_config)
    assert default_validated.max_complexity > 0
    assert default_validated.max_parameters > 0
    assert default_validated.max_statements > 0
    assert default_validated.max_lines > 0


def test_config_model_merges_with_defaults():
    """Test that partial configs are merged with defaults."""
    # Partial config should be merged with defaults
    partial_config = {
        "max_complexity": 15,  # Custom value
    }

    config_model = ConfigModel.model_validate(partial_config)
    assert config_model.max_complexity == 15  # Should use custom value
    assert config_model.max_parameters > 0  # Should use default value
    assert config_model.max_statements > 0  # Should use default value
    assert config_model.max_lines > 0  # Should use default value


@pytest.mark.parametrize(
    "input_config,expected_values",
    [
        (
            # Minimal config with only one field
            {"max_complexity": 15},
            {"max_complexity": 15, "max_parameters": DEFAULT_CONFIG["max_parameters"]},
        ),
        (
            # Config with custom excludes
            {"exclude_dirs": ["my_dir"], "exclude_files": ["temp.py"]},
            {"exclude_dirs": ["my_dir"], "exclude_files": ["temp.py"]},
        ),
        (
            # Config with custom ignore rules
            {"ignore_rules": ["HEADER_LINE_1_MISMATCH", "FOOTER_MISSING"]},
            {
                "ignore_rules": [
                    ViolationRule.HEADER_LINE_1_MISMATCH,
                    ViolationRule.FOOTER_MISSING,
                ]
            },
        ),
        (
            # Full custom config
            {
                "max_complexity": 8,
                "max_parameters": 4,
                "max_statements": 40,
                "max_lines": 80,
                "exclude_dirs": ["tests"],
                "exclude_files": ["conftest.py"],
                "ignore_rules": ["HEADER_MISSING_DOCSTRING_START"],
            },
            {
                "max_complexity": 8,
                "max_parameters": 4,
                "max_statements": 40,
                "max_lines": 80,
                "exclude_dirs": ["tests"],
                "exclude_files": ["conftest.py"],
                "ignore_rules": [ViolationRule.HEADER_MISSING_DOCSTRING_START],
            },
        ),
    ],
    ids=[
        "minimal_config",
        "custom_excludes",
        "custom_ignore_rules",
        "full_custom_config",
    ],
)
def test_validate_config_ddt(input_config, expected_values):
    """Test validation of various valid configs using DDT."""
    validated = validate_config(input_config)

    # Check that all expected values are correctly set
    for key, expected_value in expected_values.items():
        actual_value = getattr(validated, key)
        assert actual_value == expected_value, f"Expected {key}={expected_value}, got {actual_value}"

    # Check that other values use defaults
    for key in DEFAULT_CONFIG:
        if key not in expected_values:
            if key == "ignore_rules" or key == "ignore_codes":
                # Special case for ignore_rules which is converted to enum values
                # ignore_codes is not used in ConfigModel
                continue
            try:
                actual_value = getattr(validated, key)
                expected_default = DEFAULT_CONFIG[key]
                assert (
                    actual_value == expected_default
                ), f"Expected default {key}={expected_default}, got {actual_value}"
            except AttributeError:
                # Skip fields that aren't in the model but might be in DEFAULT_CONFIG
                pass


def test_ignore_codes_backward_compatibility():
    """Test that legacy ignore_codes is mapped to ignore_rules."""
    # Config with the legacy ignore_codes field instead of ignore_rules
    legacy_config = {
        "max_complexity": 12,
        "ignore_codes": ["HEADER_LINE_1_MISMATCH", "FOOTER_MISSING"],
    }

    # Validate with legacy field
    validated = validate_config(legacy_config)

    # Verify the values were properly mapped to ignore_rules
    assert len(validated.ignore_rules) == 2
    assert ViolationRule.HEADER_LINE_1_MISMATCH in validated.ignore_rules
    assert ViolationRule.FOOTER_MISSING in validated.ignore_rules
