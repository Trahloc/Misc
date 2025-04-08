"""Tests for configuration loading functionality."""

# Target function
from zeroth_law.config_loader import load_python_version_from_pyproject


def test_load_python_version_success() -> None:
    """Verify successfully loading the Python version from pyproject.toml."""
    # Arrange
    expected_version = ">=3.13,<4.0"
    pyproject_path = "pyproject.toml"  # Use the actual project file for integration

    # Act
    actual_version = load_python_version_from_pyproject(pyproject_path)

    # Assert
    assert actual_version == expected_version


# Next steps: Add tests for FileNotFoundError, KeyError, TOMLDecodeError, TypeError
