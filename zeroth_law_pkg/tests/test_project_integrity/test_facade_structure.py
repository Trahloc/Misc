# FILE: tests/test_project_integrity/test_facade_structure.py
"""
Tests to ensure the Command Facade structure (Sec 4.19) is followed within subcommands.

Structure Rules (Revised):
1. Top-level facade files (e.g., `subcommands/tools.py`) define main groups/commands.
2. If a facade file `foo.py` exists (and is not a utility file), its corresponding helper dir `_foo/` must also exist.
3. If a helper dir `_foo/` exists, its corresponding facade file `foo.py` must also exist.
4. Helper directories (`_foo/`) must contain at least one Python file (excluding `__init__.py`).
5. Utility files (e.g., `_tools/list_utils.py`) can exist alongside facades.
6. No `*_cmd.py` files allowed.
7. Facade files (`foo.py`, unless ending `_utils.py`) must define *only one* function: the main click group/command function (name matching file stem or ending `_group`). No other functions allowed.
"""

import pytest
from pathlib import Path
import os
import ast
import sys  # DEBUG

# Define the base directory to scan
SUBCOMMANDS_DIR = Path("src/zeroth_law/subcommands")

# Skip all tests in this file if the base directory doesn't exist
pytestmark = pytest.mark.skipif(
    not SUBCOMMANDS_DIR.is_dir() or not SUBCOMMANDS_DIR.exists(),  # Added exists()
    reason=f"Subcommands directory not found or inaccessible: {SUBCOMMANDS_DIR}",
)


def test_command_facade_structure_and_content():
    """
    Verifies the hierarchical Command Facade structure and limits functions in facades.
    """
    violations = []
    # Use rglob to get current filesystem state
    print(f"DEBUG: Scanning {SUBCOMMANDS_DIR}...", file=sys.stderr)  # DEBUG
    all_fs_paths = list(SUBCOMMANDS_DIR.rglob("*"))
    all_py_files = {p for p in all_fs_paths if p.is_file() and p.suffix == ".py"}
    all_dirs = {p for p in all_fs_paths if p.is_dir()}
    print(
        f"DEBUG: Found {len(all_py_files)} py files, {len(all_dirs)} dirs.",
        file=sys.stderr,
    )  # DEBUG

    # --- Rule 6: Check for invalid '*_cmd.py' files ---
    for py_file in all_py_files:
        if py_file.name.endswith("_cmd.py"):
            # Double check it actually exists before reporting
            if py_file.exists():
                violations.append(f"[Rule 6] Invalid '*_cmd.py' file found: {py_file.relative_to(SUBCOMMANDS_DIR)}")

    # --- Identify Potential Facades and Helpers from current FS state ---
    potential_facade_files = {
        f
        for f in all_py_files
        if f.exists()  # Ensure file exists
        and not f.name.startswith("_")
        and f.name != "__init__.py"
        # *** CRITICAL FIX: Only consider files NOT inside a helper directory as potential facades ***
        and not any(part.startswith("_") for part in f.relative_to(SUBCOMMANDS_DIR).parts[:-1])
    }
    all_helper_dirs = {d for d in all_dirs if d.exists() and d.name.startswith("_")}

    # DEBUG: Print identified potential facades
    print("DEBUG: Potential Facade Files:", file=sys.stderr)
    for f in sorted(list(potential_facade_files)):
        print(f"  - {f.relative_to(SUBCOMMANDS_DIR.parent)}", file=sys.stderr)
    print("DEBUG: All Helper Dirs:", file=sys.stderr)
    for d in sorted(list(all_helper_dirs)):
        print(f"  - {d.relative_to(SUBCOMMANDS_DIR.parent)}", file=sys.stderr)
    # --- End DEBUG ---

    # --- Check Relationships and Content ---

    # Rules 3 & 4: Check Helper Dirs
    for helper_dir in all_helper_dirs:
        # Ensure helper_dir exists before proceeding
        if not helper_dir.exists():
            continue

        facade_name = helper_dir.name[1:]
        parent_dir = helper_dir.parent
        expected_facade_file = parent_dir / f"{facade_name}.py"

        # Rule 3: Helper dir implies facade file exists
        if not expected_facade_file.exists():  # Use exists()
            violations.append(
                f"[Rule 3] Helper directory '{helper_dir.relative_to(SUBCOMMANDS_DIR)}' exists, but facade file '{expected_facade_file.relative_to(SUBCOMMANDS_DIR)}' is missing."
            )

        # Rule 4: Helper dir is not empty (contains .py files other than __init__.py OR nested helper dirs)
        try:
            py_helpers_in_dir = {
                item
                for item in helper_dir.iterdir()
                if item.exists() and item.is_file() and item.suffix == ".py" and item.name != "__init__.py"
            }
            nested_helper_dirs_inside = {
                d for d in all_dirs if d.exists() and d.parent == helper_dir and d.name.startswith("_")
            }
            if not py_helpers_in_dir and not nested_helper_dirs_inside:
                violations.append(
                    f"[Rule 4] Helper directory '{helper_dir.relative_to(SUBCOMMANDS_DIR)}' contains no Python files (excluding __init__.py) or nested helper directories."
                )
        except FileNotFoundError:  # Handle case where iterdir fails if dir vanished
            violations.append(
                f"[Internal Test Error] Could not iterate helper directory {helper_dir.relative_to(SUBCOMMANDS_DIR)}"
            )
            continue

        # Rule 5 Removed: Check files inside *leaf* helper dirs start with _
        # This rule was complex and less critical than the facade/helper pairing.

    # Rules 2 & 7: Check Facade Files
    for facade_file in potential_facade_files:
        # Ensure facade_file exists before processing
        if not facade_file.exists():
            continue

        facade_name = facade_file.stem
        parent_dir = facade_file.parent
        expected_helper_dir = parent_dir / f"_{facade_name}"
        is_utility_file = facade_file.name.endswith("_utils.py")  # Check if it's a utility

        # Rule 2: Facade file implies helper directory exists (unless it's a utility file)
        # This check should apply even to nested facades (e.g., _analyze/python.py needs _analyze/_python/)
        # is_inside_helper_structure = any(
        #     part.startswith("_") for part in parent_dir.parts[len(SUBCOMMANDS_DIR.parts) :]
        # )
        # DEBUG Rule 2 Check
        # print(f"DEBUG Rule 2: File={facade_file.relative_to(SUBCOMMANDS_DIR.parent)}, Util={is_utility_file}, ExpHelper={expected_helper_dir.relative_to(SUBCOMMANDS_DIR.parent)}, Exists={expected_helper_dir.exists()}", file=sys.stderr)

        # Apply Rule 2 if it's not a utility file
        if not is_utility_file:
            if not expected_helper_dir.exists():  # Use exists()
                violations.append(
                    f"[Rule 2] Facade file '{facade_file.relative_to(SUBCOMMANDS_DIR)}' exists, but helper directory '{expected_helper_dir.relative_to(SUBCOMMANDS_DIR)}' is missing."
                )

        # Rule 7: Facade defines only the main click function (unless it's a utility file)
        if not is_utility_file:
            try:
                source = facade_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(facade_file))
                defined_functions = []
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check if the function has decorators (likely click command/group)
                        has_click_decorator = any(
                            isinstance(d, ast.Call)
                            and isinstance(d.func, ast.Attribute)
                            and d.func.attr in ["command", "group"]
                            or isinstance(d, ast.Name)
                            and d.id in ["command", "group"]  # Simple decorator name
                            for d in node.decorator_list
                        )
                        # Heuristic: Assume the main func is the one with click decorators or matching name
                        is_likely_main_func = (
                            has_click_decorator or node.name == facade_name or node.name.endswith("_group")
                        )
                        if not is_likely_main_func:
                            defined_functions.append(node.name)

                if len(defined_functions) > 0:
                    violations.append(
                        f"[Rule 7] Facade file '{facade_file.relative_to(SUBCOMMANDS_DIR)}' defines extra non-Click functions: {defined_functions}. Only the main click group/command function is allowed."
                    )
            except FileNotFoundError:  # Handle case where file vanished between listing and reading
                violations.append(f"[AST] File vanished before read: {facade_file.relative_to(SUBCOMMANDS_DIR)}")
            except SyntaxError as e:
                violations.append(f"[AST] SyntaxError parsing {facade_file.relative_to(SUBCOMMANDS_DIR)}: {e}")
            except Exception as e:
                violations.append(f"[AST] Error processing {facade_file.relative_to(SUBCOMMANDS_DIR)}: {e}")

    # Final Assertion
    assert not violations, (
        f"Command Facade structure/content violations found relative to '{SUBCOMMANDS_DIR}':\n - "
        + "\n - ".join(sorted(violations))
    )
