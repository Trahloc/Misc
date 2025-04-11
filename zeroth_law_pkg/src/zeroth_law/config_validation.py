"""Configuration validation using Pydantic models.

Provides strict validation for Zeroth Law configuration values.
"""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Import defaults to use as fallbacks
from zeroth_law.config_defaults import DEFAULT_CONFIG

log = logging.getLogger(__name__)


class ViolationRule(str, Enum):
    """Enumeration of all possible violation rule codes that can be ignored."""

    HEADER_LINE_1_MISMATCH = "HEADER_LINE_1_MISMATCH"
    HEADER_MISSING_FILE_LINE = "HEADER_MISSING_FILE_LINE"
    HEADER_MISSING_DOCSTRING_START = "HEADER_MISSING_DOCSTRING_START"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    HEADER_CHECK_OS_ERROR = "HEADER_CHECK_OS_ERROR"
    HEADER_CHECK_UNEXPECTED_ERROR = "HEADER_CHECK_UNEXPECTED_ERROR"
    FOOTER_MISSING = "FOOTER_MISSING"
    FOOTER_CHECK_OS_ERROR = "FOOTER_CHECK_OS_ERROR"
    FOOTER_CHECK_UNEXPECTED_ERROR = "FOOTER_CHECK_UNEXPECTED_ERROR"

    @classmethod
    def get_all_values(cls) -> set[str]:
        """Get all valid rule code values as a set of strings."""
        return {item.value for item in cls}


class ConfigModel(BaseModel):
    """Pydantic model for Zeroth Law configuration validation.

    All fields have default values that match DEFAULT_CONFIG.
    """

    # Analysis thresholds
    max_complexity: int = Field(
        default=DEFAULT_CONFIG["max_complexity"],
        description="Maximum allowed cyclomatic complexity",
        ge=0,
    )
    max_parameters: int = Field(
        default=DEFAULT_CONFIG["max_parameters"],
        description="Maximum allowed function parameters",
        ge=0,
    )
    max_statements: int = Field(
        default=DEFAULT_CONFIG["max_statements"],
        description="Maximum allowed function statements",
        ge=0,
    )
    max_lines: int = Field(
        default=DEFAULT_CONFIG["max_lines"],
        description="Maximum allowed executable lines in file",
        ge=0,
    )

    # Filtering options
    exclude_dirs: list[str] = Field(
        default=DEFAULT_CONFIG["exclude_dirs"],
        description="Directories to exclude from analysis",
    )
    exclude_files: list[str] = Field(
        default=DEFAULT_CONFIG["exclude_files"],
        description="Files to exclude from analysis",
    )

    # Rule configuration
    ignore_rules: list[ViolationRule] = Field(
        default=[],
        description="Violation rules to ignore during analysis",
    )

    # Additional validation
    @field_validator("exclude_dirs", "exclude_files")
    @classmethod
    def validate_path_lists(cls, v: Any) -> list[str]:
        """Ensure path lists contain valid string values."""
        if not isinstance(v, list):
            raise ValueError("Must be a list of directory/file names")

        # Return strings only (convert Path objects, etc.)
        return [str(item) for item in v]

    @model_validator(mode="before")
    @classmethod
    def map_ignore_codes_to_rules(cls, data: Any) -> Any:
        """Map the legacy 'ignore_codes' field to 'ignore_rules' if present."""
        if not isinstance(data, dict):
            return data

        # If ignore_codes is present but ignore_rules is not, map it
        if "ignore_codes" in data and "ignore_rules" not in data:
            data["ignore_rules"] = data.pop("ignore_codes")
            log.debug("Mapped 'ignore_codes' to 'ignore_rules' for backward compatibility")

        return data


def validate_config(config_dict: dict[str, Any]) -> ConfigModel:
    """Validate configuration dictionary using Pydantic model.

    Args:
        config_dict: Dictionary containing configuration values

    Returns:
        Validated ConfigModel instance

    Raises:
        ValidationError: If configuration values are invalid

    """
    # Any keys not in config_dict will use default values from the model
    validated_config = ConfigModel.model_validate(config_dict)
    log.debug("Configuration validated successfully")
    return validated_config
