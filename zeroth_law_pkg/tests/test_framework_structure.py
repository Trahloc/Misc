# FILE: tests/test_framework_structure.py
"""
# PURPOSE: Verify adherence to the Zeroth Law Framework's structural guidelines,
#          specifically Section 4.14 Command-Based Module Organization (CDDS)
#          and the required test directory mirroring.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple

import pytest

# --- CONSTANTS ---
# ZLF Convention: test directories and files are prefixed with 'test_'
SRC_PKG_ROOT = Path(__file__).parent.parent / "src" / "zeroth_law"
TESTS_ROOT = Path(__file__).parent
COMMANDS_SRC_DIR = SRC_PKG_ROOT / "commands"
TESTS_COMMANDS_DIR = TESTS_ROOT / "test_commands"
COMMON_SRC_DIR = SRC_PKG_ROOT / "common"
TESTS_COMMON_DIR = TESTS_ROOT / "test_common"

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


# --- Mirroring Test --- #


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
    return TESTS_ROOT.joinpath(*test_parts)


SOURCE_FILES = _get_source_py_files()
SOURCE_FILE_IDS = [str(p.relative_to(SRC_PKG_ROOT.parent)) for p in SOURCE_FILES]


@pytest.mark.parametrize("src_file", SOURCE_FILES, ids=SOURCE_FILE_IDS)
def test_test_structure_mirrors_source(src_file: Path):
    """Verify that for every source .py file, a corresponding test_*.py file exists."""
    expected_test_file = _expected_test_path(src_file)
    assert expected_test_file.is_file(), f"Source file {src_file.relative_to(SRC_PKG_ROOT.parent)} \
        lacks corresponding test file at {expected_test_file.relative_to(TESTS_ROOT.parent)} \
        (Based on ZLF 'Prefix Everything' Convention)"
