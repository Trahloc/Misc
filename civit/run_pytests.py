#!/usr/bin/env python
"""
# PURPOSE: Wrapper script to run pytest tests without problematic plugins.

## INTERFACES:
    - main(): Direct runner for pytest that completely bypasses the plugins

## DEPENDENCIES:
    - sys: For command-line arguments
    - os: For environment variables
    - subprocess: For running pytest as a subprocess
"""

import sys
import os
import subprocess
from pathlib import Path
import importlib.util

# Flag to prevent infinite recursion
CIVIT_PYTEST_RUNNING = "CIVIT_PYTEST_RUNNING"


def main():
    """
    Run pytest tests in a clean environment without problematic plugins.

    This function applies patches to fix problematic modules, then runs pytest
    with special flags to prevent plugin loading issues.

    Returns:
        int: Exit code from pytest
    """
    # Check if we're already running to prevent recursion
    if os.environ.get(CIVIT_PYTEST_RUNNING):
        print("Detected recursion in pytest running. Exiting.")
        return 1

    # Get the script directory
    script_dir = Path(__file__).parent.absolute()

    # First, try to patch the site-packages
    patch_script = script_dir / "patch_site_packages.py"
    if patch_script.exists():
        print(f"Running site-packages patch script: {patch_script}")
        # Import and run the patch
        spec = importlib.util.spec_from_file_location(
            "patch_site_packages", patch_script
        )
        patch_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patch_module)
        patch_module.patch_hypothesis_modules()

    # Prepare environment with special flags
    env = os.environ.copy()
    env[CIVIT_PYTEST_RUNNING] = "1"
    env["PYTHONPATH"] = str(script_dir)

    # Block problematic plugins explicitly
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTEST_PLUGINS"] = ""

    # Build the command with explicit -p no:plugin flags to disable plugins
    cmd = [sys.executable, "-m", "pytest", "--no-header", "-v"]

    # Add any additional arguments
    cmd.extend(sys.argv[1:] if len(sys.argv) > 1 else ["tests/"])

    print(f"Running pytest with command: {' '.join(cmd)}")

    # Run pytest as a subprocess
    result = subprocess.run(cmd, env=env, cwd=script_dir)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
