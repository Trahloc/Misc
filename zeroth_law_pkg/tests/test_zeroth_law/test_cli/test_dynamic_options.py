import pytest
from click.testing import CliRunner

# Assume zlt.cli.main is the entry point
from zeroth_law.cli import main as zlt_cli

# Helper function to load expected options (adjust path if needed)
import json
from pathlib import Path


def load_option_defs():
    options_path = Path(__file__).parents[3] / "src" / "zeroth_law" / "zlt_options_definitions.json"
    with open(options_path, "r") as f:
        return json.load(f)


OPTION_DEFS = load_option_defs()


@pytest.mark.parametrize(
    "option_name, expected_flags, expected_description",
    [
        ("verbose", "-v, --verbose", OPTION_DEFS["verbose"]["description"]),
        # Add more test cases for other options here later
        ("quiet", "-q, --quiet", OPTION_DEFS["quiet"]["description"]),
        ("config", "--config FILE_PATH", OPTION_DEFS["config"]["description"]),
        ("recursive", "-r, --recursive", OPTION_DEFS["recursive"]["description"]),
        # ("paths", "PATHS", OPTION_DEFS["paths"]["description"]), # Positional args don't appear in options help
    ],
)
def test_dynamic_cli_options_in_help(option_name, expected_flags, expected_description):
    """Verify that dynamically added options appear correctly in --help output."""
    runner = CliRunner()
    # Assuming ZLT commands are defined directly under the main entry point for now
    # If options are per-subcommand, this test needs adjustment
    result = runner.invoke(zlt_cli, ["--help"])

    assert result.exit_code == 0
    # Check if the flags and description appear together in the help output
    # Simple check: Look for the flag part and description on the same line or nearby
    # More robust check might involve parsing the help text structure
    # Example check (might need refinement based on Click's help format):
    help_lines = result.output.splitlines()
    option_line_found = False
    for line in help_lines:
        line_stripped = line.strip()
        # Handle flags potentially split from description by whitespace
        if line_stripped.startswith(expected_flags):
            # Check if description follows on the same line (common pattern)
            if expected_description in line_stripped:
                option_line_found = True
                break
            # TODO: Handle cases where description might be on the next line
            #       or formatting is different.

    assert option_line_found, f"Help output did not contain expected line for option '{option_name}' with flags '{expected_flags}' and description '{expected_description}'.\nOutput:\n{result.output}"
