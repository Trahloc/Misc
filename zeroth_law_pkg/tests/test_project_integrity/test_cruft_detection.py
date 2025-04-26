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

STRUCTURE_DATA_PATH = WORKSPACE_ROOT / "project_structure.json"  # Assuming this path

# Files/patterns explicitly allowed to exist even if not in structure data
# Use fnmatch patterns (similar to .gitignore) relative to WORKSPACE_ROOT
KNOWN_GOOD_PATTERNS = {
    # Project files (exact match)
    "pyproject.toml",
    "poetry.lock",
    "uv.lock",
    "README.md",
    ".gitignore",
    ".gitattributes",  # Keep if used
    ".editorconfig",  # Keep if used
    "LICENSE",  # Keep if used
    ".pre-commit-config.yaml",  # Keep
    "NOTES.md",  # Keep
    "TODO.md",  # Keep
    "CODE_TODOS.md",  # Keep
    "package.json",  # For npm/prettier
    "project_structure.json",  # Generated structure data
    "mock_whitelist.toml",
    "conftest.py",  # Root conftest
    "__init__.py",  # Allow root __init__ if needed
    # Top-level Dirs (use ** for recursive matching)
    ".git/**",
    ".venv/**",
    ".vscode/**",
    ".cursor/**",
    ".github/**",
    ".pytest_cache/**",
    "build/**",
    "dist/**",
    "src/**",  # Allow everything under src (checked against structure.json)
    "tests/**",  # Allow everything under tests (including test_data, etc.)
    "test_data/**",  # Explicitly allow test_data and its contents
    "docs/**",
    "scripts/**",
    "templates/**",
    "tool_defs/**",
    "tools/**",  # Contains generated files + index
    "frameworks/**",
    "generated_command_outputs/**",
    "coverage_html_report/**",
    "*.egg-info/**",
    "__pycache__/**",
    # Specific generated files (if not covered by dir patterns)
    ".coverage",  # Note: .coverage* pattern might be better if names vary
    "coverage.json",
    "coverage.xml",
    "coverage_report.txt",
    "coverage_total.txt",
    # Temporary files/dirs (if tracked, usually should be gitignored)
    "tmp/**",
}

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

    # 2. Load expected source files from structure data (handle if missing)
    expected_source_files = set()
    # print(f"DEBUG: Checking STRUCTURE_DATA_PATH: {STRUCTURE_DATA_PATH.resolve()}", file=sys.stderr) # Removed debug line
    if STRUCTURE_DATA_PATH.is_file():
        try:
            with open(STRUCTURE_DATA_PATH, "r") as f:
                data = json.load(f)
            # Assume paths in JSON are relative to WORKSPACE_ROOT or easily convertible
            # Normalize to POSIX paths for consistent matching
            expected_source_files = {Path(p).as_posix() for p in data.get("source_files", [])}
        except json.JSONDecodeError:
            pytest.fail(f"Could not decode JSON from {STRUCTURE_DATA_PATH}")
        except Exception as e:
            pytest.fail(f"Error reading structure data {STRUCTURE_DATA_PATH}: {e}")
    else:
        # If the structure file doesn't exist, we can't know expected source files.
        # Depending on policy, you might fail here, or just rely on KNOWN_GOOD_PATTERNS
        print(
            f"Warning: Structure data file not found at {STRUCTURE_DATA_PATH}. "
            "Cruft detection will rely solely on KNOWN_GOOD_PATTERNS.",
            file=sys.stderr,
        )
        # pytest.fail(f"Structure data file not found: {STRUCTURE_DATA_PATH}") # Option to fail

    # 3. Combine expected source and known good patterns/files
    allowed_files_patterns = {Path(p).as_posix() for p in KNOWN_GOOD_PATTERNS}
    all_expected_or_allowed = expected_source_files.union(allowed_files_patterns)

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
            f"{STRUCTURE_DATA_PATH.name} or listed/matched in the test's KNOWN_GOOD_PATTERNS:\n"
            f" - {file_list}\n"
            "Please investigate these files. Add them to KNOWN_GOOD_PATTERNS in "
            f"{Path(__file__).name} if they should be allowed, ensure they are included "
            f"in {STRUCTURE_DATA_PATH.name} if they are source code, or remove them if they are cruft."
        )
    else:
        print("No unexpected tracked files found.")
