import pytest
from pathlib import Path
import toml

# Now import should work
from zeroth_law.dev_scripts.config_reader import load_tool_lists_from_toml

# Define a sample valid pyproject.toml content
VALID_TOML_CONTENT = """
[tool.zeroth-law.tools]
whitelist = ["tool_a", "tool_b"]
blacklist = ["tool_c", "tool_d"]
"""

# Define sample TOML with missing keys
MISSING_KEYS_TOML_CONTENT = """
[tool.zeroth-law.tools]
# whitelist = ["tool_a", "tool_b"]
# blacklist = ["tool_c", "tool_d"]
"""

# Define sample TOML with missing tools section
MISSING_SECTION_TOML_CONTENT = """
[project]
name = "test"
"""

# Define sample TOML with invalid data types
INVALID_TYPE_TOML_CONTENT = """
[tool.zeroth-law.tools]
whitelist = "not_a_list"
blacklist = 123
"""

def test_load_valid_toml(tmp_path):
    """Test loading from a valid pyproject.toml file."""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text(VALID_TOML_CONTENT, encoding="utf-8")

    whitelist, blacklist = load_tool_lists_from_toml(toml_path)

    assert isinstance(whitelist, set)
    assert isinstance(blacklist, set)
    assert whitelist == {"tool_a", "tool_b"}
    assert blacklist == {"tool_c", "tool_d"}

def test_load_missing_keys(tmp_path):
    """Test loading when whitelist/blacklist keys are missing."""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text(MISSING_KEYS_TOML_CONTENT, encoding="utf-8")

    whitelist, blacklist = load_tool_lists_from_toml(toml_path)

    assert whitelist == set()
    assert blacklist == set()

def test_load_missing_section(tmp_path):
    """Test loading when the [tool.zeroth-law.tools] section is missing."""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text(MISSING_SECTION_TOML_CONTENT, encoding="utf-8")

    whitelist, blacklist = load_tool_lists_from_toml(toml_path)

    assert whitelist == set()
    assert blacklist == set()

def test_load_invalid_types(tmp_path):
    """Test loading when whitelist/blacklist have incorrect types."""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text(INVALID_TYPE_TOML_CONTENT, encoding="utf-8")

    # Expecting a ValueError due to wrong types
    with pytest.raises(ValueError):
         load_tool_lists_from_toml(toml_path)

def test_load_file_not_found():
    """Test loading when the pyproject.toml file does not exist."""
    non_existent_path = Path("./non_existent_pyproject.toml") # Use relative path likely in tmp
    if non_existent_path.exists():
        non_existent_path.unlink() # Ensure it doesn't exist

    # Expecting FileNotFoundError
    with pytest.raises(FileNotFoundError):
        load_tool_lists_from_toml(non_existent_path)

def test_load_invalid_toml_content(tmp_path):
    """Test loading from a file with invalid TOML syntax."""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text("this is not valid toml content = {", encoding="utf-8")

    # Expecting TomlDecodeError
    with pytest.raises(toml.TomlDecodeError):
        load_tool_lists_from_toml(toml_path)