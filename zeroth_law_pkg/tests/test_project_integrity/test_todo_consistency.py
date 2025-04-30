"""Tests for the consistency and formatting of TODO.md."""

import pytest
import re
import argparse
import sys
from pathlib import Path
from typing import List, Tuple

# Assuming project root is discoverable. If not, adjust path finding.
# This assumes tests are run from the project root or this path is adjusted.
PROJECT_ROOT = Path(__file__).parent.parent.parent
TODO_FILE = PROJECT_ROOT / "TODO.md"


def _detect_violations() -> List[Tuple[int, str]]:
    """Scans TODO.md and returns a list of violations.

    Each violation is a tuple: (parent_line_num, violation_message)
    """
    if not TODO_FILE.exists():
        pytest.fail(f"TODO.md not found at {TODO_FILE}")

    violations_details = []
    parent_stack = []
    task_regex = re.compile(r"^(\s*)- \[([ x])\] (.*)")

    with open(TODO_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()  # Read all lines first for modification

    for line_num, line in enumerate(lines, 1):
        match = task_regex.match(line)
        if not match:
            if line.strip() and not line.startswith(" "):  # Basic check for section break
                parent_stack = []
            continue

        indent_str, status, description = match.groups()
        indent_level = len(indent_str)

        while parent_stack and indent_level <= parent_stack[-1][0]:
            parent_stack.pop()

        if parent_stack and status == " ":
            parent_indent, parent_status, parent_line_num, parent_line = parent_stack[-1]
            if parent_status == "x":
                message = (
                    f"L{parent_line_num}: Parent task marked complete '[x]' but has incomplete child at L{line_num}:\n"
                    f"  Parent: {parent_line.strip()}\n"
                    f"  Child:  {line.strip()}"
                )
                violations_details.append((parent_line_num, message))

        parent_stack.append((indent_level, status, line_num, line.strip()))  # Store stripped line

    return violations_details


def _fix_violations(lines: List[str], violation_lines: List[int]) -> List[str]:
    """Modifies the list of lines to fix violations by unchecking parents."""
    fixed_lines = lines[:]
    task_marker_regex = re.compile(r"^(\s*- \[)x(\])")
    lines_fixed_count = 0

    for line_num_one_indexed in violation_lines:
        line_index = line_num_one_indexed - 1
        if line_index < len(fixed_lines):
            original_line = fixed_lines[line_index]
            # Use regex sub for safe replacement
            modified_line, num_subs = task_marker_regex.subn(r"\1 \2", original_line)
            if num_subs > 0:
                fixed_lines[line_index] = modified_line
                lines_fixed_count += 1
                print(f"  - Fixed L{line_num_one_indexed}: Changed '[x]' to '[ ]'")
            else:
                print(f"  - WARNING: Expected to fix L{line_num_one_indexed} but marker '[x]' not found as expected.")
        else:
            print(f"  - WARNING: Line number {line_num_one_indexed} out of bounds during fix attempt.")

    print(f"Attempted to fix {len(violation_lines)} violations, successfully fixed {lines_fixed_count} lines.")
    return fixed_lines


def test_parent_tasks_marked_incomplete_if_children_incomplete(fix_mode: bool = False):
    """Verifies (and optionally fixes) that parent tasks in TODO.md are marked [ ] if any children are [ ]."""

    violations = _detect_violations()
    violation_messages = [msg for _, msg in violations]
    parent_lines_to_fix = sorted(list(set(line_num for line_num, _ in violations)))  # Unique lines

    if not violations:
        print("\nTODO.md consistency check passed.")
        return  # Pass if no violations

    error_message = "Found parent tasks marked [x] with incomplete children:\n\n" + "\n\n".join(violation_messages)

    if fix_mode:
        print("\nAttempting to fix TODO.md inconsistencies...")
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            original_lines = f.readlines()

        fixed_lines = _fix_violations(original_lines, parent_lines_to_fix)

        # Write back the fixed content
        try:
            with open(TODO_FILE, "w", encoding="utf-8") as f:
                f.writelines(fixed_lines)
            print(f"Successfully wrote fixes back to {TODO_FILE}")
        except IOError as e:
            print(f"ERROR: Failed to write fixes to {TODO_FILE}: {e}")
            pytest.fail(f"IOError writing fixes: {e}")

        # Fail the test after fixing to indicate changes were made
        fail_msg = "TODO.md was modified to fix inconsistencies. Please review and commit.\n\n" + error_message
        pytest.fail(fail_msg, pytrace=False)
    else:
        # Fail the test if not in fix mode and violations exist
        assert not violations, error_message


# --- Allow running as a script with --fix --- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check and optionally fix TODO.md parent task completion consistency.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically uncheck parent tasks marked [x] that have incomplete [ ] children.",
    )
    args = parser.parse_args()

    print(f"Running TODO consistency check (Fix Mode: {args.fix})...")
    try:
        # We run the test function directly. It will print info and use pytest.fail()
        # which raises an exception if violations are found (and not fixed/reported).
        test_parent_tasks_marked_incomplete_if_children_incomplete(fix_mode=args.fix)
        # If it reaches here, the test passed (no violations found initially)
        sys.exit(0)
    except Exception as e:
        # Catch pytest.fail or other exceptions
        print(f"\nCheck failed or error occurred: {e}", file=sys.stderr)
        # If it was pytest.fail due to needing fixes, exit code should indicate failure
        # A simple non-zero exit code works here.
        sys.exit(1)
