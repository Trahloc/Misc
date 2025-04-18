"""Discovers potential CLI tools from the active virtual environment and filters them.

Provides functions to get potential tools and update the managed tools configuration.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml  # Requires PyYAML

# --- Constants ---
# Assume this script runs from the workspace root or src/zeroth_law/dev_scripts
try:
    # Assumes the script is under src/zeroth_law/dev_scripts
    _SCRIPT_DIR = Path(__file__).parent.resolve()
    WORKSPACE_ROOT = _SCRIPT_DIR.parents[2]  # src/zeroth_law/dev_scripts -> workspace
except NameError:
    # Fallback if __file__ not defined (e.g., interactive import)
    WORKSPACE_ROOT = Path.cwd().resolve()

TOOLS_CONFIG_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "managed_tools.yaml"
TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"

# --- Configuration Loading ---


def load_tools_config() -> Dict[str, List[str]]:
    """Loads the managed tools configuration from YAML."""
    default_config: Dict[str, List[str]] = {"managed_tools": [], "excluded_executables": []}
    if not TOOLS_CONFIG_PATH.is_file():
        print(f"Warning: Config file not found at {TOOLS_CONFIG_PATH}. Using defaults.")
        return default_config
    try:
        with open(TOOLS_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if not isinstance(config, dict):
                raise ValueError("Config root must be a dictionary.")
            # Basic validation
            managed = config.get("managed_tools", [])
            excluded = config.get("excluded_executables", [])
            if not isinstance(managed, list) or not all(isinstance(i, str) for i in managed):
                raise ValueError("'managed_tools' must be a list of strings.")
            if not isinstance(excluded, list) or not all(isinstance(i, str) for i in excluded):
                raise ValueError("'excluded_executables' must be a list of strings.")
            return {"managed_tools": managed, "excluded_executables": excluded}
    except (yaml.YAMLError, ValueError, IOError) as e:
        print(f"Error loading or parsing {TOOLS_CONFIG_PATH}: {e}. Using defaults.")
        return default_config


def save_tools_config(config: Dict[str, List[str]]) -> None:
    """Saves the tools configuration to YAML."""
    try:
        # Ensure lists are sorted for consistency
        config["managed_tools"] = sorted(list(set(config.get("managed_tools", []))))
        config["excluded_executables"] = sorted(list(set(config.get("excluded_executables", []))))
        TOOLS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOOLS_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"Successfully saved configuration to {TOOLS_CONFIG_PATH}")
    except (IOError, TypeError) as e:
        print(f"Error saving configuration to {TOOLS_CONFIG_PATH}: {e}")


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
    parser.add_argument("--check", action="store_true", help="Check for newly discovered tools that are not managed or excluded.")
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
            print("No new potential tools found. managed_tools.yaml is up-to-date with discovered non-excluded executables.")
            sys.exit(0)
    else:
        print("Please specify an action, e.g., --check")
