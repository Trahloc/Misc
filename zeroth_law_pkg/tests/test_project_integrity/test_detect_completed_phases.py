"""Tests for detecting completed phases in TODO.md."""

import pytest
import re
from pathlib import Path

# Assuming project root is discoverable. If not, adjust path finding.
PROJECT_ROOT = Path(__file__).parent.parent.parent
TODO_FILE = PROJECT_ROOT / "TODO.md"


def test_no_fully_completed_phases_in_todo():
    """Verifies that no Phase section in TODO.md has all its tasks marked [x]."""
    assert TODO_FILE.exists(), f"TODO.md not found at {TODO_FILE}"

    completed_phases = []
    current_phase_header = None
    tasks_in_current_phase = 0
    incomplete_tasks_in_current_phase = 0

    # Regex to find Phase headers
    phase_header_regex = re.compile(r"^## \*\*(Phase [A-Z]: .+)\*\*$")
    # Regex to find task lines
    task_regex = re.compile(r"^\s*- \[([ x])\]")

    with open(TODO_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            header_match = phase_header_regex.match(line.strip())
            task_match = task_regex.match(line)

            if header_match:
                # End of previous phase? Check its status.
                if (
                    current_phase_header is not None
                    and tasks_in_current_phase > 0
                    and incomplete_tasks_in_current_phase == 0
                ):
                    completed_phases.append(current_phase_header)

                # Start of a new phase
                current_phase_header = header_match.group(1)
                tasks_in_current_phase = 0
                incomplete_tasks_in_current_phase = 0
                # print(f"DEBUG: Found Phase: {current_phase_header}") # Debug

            elif task_match and current_phase_header is not None:
                # Found a task within the current phase
                status = task_match.group(1)
                tasks_in_current_phase += 1
                if status == " ":
                    incomplete_tasks_in_current_phase += 1
                # print(f"DEBUG: Task found - Status: {status}, Total: {tasks_in_current_phase}, Incomplete: {incomplete_tasks_in_current_phase}") # Debug

        # Check the status of the very last phase in the file
        if current_phase_header is not None and tasks_in_current_phase > 0 and incomplete_tasks_in_current_phase == 0:
            completed_phases.append(current_phase_header)

    assert not completed_phases, (
        f"Found {len(completed_phases)} phase(s) in TODO.md that appear complete (all tasks marked [x]). "
        f"Please review and archive them to 'docs/todos/completed-<timestamp>.md':\n - "
        + "\n - ".join(completed_phases)
    )
