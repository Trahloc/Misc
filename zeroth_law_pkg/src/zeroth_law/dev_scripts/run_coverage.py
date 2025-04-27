#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
import re

# Get the workspace root (assuming this script is in workspace/src/zeroth_law/dev_scripts)
# Need to go up 4 levels from __file__ (dev_scripts -> zeroth_law -> src -> workspace)
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]

# --- Configuration ---

# AI CODE ASSISTANT INSTRUCTION:
# DO NOT ADD ANY ENTRIES TO THE 'COVERAGE_EXCLUDE_PATTERNS' LIST BELOW.
# This list is exclusively managed by the human developers. If files or directories
# need to be excluded from coverage analysis, the human developer will add patterns here.
COVERAGE_EXCLUDE_PATTERNS = [
    # Example: "src/zeroth_law/dev_scripts/*",
    # Example: "tests/conftest.py",
]

# Erase command
coverage_erase_cmd = ["uv", "run", "coverage", "erase"]

# Build the coverage run command
# We use '-m pytest' to run pytest as a module via coverage
# Add -m "not coverage_check" to exclude the meta-test during collection
coverage_run_cmd = [
    "uv",
    "run",
    "coverage",
    "run",
    "-m",
    "pytest",
    "-m",
    "not coverage_check",
]
if COVERAGE_EXCLUDE_PATTERNS:
    # Add omit flag only if there are patterns
    coverage_run_cmd.extend(["--omit", ",".join(COVERAGE_EXCLUDE_PATTERNS)])

# Command to run only the threshold test - disable coverage for this run
threshold_test_cmd = [
    "uv",
    "run",
    "pytest",
    "--no-cov",
    "tests/test_tool_integration.py::test_project_coverage_threshold",
]

# Command to generate the text report to a file
coverage_report_cmd = ["uv", "run", "coverage", "report", "-m"]
REPORT_FILENAME = "coverage_report.txt"
COVERAGE_TOTAL_FILENAME = "coverage_total.txt"


def run_command(cmd, cwd, allowed_exit_codes=(0,), capture_stdout_for_cmd=None):
    """Runs a command, checks errors, optionally captures stdout for specific cmd."""
    print(f"\n--- Running command: {' '.join(cmd)} ---")
    capture = cmd == capture_stdout_for_cmd
    result = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True)

    # Print stdout unless it was captured for specific processing
    if not capture:
        print(result.stdout)
    # Always print stderr
    if result.stderr:
        print("--- STDERR ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        print("--------------", file=sys.stderr)
    if result.returncode not in allowed_exit_codes:
        print(
            f"\n*** Command failed with unexpected exit code {result.returncode} (allowed: {allowed_exit_codes})! ***",
            file=sys.stderr,
        )
        sys.exit(result.returncode)
    print(f"--- Command finished (exit code: {result.returncode}) ---")
    return result


def main():
    """Main execution function."""
    print(f"Workspace Root: {WORKSPACE_ROOT}")

    print("\nStep 1: Erasing previous coverage data...")
    run_command(coverage_erase_cmd, cwd=WORKSPACE_ROOT)

    print("\nStep 2: Running tests via coverage to collect data...")
    # Run pytest via coverage, allow failure, but don't capture output here
    run_command(
        coverage_run_cmd,
        cwd=WORKSPACE_ROOT,
        allowed_exit_codes=(0, 1),  # Allow tests to fail without stopping script
        # capture_stdout_for_cmd=coverage_run_cmd, # REMOVED - we capture report later
    )

    # Step 2.5: Generate and capture the coverage report summary
    print("\nStep 2.5: Generating coverage report summary...")
    coverage_report_summary_cmd = [
        "uv",
        "run",
        "coverage",
        "report",
    ]  # Basic report for total
    report_result = run_command(
        coverage_report_summary_cmd,
        cwd=WORKSPACE_ROOT,
        allowed_exit_codes=(0,),  # Report should succeed
        capture_stdout_for_cmd=coverage_report_summary_cmd,  # Capture this output
    )

    # Parse the captured stdout from report_result
    total_percentage = None
    if report_result.stdout:  # Check if stdout was captured
        print("--- Captured STDOUT from Step 2.5 (Coverage Report) ---")
        print(report_result.stdout)  # Print the captured output for verification
        print("-------------------------------------------------------")  # Removed invalid escapes
        # Look for the TOTAL line in the report output
        for line in report_result.stdout.splitlines():
            if line.startswith("TOTAL"):
                # Regex to find digits possibly followed by % at the end of the TOTAL line
                match = re.search(r"\b(\d+(?:\.\d+)?)[%\s]*$", line)  # Updated regex for potential float
                if match:
                    try:
                        total_percentage = float(match.group(1))
                        break
                    except ValueError:
                        pass  # Ignore if parsing fails

    if total_percentage is None:
        print(
            f"*** ERROR: Could not parse TOTAL percentage from coverage report output! ***",
            file=sys.stderr,
        )
        total_percentage = 0.0
        print(f"Proceeding with 0.0% for threshold check.", file=sys.stderr)

    # Write the parsed percentage to the total file
    total_output_path = WORKSPACE_ROOT / COVERAGE_TOTAL_FILENAME
    try:
        with open(total_output_path, "w", encoding="utf-8") as f:
            f.write(f"{total_percentage:.1f}")  # Write single number
        print(f"Successfully wrote parsed total ({total_percentage:.1f}%) to {total_output_path}")
    except IOError as e:
        print(
            f"*** ERROR: Failed to write parsed total to {total_output_path}: {e} ***",
            file=sys.stderr,
        )
        sys.exit(1)

    # Step 3: Run the threshold test which now reads the total file
    print(f"\nStep 3: Running coverage threshold test (reading {COVERAGE_TOTAL_FILENAME})...")
    run_command(threshold_test_cmd, cwd=WORKSPACE_ROOT, allowed_exit_codes=(0,))

    print(
        f"\nCoverage total ({total_percentage:.1f}%) saved to '{COVERAGE_TOTAL_FILENAME}' and threshold test executed successfully."
    )


if __name__ == "__main__":
    main()
