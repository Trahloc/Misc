# FILE: tests/test_project_integrity/test_framework_structure.py
"""
# PURPOSE: Verify adherence to the Zeroth Law Framework's structural guidelines,
#          specifically Section 4.14 Command-Based Module Organization (CDDS)
#          and the required test directory mirroring within tests/test_zeroth_law/.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple
import toml # Need toml to read pyproject.toml
import fnmatch # For pattern matching in root check

import pytest

# --- CONSTANTS ---
# ZLF Convention: test directories and files are prefixed with 'test_'
SRC_PKG_ROOT = Path(__file__).parent.parent.parent / "src" / "zeroth_law"
# TESTS_ROOT = Path(__file__).parent.parent # Old Root
TESTS_ROOT = Path(__file__).parent.parent # Still the tests/ directory itself
TESTS_MIRROR_ROOT = TESTS_ROOT / "test_zeroth_law" # FINAL: Prefixed container
WORKSPACE_ROOT = TESTS_ROOT.parent # Project root directory

COMMANDS_SRC_DIR = SRC_PKG_ROOT / "commands"
# TESTS_COMMANDS_DIR = TESTS_ROOT / "test_commands" # Old
TESTS_COMMANDS_DIR = TESTS_MIRROR_ROOT / "test_commands" # NEW: Under tests/test_zeroth_law/

COMMON_SRC_DIR = SRC_PKG_ROOT / "common"
# TESTS_COMMON_DIR = TESTS_ROOT / "test_common" # Old
TESTS_COMMON_DIR = TESTS_MIRROR_ROOT / "test_common" # NEW: Under tests/test_zeroth_law/

COMMON_DIR_NAME = "common"  # Used to exclude common dir from command processing


def _get_command_dirs() -> List[Path]:
    """Finds all command source subdirectories."""
    if not COMMANDS_SRC_DIR.is_dir():
        return []
    return [
        item
        for item in COMMANDS_SRC_DIR.iterdir()
        if item.is_dir() and not item.name.startswith("_") and item.name != COMMON_DIR_NAME
    ]


COMMAND_SRC_DIRS = _get_command_dirs()
COMMAND_NAMES = [d.name for d in COMMAND_SRC_DIRS]


# --- Structural Tests (Existing) ---

@pytest.mark.parametrize("command_src_dir", COMMAND_SRC_DIRS, ids=COMMAND_NAMES)
def test_command_directory_structure(command_src_dir: Path):
    """Verify standard file/directory structure for each command (ZLF 4.14)."""
    command_name = command_src_dir.name
    impl_file = command_src_dir / f"{command_name}.py"
    # ZLF Convention: Prefix test directories and files
    test_dir = TESTS_COMMANDS_DIR / f"test_{command_name}"
    test_file = test_dir / f"test_{command_name}.py"

    assert impl_file.is_file(), f"Implementation file missing: {impl_file}"
    assert test_dir.is_dir(), f"Test directory missing: {test_dir}"
    assert test_file.is_file(), f"Main test file missing: {test_file}"


def _find_cross_imports(command_src_dir: Path) -> List[Tuple[str, int, str]]:
    """
    Uses AST to find imports referencing other command modules within a command's directory.

    Returns:
        List of tuples: (filename, lineno, imported_module_name)
    """
    command_name = command_src_dir.name
    violations = []
    # Ensure we compare against the python module path, not filesystem path
    other_command_modules = {f"zeroth_law.commands.{name}" for name in COMMAND_NAMES if name != command_name}

    for py_file in command_src_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                module_str = None
                if isinstance(node, ast.ImportFrom):
                    module_str = node.module
                elif isinstance(node, ast.Import):
                    # Only check direct command module imports, not submodules like .utils
                    for alias in node.names:
                        if alias.name in other_command_modules:
                            module_str = alias.name  # Treat direct import as module string
                            break  # Found violation for this import node

                if module_str and module_str.startswith(tuple(other_command_modules)):
                    # Check if it starts with any *other* command module path
                    # e.g., importing zeroth_law.commands.analyze from zeroth_law.commands.init
                    violations.append((str(py_file.relative_to(SRC_PKG_ROOT.parent)), node.lineno, module_str))

        except Exception as e:
            # Log or handle parsing errors if necessary
            print(f"Warning: Could not parse {py_file}: {e}", file=sys.stderr)
    return violations


@pytest.mark.parametrize("command_src_dir", COMMAND_SRC_DIRS, ids=COMMAND_NAMES)
def test_no_cross_command_imports(command_src_dir: Path):
    """Verify that command modules do not import from other command modules (ZLF 4.14)."""
    cross_imports = _find_cross_imports(command_src_dir)
    assert not cross_imports, (
        f"Found cross-command imports in '{command_src_dir.name}':\n"
        + "\n".join([f"  - {fname}:{lineno} imports {mod}" for fname, lineno, mod in cross_imports])
        + f"\nShared utilities should be in 'src/zeroth_law/{COMMON_DIR_NAME}/'."
    )


def _module_defines_all(module_file: Path) -> bool:
    """Check if a module file defines the __all__ variable."""
    if not module_file.is_file():
        return False  # Cannot define __all__ if file doesn't exist
    try:
        tree = ast.parse(module_file.read_text())
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        return True
    except Exception as e:
        print(f"Warning: Could not parse {module_file} for __all__: {e}", file=sys.stderr)
    return False


@pytest.mark.parametrize("command_src_dir", COMMAND_SRC_DIRS, ids=COMMAND_NAMES)
def test_command_module_defines_all(command_src_dir: Path):
    """Verify that the main command implementation file defines __all__ (ZLF 4.14)."""
    command_name = command_src_dir.name
    impl_file = command_src_dir / f"{command_name}.py"
    assert _module_defines_all(impl_file), f"Main implementation file {impl_file} must define '__all__'."


# --- Mirroring Tests (Existing + New Orphan Check) --- #

def _get_source_py_files() -> Set[Path]:
    """Gets all non-__init__.py Python files within the src/zeroth_law package."""
    return {p for p in SRC_PKG_ROOT.rglob("*.py") if p.name != "__init__.py"}


def _expected_test_path(src_file: Path) -> Path:
    """Calculates the expected corresponding test file path based on ZLF convention."""
    relative_path = src_file.relative_to(SRC_PKG_ROOT)
    parts = list(relative_path.parts)
    # Prefix directory parts
    test_parts = [f"test_{p}" for p in parts[:-1]]
    # Prefix filename part
    filename = parts[-1]
    test_filename = f"test_{filename}"
    test_parts.append(test_filename)
    # return TESTS_ROOT.joinpath(*test_parts) # Old base
    return TESTS_MIRROR_ROOT.joinpath(*test_parts) # FINAL base


SOURCE_FILES = _get_source_py_files()
SOURCE_FILE_IDS = [str(p.relative_to(SRC_PKG_ROOT.parent)) for p in SOURCE_FILES]

@pytest.mark.parametrize("src_file", SOURCE_FILES, ids=SOURCE_FILE_IDS)
def test_test_structure_mirrors_source(src_file: Path):
    """Verify that for every source .py file, a corresponding test_*.py file exists inside tests/test_zeroth_law/."""
    expected_test_file = _expected_test_path(src_file)
    assert expected_test_file.is_file(), (
        f"Source file {src_file.relative_to(SRC_PKG_ROOT.parent)} \
        lacks corresponding test file at {expected_test_file.relative_to(TESTS_ROOT)} \
        (Based on ZLF 'Prefix Everything' Convention inside tests/test_zeroth_law/)"
    )

def _get_test_py_files() -> Set[Path]:
    """Gets all non-__init__.py test_*.py files within the tests/test_zeroth_law/ directory."""
    # Exclude __init__.py and conftest.py
    return {
        p for p in TESTS_MIRROR_ROOT.rglob("test_*.py")
        if p.name not in ["__init__.py", "conftest.py"]
    }

def _expected_source_path(test_file: Path) -> Path:
    """Calculates the expected corresponding source file path."""
    relative_path = test_file.relative_to(TESTS_MIRROR_ROOT)
    # Remove 'test_' prefix from all parts
    src_parts = [p.removeprefix("test_") for p in relative_path.parts]
    return SRC_PKG_ROOT.joinpath(*src_parts)

TEST_FILES = _get_test_py_files()
TEST_FILE_IDS = [str(p.relative_to(TESTS_ROOT)) for p in TEST_FILES]

@pytest.mark.parametrize("test_file", TEST_FILES, ids=TEST_FILE_IDS)
def test_no_orphaned_test_files(test_file: Path):
    """Verify that every test file mirrors an existing source file."""
    expected_source_file = _expected_source_path(test_file)
    assert expected_source_file.is_file(), (
        f"Test file {test_file.relative_to(TESTS_ROOT)} exists but corresponding "
        f"source file {expected_source_file.relative_to(WORKSPACE_ROOT / 'src')} "
        f"does not."
    )

# --- Naming Convention Tests (Existing + New) ---

def test_no_test_prefix_in_source_files():
    """Verify that no source files within src/zeroth_law/ start with 'test_'."""
    violations = [
        p.relative_to(SRC_PKG_ROOT.parent)
        for p in SRC_PKG_ROOT.rglob("*.py")
        if p.name.startswith("test_")
    ]
    assert not violations, (
        "Found source files prefixed with 'test_' which is forbidden:\n - "
        + "\n - ".join(map(str, violations))
    )

def test_tests_root_naming_convention():
    """Verify immediate children of tests/ are standard or start with test_."""
    allowed_non_prefixed = {"__init__.py", "conftest.py"}
    violations = []
    if TESTS_ROOT.is_dir():
        for item in TESTS_ROOT.iterdir():
            if item.name not in allowed_non_prefixed and not item.name.startswith("test_"):
                 violations.append(item.name)
    assert not violations, (
        f"Found files/directories in '{TESTS_ROOT.relative_to(WORKSPACE_ROOT)}' "
        f"that are not standard ({', '.join(allowed_non_prefixed)}) and do not start with 'test_': "
        f"{', '.join(violations)}"
    )

# --- Project Root Structure Tests ---

def test_project_root_contains_only_whitelisted_items():
    """Verify project root directory only contains items whitelisted in pyproject.toml."""
    try:
        pyproject_path = WORKSPACE_ROOT / "pyproject.toml"
        config = toml.load(pyproject_path)
        allowed_items_config = config.get("tool", {}).get("zeroth-law", {}).get("allowed-project-roots", {}).get("items", [])
        if not allowed_items_config:
             pytest.fail("Could not find [tool.zeroth-law.allowed-project-roots].items in pyproject.toml")

        allowed_patterns = set(allowed_items_config) # Use patterns directly

    except FileNotFoundError:
        pytest.fail(f"pyproject.toml not found at {WORKSPACE_ROOT}")
    except Exception as e:
        pytest.fail(f"Error reading allowed root items from pyproject.toml: {e}")

    actual_items = {item.name for item in WORKSPACE_ROOT.iterdir()}
    violations = set()

    for item_name in actual_items:
        is_allowed = False
        for pattern in allowed_patterns:
            if fnmatch.fnmatch(item_name, pattern):
                is_allowed = True
                break
        if not is_allowed:
            violations.add(item_name)

    assert not violations, (
        "Found unexpected files/directories at the project root "
        f"({WORKSPACE_ROOT}) that are not listed/matched in "
        "[tool.zeroth-law.allowed-project-roots].items in pyproject.toml:\n - "
        + "\n - ".join(sorted(list(violations)))
    )

# Note: test_no_test_prefix_outside_tests_dir was deemed too complex/brittle
# to implement reliably by simply checking the root dir, as subdirs like src/ could
# potentially (though wrongly) contain 'test_' prefixed files. Relying on the
# specific checks within tests/ and src/ (test_no_test_prefix_in_source_files)
# is likely more effective.
