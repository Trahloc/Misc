# FILE: src/zeroth_law/analyzers/precommit_analyzer.py
"""Analyzes .pre-commit-config.yaml files for ZLF compliance."""

import structlog
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

log = structlog.get_logger()

# Hooks known to require the project's virtual environment
# TODO: Make this configurable?
PROJECT_ENV_HOOKS: Set[str] = {
    "mypy",
    "pytest",
    "autoinit",
    "zeroth-law",  # Assuming our own analyzer hook might run locally
    # Add other hooks IDs as needed
}


def analyze_precommit_config(config_path: Path) -> Dict[str, List[Any]]:
    """Analyzes a .pre-commit-config.yaml file for ZLF workflow compliance.

    Checks hooks in PROJECT_ENV_HOOKS to ensure they use `language: system`
    and an `entry` starting with `uv run `.

    Args:
    ----
        config_path: Path to the .pre-commit-config.yaml file.

    Returns:
    -------
        A dictionary containing violation messages, keyed by category.
        Returns an empty dictionary if no violations are found or file cannot be parsed.
    """
    violations: Dict[str, List[Any]] = {"precommit_workflow": []}
    log.debug(f"Analyzing pre-commit config: {config_path}")

    try:
        with config_path.open("r") as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        log.error(f"Pre-commit config file not found: {config_path}")
        violations["precommit_workflow"].append(f"File not found: {config_path}")
        return violations
    except yaml.YAMLError as e:
        log.error(f"Error parsing pre-commit config file {config_path}: {e}")
        violations["precommit_workflow"].append(f"YAML parsing error: {e}")
        return violations
    except Exception as e:
        log.error(f"Unexpected error reading pre-commit config {config_path}: {e}")
        violations["precommit_workflow"].append(f"Unexpected read error: {e}")
        return violations

    if not isinstance(config_data, dict) or "repos" not in config_data:
        log.warning(f"Invalid pre-commit config format in {config_path}: Missing 'repos' key.")
        # Allow processing potentially malformed files, but don't crash
        return {}  # Or add a specific violation if preferred

    for repo in config_data.get("repos", []):
        if not isinstance(repo, dict) or "hooks" not in repo:
            continue

        for hook in repo.get("hooks", []):
            if not isinstance(hook, dict) or "id" not in hook:
                continue

            hook_id = hook.get("id")
            if hook_id in PROJECT_ENV_HOOKS:
                language = hook.get("language")
                entry = hook.get("entry", "")  # Default to empty string if missing

                if language != "system":
                    msg = (
                        f"Hook '{hook_id}' should use 'language: system' to run in the project environment, "
                        f"but found 'language: {language}'."
                    )
                    violations["precommit_workflow"].append(msg)
                    log.debug(msg)

                if not entry.strip().startswith("uv run "):
                    msg = (
                        f"Hook '{hook_id}' should use 'uv run ...' in 'entry' to ensure execution via project venv, "
                        f"but found entry: '{entry}'."
                    )
                    violations["precommit_workflow"].append(msg)
                    log.debug(msg)

    # Return only if violations were actually found
    if not violations["precommit_workflow"]:
        return {}

    return violations
