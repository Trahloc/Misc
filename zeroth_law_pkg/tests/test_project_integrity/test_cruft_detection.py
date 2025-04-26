# tests/test_cruft_detection.py
import fnmatch  # For pattern matching
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# --- Configuration ---
try:
    # Go up three levels: tests/test_project_integrity -> tests -> workspace_root
    WORKSPACE_ROOT = Path(__file__).parent.parent.parent.resolve()
except NameError:
    WORKSPACE_ROOT = Path.cwd().resolve()

# STRUCTURE_DATA_PATH = WORKSPACE_ROOT / "project_structure.json"  # Old path
STRUCTURE_DATA_PATH = WORKSPACE_ROOT / "tests" / "test_data" / "project_structure.json"  # New path

# Files/patterns explicitly allowed to exist even if not in structure data
# Use fnmatch patterns (similar to .gitignore) relative to WORKSPACE_ROOT
# --- REMOVED HARDCODED LIST - Now loaded from STRUCTURE_DATA_PATH --- #
# KNOWN_GOOD_PATTERNS = {
#    ...
# }

# --- Helper ---


def get_git_tracked_files(repo_root: Path) -> set[str]:
    """Get a set of all files tracked by git, relative to repo_root."""
    try:
        cmd = ["git", "ls-files"]
        print(f"\nAttempting to run: {' '.join(cmd)} in {repo_root}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
            env=os.environ,
        )
        print("subprocess.run for git ls-files completed successfully.")
        # Process the output *after* confirming subprocess success
        tracked_files = {Path(p).as_posix() for p in result.stdout.strip().splitlines()}
        print(f"Processed {len(tracked_files)} files.")
        return tracked_files
    except FileNotFoundError:
        pytest.skip("git command not found.")
        return set()
    except subprocess.CalledProcessError as e:
        print(f"Error running git ls-files: {e}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        pytest.skip("Failed to list git tracked files.")
        return set()
    except Exception as e:
        # This should now hopefully only catch errors during output processing
        print(f"Unexpected error type during output processing: {type(e)}", file=sys.stderr)
        print(f"Unexpected error args during output processing: {e.args}", file=sys.stderr)
        print(f"Unexpected error processing git output: {e}", file=sys.stderr)
        pytest.skip("Unexpected error processing git output.")
        return set()


def is_allowed(file_path: str, allowed_patterns: set[str]) -> bool:
    """Check if a file path matches any of the allowed fnmatch patterns or is exactly present."""
    # Check for exact match first (common case for source files listed in structure data)
    if file_path in allowed_patterns:
        return True
    # Then check fnmatch patterns
    for pattern in allowed_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


# --- Test ---


def test_no_unexpected_files_in_repo():
    """
    Check for files tracked by git that are not expected based on structure data
    or known good patterns.
    """
    # --- PRELIMINARY CHECK: Ensure structure data is committed ---
    structure_file_rel_path = STRUCTURE_DATA_PATH.relative_to(WORKSPACE_ROOT).as_posix()
    try:
        # Use --porcelain v1 for stable, scriptable output
        # Check status relative to HEAD (committed state)
        cmd_status = ["git", "status", "--porcelain", str(structure_file_rel_path)]
        print(f"\nChecking git status for: {structure_file_rel_path}")
        result_status = subprocess.run(
            cmd_status, capture_output=True, text=True, check=True, cwd=WORKSPACE_ROOT, env=os.environ
        )
        if result_status.stdout.strip():  # If output is not empty, file has changes
            status_lines = result_status.stdout.strip()
            # print(f"INFO: Uncommitted changes detected for {structure_file_rel_path}:\n  {status_lines}", file=sys.stderr)
            # print(f"INFO: Staging {structure_file_rel_path} automatically.", file=sys.stderr)
            # # Stage the file
            # cmd_add = ["git", "add", str(structure_file_rel_path)]
            # result_add = subprocess.run(cmd_add, capture_output=True, text=True, check=True,
            #                             cwd=WORKSPACE_ROOT, env=os.environ)
            # print(f"INFO: 'git add' completed for {structure_file_rel_path}.")
            # Fail the test with the prioritized message
            pytest.fail(
                f"Low Priority: The structure data file '{structure_file_rel_path}' has uncommitted changes:\n"
                f"  {status_lines}\n"
                f"This test requires a clean, committed structure file to be reliable. "
                f"Please ensure other tests pass, then commit changes to this file."
            )
        else:
            print(f"'{structure_file_rel_path}' is clean according to git status.")

    except FileNotFoundError:
        pytest.skip("git command not found.")  # Skip if git isn't available
    except subprocess.CalledProcessError as e:
        # Handle case where file might not be tracked yet (ls-files handles this later)
        # or other git status errors
        print(
            f"Warning: 'git status' failed for {structure_file_rel_path}. Proceeding, but result might be based on stale data if file exists.",
            file=sys.stderr,
        )
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        assert not mock_print.called, (
            f"Script printed '{message}'. Should silently proceed, "
            f"but result might be based on stale data if file exists."
        )
    except Exception as e:
        # Catch other potential errors during the status check
        pytest.fail(f"Unexpected error checking git status for {structure_file_rel_path}: {e}")
    # --- END PRELIMINARY CHECK ---

    # 1. Get actual tracked files
    actual_files = get_git_tracked_files(WORKSPACE_ROOT)
    if not actual_files:
        pytest.skip("Could not retrieve tracked files from git.")
        return

    # 2. Load expected source files and allowed patterns from structure data
    expected_source_files = set()
    allowed_root_patterns = set()
    # print(f"DEBUG: Checking STRUCTURE_DATA_PATH: {STRUCTURE_DATA_PATH.resolve()}", file=sys.stderr)
    if STRUCTURE_DATA_PATH.is_file():
        try:
            with open(STRUCTURE_DATA_PATH, "r") as f:
                data = json.load(f)
            # Assume paths in JSON are relative to WORKSPACE_ROOT or easily convertible
            # Normalize to POSIX paths for consistent matching
            expected_source_files = {Path(p).as_posix() for p in data.get("source_files", [])}
            # --- ADDED: Load allowed root patterns --- #
            allowed_root_patterns = {Path(p).as_posix() for p in data.get("allowed_root_patterns", [])}
        except json.JSONDecodeError:
            pytest.fail(f"Could not decode JSON from {STRUCTURE_DATA_PATH}")
        except Exception as e:
            pytest.fail(f"Error reading structure data {STRUCTURE_DATA_PATH}: {e}")
    else:
        # If the structure file doesn't exist, we can't proceed reliably.
        pytest.fail(f"Structure data file not found at {STRUCTURE_DATA_PATH}")

    # 3. Combine expected source and allowed root patterns
    # allowed_files_patterns = {Path(p).as_posix() for p in KNOWN_GOOD_PATTERNS} # Removed
    all_expected_or_allowed = expected_source_files.union(allowed_root_patterns)

    # 4. Find unexpected files using is_allowed (which uses fnmatch)
    unexpected_files = set()
    for file_path in actual_files:
        # Use is_allowed directly which checks exact match and patterns
        if not is_allowed(file_path, all_expected_or_allowed):
            unexpected_files.add(file_path)

    # 5. Fail if unexpected files are found
    if unexpected_files:
        file_list = "\n - ".join(sorted(list(unexpected_files)))
        pytest.fail(
            "Found unexpected files tracked by git that are not defined in "
            f"{STRUCTURE_DATA_PATH.name} under 'source_files' or 'allowed_root_patterns':\n"
            f" - {file_list}\n"
            "Please investigate these files. Ensure they are included correctly "
            f"in {STRUCTURE_DATA_PATH.name} or remove them if they are cruft."
        )
    else:
        print("No unexpected tracked files found.")
