# tests/test_git_execution.py
import os
import subprocess
import sys
from pathlib import Path

import pytest

# --- Configuration ---
try:
    WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
except NameError:
    WORKSPACE_ROOT = Path.cwd().resolve()


def test_git_ls_files_subprocess():
    """
    Directly test the execution of 'git ls-files' via subprocess.run.
    """
    cmd = ["git", "ls-files"]
    print(f"\nAttempting to run: {' '.join(cmd)} in {WORKSPACE_ROOT}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,  # Fail on non-zero exit code
            cwd=WORKSPACE_ROOT,
            env=os.environ,  # Inherit environment
        )
        print("Command executed successfully.")
        print(f"Return Code: {result.returncode}")
        print(f"STDOUT (first 100 chars): {result.stdout[:100]}...")
        # Basic assertions
        assert result.returncode == 0, "git ls-files exited with non-zero status"
        assert len(result.stdout) > 0, "git ls-files produced no output"
        assert ".gitignore" in result.stdout, "Expected file .gitignore not found in output"

    except FileNotFoundError:
        pytest.fail("git command not found. Is git installed and in the PATH?")
    except subprocess.CalledProcessError as e:
        print("ERROR: 'git ls-files' failed!", file=sys.stderr)
        print(f"Return Code: {e.returncode}", file=sys.stderr)
        print(f"STDERR:\n{e.stderr}", file=sys.stderr)
        print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
        pytest.fail(f"git ls-files failed with CalledProcessError: {e}")
    except Exception as e:
        print("ERROR: An unexpected exception occurred!", file=sys.stderr)
        print(f"Exception Type: {type(e)}", file=sys.stderr)
        print(f"Exception Args: {e.args}", file=sys.stderr)
        pytest.fail(f"Unexpected exception during 'git ls-files' execution: {e}")
