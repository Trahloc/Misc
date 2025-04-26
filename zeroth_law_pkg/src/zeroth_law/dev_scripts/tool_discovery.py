"""Discovers potential CLI tools from the active virtual environment and filters them.

Provides functions to get potential tools and update the managed tools configuration.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml  # Requires PyYAML
import toml  # Add TOML import
import logging  # Add logging import

# --- Constants ---
# Assume this script runs from the workspace root or src/zeroth_law/dev_scripts
try:
    # Assumes the script is under src/zeroth_law/dev_scripts
    _SCRIPT_DIR = Path(__file__).parent.resolve()
    WORKSPACE_ROOT = _SCRIPT_DIR.parents[2]  # src/zeroth_law/dev_scripts -> workspace
except NameError:
    # Fallback if __file__ not defined (e.g., interactive import)
    WORKSPACE_ROOT = Path.cwd().resolve()

TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
PYPROJECT_PATH = WORKSPACE_ROOT / "pyproject.toml"

log = logging.getLogger(__name__)  # Add logger

# --- Configuration Loading ---


def load_tools_config() -> Dict[str, List[str]]:
    """Loads the managed and excluded tools configuration from pyproject.toml."""
    default_config: Dict[str, List[str]] = {"managed_tools": [], "excluded_executables": []}

    if not PYPROJECT_PATH.is_file():
        log.error(f"Configuration file not found: {PYPROJECT_PATH}")
        return default_config

    try:
        with open(PYPROJECT_PATH, "r", encoding="utf-8") as f:
            data = toml.load(f)

        # Navigate to the correct section
        zlt_config = data.get("tool", {}).get("zeroth-law", {})
        managed_tools_config = zlt_config.get("managed-tools", {})

        # Extract lists using the keys from pyproject.toml
        managed = managed_tools_config.get("whitelist", [])
        excluded = managed_tools_config.get("blacklist", [])

        # Basic validation
        if not isinstance(managed, list) or not all(isinstance(i, str) for i in managed):
            raise ValueError("'[tool.zeroth-law.managed-tools].whitelist' must be a list of strings.")
        if not isinstance(excluded, list) or not all(isinstance(i, str) for i in excluded):
            raise ValueError("'[tool.zeroth-law.managed-tools].blacklist' must be a list of strings.")

        # Return in the expected format
        return {"managed_tools": managed, "excluded_executables": excluded}

    except (toml.TomlDecodeError, ValueError, IOError) as e:
        log.error(f"Error loading or parsing {PYPROJECT_PATH}: {e}", exc_info=True)
        return default_config


# --- Discovery Logic (Refactored from test_tool_integration.py) ---


def get_potential_managed_tools() -> Set[str]:
    """Gets a list of potential CLI tools from the active venv bin, excluding configured noise."""
    config = load_tools_config()
    excluded_scripts = set(config.get("excluded_executables", []))

    potential_tools: Set[str] = set()
    try:
        venv_path = Path(sys.prefix)
        bin_path = venv_path / ("Scripts" if sys.platform == "win32" else "bin")

        if not bin_path.is_dir():
            print(f"Warning: Active venv executable directory not found: {bin_path}", file=sys.stderr)
            return set()  # Return empty if bin not found

        all_scripts = [f.name for f in bin_path.iterdir() if f.is_file()]

        for script in all_scripts:
            script_base = Path(script).stem
            if script_base not in excluded_scripts:
                potential_tools.add(script_base)

        return potential_tools

    except Exception as e:
        print(f"Unexpected error getting CLI tools from venv: {e}", file=sys.stderr)
        return set()  # Return empty on error


# --- Helper to get existing tool directories ---
def get_existing_tool_dirs() -> Set[str]:
    """Gets the names of directories present under the tools directory."""
    if not TOOLS_DIR.is_dir():
        return set()
    return {d.name for d in TOOLS_DIR.iterdir() if d.is_dir()}


# --- Main Script Logic --- (Example: Can be run via `python ... tool_discovery.py --check`)
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Discover and manage ZLT tool configurations.")
    parser.add_argument(
        "--check", action="store_true", help="Check for newly discovered tools that are not managed or excluded."
    )
    # Add --update-list later if needed, requires careful implementation

    args = parser.parse_args()

    if args.check:
        print("Running tool discovery check...")
        potential_tools = get_potential_managed_tools()
        config = load_tools_config()
        known_managed_tools = set(config.get("managed_tools", []))

        unknown_tools = potential_tools - known_managed_tools

        if unknown_tools:
            print("\n--------------------------------------------------")
            print(f"Newly discovered potential tools found: {sorted(list(unknown_tools))}")
            print("These executables exist in the environment bin directory but are neither")
            print("explicitly excluded nor listed as managed in managed_tools.yaml.")
            print("\nAction Required: For each listed executable, research it and update managed_tools.yaml:")
            print("  - If it's a tool ZLT should manage, add its name to the 'managed_tools' list.")
            print("  - If it's cruft/helper/unwanted, add its name to the 'excluded_executables' list.")
            print("--------------------------------------------------")
            sys.exit(1)  # Exit with error code to signal failure for CI/automation
        else:
            print(
                "No new potential tools found. managed_tools.yaml is up-to-date with discovered non-excluded executables."
            )
            sys.exit(0)
    else:
        print("Please specify an action, e.g., --check")
