import pytest
import json
from pathlib import Path
from click.testing import CliRunner

# Assuming zlt_cli is the main entry point function
# from zeroth_law.cli import main as zlt_cli # OLD
from zeroth_law.cli import cli_group as zlt_cli  # NEW: Use the group object

# Get the directory of the current test file
_TEST_DIR = Path(__file__).parent
_ZLT_ROOT = _TEST_DIR.parent.parent.parent / "src" / "zeroth_law"
_OPTIONS_DEF_PATH = _ZLT_ROOT / "zlt_options_definitions.json"

# Load option definitions for parametrization
with open(_OPTIONS_DEF_PATH, "r", encoding="utf-8") as f:
    OPTION_DEFS = json.load(f)


# --- Test Cases --- #
@pytest.mark.parametrize(
    "option_name, expected_flags, expected_description",
    [
        ("verbose", "-v, --verbose", "Increase verbosity. -v for INFO, -vv for DEBUG."),
        ("quiet", "-q, --quiet", "Suppress all output except errors."),
        ("config", "--config FILE_PATH", "Load configuration from a specific file."),
        # ("recursive", "-r, --recursive", OPTION_DEFS["recursive"]["description"]), # Recursive removed as global
        # ("paths", "PATHS", OPTION_DEFS["paths"]["description"]), # Positional args don't appear in options help
    ],
)
def test_dynamic_cli_options_in_help(option_name, expected_flags, expected_description):
    """Verify that dynamically added options appear correctly in --help output."""
    runner = CliRunner()
    # Assuming ZLT commands are defined directly under the main entry point for now
    # If options are per-subcommand, this test needs adjustment
    result = runner.invoke(zlt_cli, ["--help"])

    # Check exit code
    assert result.exit_code == 0, f"CLI exited with code {result.exit_code}: {result.output}"

    # Check if the option flags are present
    assert (
        expected_flags in result.output
    ), f"Expected flags '{expected_flags}' not found in help output for '{option_name}'"

    # Check if the description is present
    # Be slightly flexible with whitespace
    cleaned_output = " ".join(result.output.split())
    cleaned_description = " ".join(expected_description.split())
    assert (
        cleaned_description in cleaned_output
    ), f"Expected description '{expected_description}' not found in help output for '{option_name}'"

    print(f"Test passed for option: {option_name}")  # Optional: Print success message
