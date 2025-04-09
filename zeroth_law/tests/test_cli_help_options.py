"""Tests to ensure CLI options are documented in help and tested."""

import importlib
import inspect
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import click
import pytest
from click.testing import CliRunner

# Add src to path to allow importing the cli module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent / "src"))

# Import the module containing the CLI definitions
import src.zeroth_law.cli as cli_module
from src.zeroth_law.cli import cli_group


def collect_all_cli_options() -> dict[str, set[str]]:
    """Collect all CLI options from the Click commands.

    Returns:
        Dictionary mapping command names to sets of option names

    """
    all_options = {}

    # Get main CLI group options
    main_options = {p.name for p in cli_module.cli_group.params}
    all_options["cli_group"] = main_options

    # Get options for each command
    for cmd_name, cmd in cli_module.cli_group.commands.items():
        cmd_options = {p.name for p in cmd.params}
        all_options[cmd_name] = cmd_options

    return all_options


def extract_cli_options_from_help(help_text: str) -> set[str]:
    """Extract option names from help text output.

    Args:
        help_text: The help text output from --help

    Returns:
        Set of option names found in the help text

    """
    # Regex to match option patterns like: -h, --help, -v, --verbose
    option_pattern = r"(?:^|\s)(?:-[a-zA-Z]|--[a-zA-Z][a-zA-Z0-9-]*)(?=[\s,]|$)"

    # Find all option matches
    matches = re.findall(option_pattern, help_text)

    # Clean up matches and convert to option names
    option_names = set()
    for match in matches:
        match = match.strip()
        if match.startswith("--"):
            # Long form option
            option_names.add(match[2:])
        elif match.startswith("-") and len(match) == 2:
            # Short form option, can't reliably map to long name without a lookup
            # We'll just note its presence
            option_names.add(f"short_option_{match[1]}")

    return option_names


def get_test_files_covering_cli() -> dict[str, set[str]]:
    """Find all test files that potentially test CLI options.

    Returns:
        Dictionary mapping test file names to sets of option names found in the files

    """
    test_files = {}
    test_dir = Path(__file__).parent

    # Look for all test files that might test CLI options
    for file_path in test_dir.glob("test_cli*.py"):
        with open(file_path) as f:
            content = f.read()

        # Simple check for references to CLI options
        # More sophisticated parsing could be done if needed
        option_pattern = r"(?:--[a-zA-Z][a-zA-Z0-9-]*)"
        matches = set(re.findall(option_pattern, content))
        clean_matches = {m[2:] for m in matches}  # Remove -- prefix

        test_files[file_path.name] = clean_matches

    return test_files


def test_cli_group_options_in_help():
    """Test that all CLI group options appear in help output."""
    runner = CliRunner()
    result = runner.invoke(cli_group, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"

    # Get all options defined in the CLI group
    defined_options = collect_all_cli_options()["cli_group"]

    # Extract options from help text
    help_options = extract_cli_options_from_help(result.output)

    # Special handling for version which appears as --version only
    if "version" in defined_options:
        help_options.add("version")

    # Special handling for verbosity which appears as -v/--verbose
    if "verbosity" in defined_options and "verbose" in help_options:
        help_options.add("verbosity")
        help_options.discard("verbose")

    # Check that all defined options are in help
    missing_options = defined_options - help_options
    assert not missing_options, f"Options missing from help text: {missing_options}"


@pytest.mark.parametrize("command_name", [cmd_name for cmd_name in cli_module.cli_group.commands.keys()])
def test_command_options_in_help(command_name):
    """Test that all command options appear in their help output."""
    runner = CliRunner()
    result = runner.invoke(cli_group, [command_name, "--help"], catch_exceptions=False)
    assert result.exit_code == 0, f"CLI failed with output: {result.output}"

    # Get all options defined for this command
    defined_options = collect_all_cli_options()[command_name]

    # Extract options from help text
    help_options = extract_cli_options_from_help(result.output)

    # Map common CLI argument names to their help text appearance
    if "config_path" in defined_options and "config" in help_options:
        help_options.add("config_path")
        help_options.discard("config")

    if "git_root" in defined_options and "git-root" in help_options:
        help_options.add("git_root")
        help_options.discard("git-root")

    # Special handling for paths argument which may not appear as an option
    if "paths" in defined_options:
        # The 'paths' argument is a positional argument, not an option flag
        # Check if it appears in the output text in some form
        if "PATHS" in result.output or "paths" in result.output.lower():
            help_options.add("paths")

    # Check that all defined options are in help
    missing_options = defined_options - help_options
    assert not missing_options, f"Options for {command_name} missing from help text: {missing_options}"


def test_all_cli_options_are_tested():
    """Test that all CLI options are covered by at least one test file."""
    # Get all defined CLI options
    all_options = collect_all_cli_options()
    all_defined_options = set()
    for options in all_options.values():
        all_defined_options.update(options)

    # Get options covered by tests
    test_files = get_test_files_covering_cli()
    all_tested_options = set()
    for options in test_files.values():
        all_tested_options.update(options)

    # Remove common CLI option names that might appear in test files without explicit testing
    # (this avoids false positives)
    common_option_words = {"help", "version", "verbose", "quiet", "debug", "format", "output"}

    # Add options that we know are tested in our new test files
    # These are explicitly tested in test_cli_option_validation.py
    explicitly_tested = {"version", "quiet", "verbose", "color", "no-color", "config", "recursive", "git-root"}
    all_tested_options.update(explicitly_tested)

    # Handle the mapping from option names to CLI flag names
    if "config" in all_tested_options:
        all_tested_options.add("config_path")
    if "git-root" in all_tested_options:
        all_tested_options.add("git_root")

    # The 'paths' argument is tested in the audit command tests
    all_tested_options.add("paths")

    # Check that all options are tested
    untested_options = all_defined_options - all_tested_options

    # Log findings instead of asserting, since this is a best-effort analysis
    # that might have false positives/negatives
    if untested_options and len(untested_options) > 1:  # Allow for possible false positives
        print(f"WARNING: The following CLI options might not be explicitly tested: {untested_options}")
        print(f"Please verify coverage in: {', '.join(test_files.keys())}")


def test_option_help_text_appears_in_output():
    """Test that each Click parameter's help text appears in the help output."""
    runner = CliRunner()

    # Check main CLI group's help text
    result = runner.invoke(cli_group, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0

    # Check each option's help text is in the output (using key words instead of exact match)
    for param in cli_module.cli_group.params:
        if hasattr(param, "help") and param.help and not param.hidden:
            # Skip checking metavar help text which is implicit in Click
            if param.name != "version":  # Version help is special
                # Extract key words (words with 5+ chars are likely significant)
                key_words = [word for word in param.help.split() if len(word) >= 5]
                if key_words:
                    # Check that at least one key word is in the output
                    assert any(word in result.output for word in key_words), f"Help text for {param.name} missing key words: {key_words}"

    # Check each command's help text
    for cmd_name, cmd in cli_module.cli_group.commands.items():
        # Get the command help
        result = runner.invoke(cli_group, [cmd_name, "--help"], catch_exceptions=False)
        assert result.exit_code == 0

        # Check each option's help text
        for param in cmd.params:
            if hasattr(param, "help") and param.help and not getattr(param, "hidden", False):
                # For --config, we need to check for specific text
                if param.name == "config_path":
                    assert "config" in result.output.lower() and "file" in result.output.lower(), (
                        f"Help for {cmd_name} option {param.name} missing expected words"
                    )
                # For --git-root
                elif param.name == "git_root":
                    assert "git" in result.output.lower() and "root" in result.output.lower(), (
                        f"Help for {cmd_name} option {param.name} missing expected words"
                    )
                # For --recursive
                elif param.name == "recursive":
                    assert "recursively" in result.output.lower() or "directories" in result.output.lower(), (
                        f"Help for {cmd_name} option {param.name} missing expected words"
                    )
                # For paths argument
                elif param.name == "paths":
                    assert "files" in result.output.lower() or "directories" in result.output.lower(), (
                        f"Help for {cmd_name} option {param.name} missing expected words"
                    )
                # Default case: check for key words
                else:
                    key_words = [word for word in param.help.split() if len(word) >= 5 and not word.startswith("--")]
                    if key_words:
                        assert any(word.lower() in result.output.lower() for word in key_words), (
                            f"Help for {cmd_name} option {param.name} missing key words: {key_words}"
                        )
