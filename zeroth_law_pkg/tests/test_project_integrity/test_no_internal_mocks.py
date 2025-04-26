# FILE: tests/test_framework_compliance/test_no_internal_mocks.py
"""
Tests that test files do not mock internal project modules,
enforcing the ZLF principle of testing against real implementations.
"""

import ast
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Set
import toml  # Import toml

import pytest

# --- Constants ---
SRC_PREFIX = "src.zeroth_law"  # The prefix indicating internal modules
TESTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = TESTS_DIR.parent  # Assumes tests/ is one level down from root
MOCK_WHITELIST_PATH = TESTS_DIR / "test_data" / "mock_whitelist.toml"

log = logging.getLogger(__name__)

# --- Load and Process Whitelist --- #


def _load_and_process_whitelist(whitelist_path: Path) -> Dict[str, Set[str]]:
    """Loads the TOML whitelist and transforms it into a lookup dictionary."""
    allowed_mocks_by_rel_file: Dict[str, Set[str]] = {}
    if not whitelist_path.is_file():
        log.warning(f"Mock whitelist file not found: {whitelist_path}. No internal mocks will be allowed.")
        return allowed_mocks_by_rel_file

    try:
        data = toml.load(whitelist_path)
        files_config = data.get("files", {})
        if not isinstance(files_config, dict):
            log.error(f"Invalid structure in {whitelist_path}: 'files' key is not a table/dictionary.")
            return {}

        for rel_path, config in files_config.items():
            if not isinstance(config, dict):
                log.warning(f"Skipping invalid entry for file '{rel_path}' in {whitelist_path}: value is not a table.")
                continue

            targets = config.get("allowed_targets", [])
            if not isinstance(targets, list):
                log.warning(
                    f"Skipping invalid entry for file '{rel_path}' in {whitelist_path}: 'allowed_targets' is not a list."
                )
                continue

            # Normalize path separators for consistency (e.g., Windows vs Linux)
            normalized_rel_path = str(Path(rel_path)).replace("\\", "/")
            allowed_mocks_by_rel_file[normalized_rel_path] = set(targets)
            log.debug(f"Loaded {len(targets)} allowed mocks for {normalized_rel_path}")

    except toml.TomlDecodeError as e:
        log.error(f"Error parsing mock whitelist file {whitelist_path}: {e}")
        # Return empty dict on parse error to prevent allowing mocks unintentionally
        return {}
    except Exception as e:
        log.error(f"Unexpected error loading mock whitelist {whitelist_path}: {e}", exc_info=True)
        return {}

    return allowed_mocks_by_rel_file


# Load the whitelist at module scope
ALLOWED_MOCKS_BY_FILE = _load_and_process_whitelist(MOCK_WHITELIST_PATH)


# --- Helper Functions ---


def find_test_files() -> List[Path]:
    """Finds all test_*.py files within the tests directory."""
    # Exclude self to avoid recursion
    all_files = list(TESTS_DIR.rglob("test_*.py"))
    self_path = Path(__file__).resolve()
    return [p for p in all_files if p.resolve() != self_path]


class MockFinder(ast.NodeVisitor):
    """
    AST Visitor to find forbidden mock patch targets.
    """

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.forbidden_mocks: List[Tuple[int, str]] = []
        # Pre-calculate relative path for lookups
        try:
            self.relative_file_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            # Handle cases where the file might not be under PROJECT_ROOT (shouldn't happen ideally)
            log.warning(f"Could not determine relative path for {file_path} against {PROJECT_ROOT}")
            self.relative_file_path = None

    def _is_forbidden_target(self, target_str: str) -> bool:
        """Checks if a mock target string refers to an internal module
        and is not specifically allowed for the current file."""
        is_internal = target_str.startswith(SRC_PREFIX)
        if not is_internal:
            return False  # Not internal, so not forbidden by this checker

        # Check against the contextual whitelist
        is_allowed_for_this_file = False
        if self.relative_file_path:
            allowed_targets_for_file = ALLOWED_MOCKS_BY_FILE.get(self.relative_file_path, set())
            if target_str in allowed_targets_for_file:
                is_allowed_for_this_file = True

        # Forbidden if internal AND NOT allowed for this specific file
        return not is_allowed_for_this_file

    def _check_patch_call(self, node: ast.Call):
        """Checks if an ast.Call node is a patch call with a forbidden target."""
        # Check if the function being called is 'patch' or 'mock.patch' etc.
        is_patch_call = False
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            # We could trace node.func.value to see if it comes from unittest.mock, but keep it simple

        if func_name == "patch":
            is_patch_call = True

        if is_patch_call and node.args:
            first_arg = node.args[0]
            target_str = None
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                target_str = first_arg.value

            if target_str and self._is_forbidden_target(target_str):
                self.forbidden_mocks.append((node.lineno, target_str))
                # Don't check keywords if positional target is bad
                # NOTE: We return here to avoid potentially double-counting if target is also in keywords,
                # BUT we might miss a *different* forbidden target in keywords.
                # Let's check keywords regardless for completeness.
                # return

        # Also check keyword arguments
        if is_patch_call:
            for kw in node.keywords:
                if kw.arg == "target" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    target_str = kw.value.value
                    if self._is_forbidden_target(target_str):
                        # Avoid adding duplicate if already found in args
                        if not any(m[1] == target_str for m in self.forbidden_mocks):
                            self.forbidden_mocks.append((node.lineno, target_str))
                    # We only care about the 'target=' keyword for this check
                    # break # Don't break, check all keywords? No, target is specific.

    def visit_Call(self, node: ast.Call):
        """Visit function calls."""
        self._check_patch_call(node)
        self.generic_visit(node)  # Continue traversing

    def visit_With(self, node: ast.With):
        """Visit 'with' statements for 'with patch(...)' context managers."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                self._check_patch_call(item.context_expr)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions for @patch decorators."""
        for decorator in node.decorator_list:
            # Decorators can be complex (e.g., @patch.object), focus on direct @patch("...")
            if isinstance(decorator, ast.Call):
                self._check_patch_call(decorator)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definitions for @patch decorators."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                self._check_patch_call(decorator)
        self.generic_visit(node)


# --- Test Function ---

# Ensure find_test_files() excludes the current file before parameterization
TEST_FILES = find_test_files()


@pytest.mark.parametrize("test_file_path", TEST_FILES, ids=lambda p: str(p.relative_to(TESTS_DIR)) if p else "None")
# @pytest.mark.skip(reason="Temporarily skipping due to justified internal mocks needing allow-listing.")
def test_no_forbidden_internal_mocks(test_file_path: Path):
    """
    Verify that a test file does not contain mocks patching internal modules
    unless explicitly allowed for that specific file in mock_whitelist.toml.
    """
    if not test_file_path:
        pytest.skip("No test files found for mock checking.")
        return

    log.debug(f"Checking file: {test_file_path}")
    try:
        content = test_file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(test_file_path))
    except SyntaxError as e:
        pytest.fail(f"Syntax error parsing AST for {test_file_path}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to read or parse AST for {test_file_path}: {e}")

    finder = MockFinder(test_file_path)
    try:
        finder.visit(tree)
    except Exception as e:
        pytest.fail(f"Error visiting AST nodes in {test_file_path}: {e}")

    if finder.forbidden_mocks:
        test_file_rel = finder.relative_file_path or str(test_file_path)  # Use calculated relative path
        found_mocks_str = "\n".join(
            f"  - Line {lineno}: patch('{target}')" for lineno, target in finder.forbidden_mocks
        )
        pytest.fail(
            # Use the formatted string directly as the short failure message for clarity in pytest output
            f"Forbidden internal mock(s) found in {test_file_rel}:\n{found_mocks_str}",
            pytrace=False,  # Keep pytrace False for cleaner output
            # (
            #     f"Forbidden internal mocks found in {test_file_rel}:\n{found_mocks_str}\n"
            #     f"Internal mocking is only allowed if explicitly listed for this file in mock_whitelist.toml. "
            #     f"Refer to ZLF (Sec 3, Principle 6). Test against real implementations where possible."
            # ),
        )
