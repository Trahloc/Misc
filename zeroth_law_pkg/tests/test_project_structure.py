from pathlib import Path

import pytest

# --- Configuration ---
try:
    # Assumes the tests directory is directly under the workspace root
    WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
except NameError:
    # Fallback to current working directory, assuming it's the root
    WORKSPACE_ROOT = Path.cwd().resolve()

SRC_DIR = WORKSPACE_ROOT / "src" / "zeroth_law"
TESTS_DIR = WORKSPACE_ROOT / "tests"

# Files/patterns to exclude from the source code check (not requiring dedicated test files)
SRC_EXCLUDE_PATTERNS = [
    "__init__.py",
    "__main__.py",  # Often just calls another function tested elsewhere
    "cli.py",  # Often tested via integration tests or dedicated CLI tests
    "dev_scripts/",  # Exclude development scripts
    "tools/",  # Exclude tool configurations
    # Add other patterns if needed
]

# Files/patterns to exclude from the test code check (don't correspond 1:1 to a source module)
TEST_EXCLUDE_PATTERNS = [
    "__init__.py",
    "conftest.py",  # Pytest configuration, fixtures
    "test_tool_integration.py",  # Our specific integration test
    "test_project_structure.py",  # This file itself
    # Exclude tests for broader functionality or configurations
    "test_cli_help.py",
    "test_cli_help_options.py",
    "test_cli_json_output.py",
    "test_cli_option_validation.py",
    "test_cli_refactor.py",
    "test_cli_simple.py",
    "test_cli_structure.py",
    "test_cruft_detection.py",
    "test_generate_structure_data.py",
    "test_git_execution.py",
    "test_tool_defs/",  # Exclude the entire tool definitions test directory
    # Analyzer tests that don't map 1:1 to a source file
    "analyzer/python/test_analyzer_refactor_errors.py",
    "analyzer/python/test_file_analyzer.py",
    # Add other patterns if needed
]

# --- Helper Functions ---


def _is_excluded(path: Path, exclude_patterns: list[str], base_dir: Path) -> bool:
    """Check if a path matches any exclusion patterns relative to a base dir."""
    relative_path_str = str(path.relative_to(base_dir))
    for pattern in exclude_patterns:
        if pattern.endswith("/"):  # Directory pattern
            if relative_path_str.startswith(pattern.rstrip("/")):
                return True
        elif pattern == Path(relative_path_str).name:  # Filename pattern
            return True
        elif path.match(pattern):  # Glob pattern
            return True
    return False


def get_source_modules(src_dir: Path, exclude_patterns: list[str]) -> set[Path]:
    """Find all potentially testable python modules in the source directory."""
    modules: set[Path] = set()
    if not src_dir.is_dir():
        return modules
    for path in src_dir.rglob("*.py"):
        if not _is_excluded(path, exclude_patterns, src_dir):
            modules.add(path)
    return modules


def get_test_modules(tests_dir: Path, exclude_patterns: list[str]) -> set[Path]:
    """Find all test modules in the tests directory."""
    modules: set[Path] = set()
    if not tests_dir.is_dir():
        return modules
    for path in tests_dir.rglob("test_*.py"):
        if not _is_excluded(path, exclude_patterns, tests_dir):
            modules.add(path)
    return modules


def get_expected_test_path(src_path: Path, src_base: Path, test_base: Path) -> Path:
    """Calculate the expected test file path based on the source file path."""
    relative_path = src_path.relative_to(src_base)
    # Insert 'test_' before the final filename stem
    test_filename = f"test_{relative_path.stem}{relative_path.suffix}"
    return test_base / relative_path.parent / test_filename


def get_expected_source_path(test_path: Path, test_base: Path, src_base: Path) -> Path:
    """Calculate the expected source file path based on the test file path."""
    relative_path = test_path.relative_to(test_base)
    # Remove 'test_' prefix from the filename stem
    if not relative_path.stem.startswith("test_"):
        # This case should ideally not happen if get_test_modules is correct,
        # but handle defensively.
        raise ValueError(f"Test file does not start with 'test_': {test_path}")
    src_filename = f"{relative_path.stem[5:]}{relative_path.suffix}"
    return src_base / relative_path.parent / src_filename


# --- Tests ---

# Calculate module lists here, AFTER constants and helpers are defined
SOURCE_MODULES = get_source_modules(SRC_DIR, SRC_EXCLUDE_PATTERNS)
TEST_MODULES = get_test_modules(TESTS_DIR, TEST_EXCLUDE_PATTERNS)

# Generate expected paths for easier comparison
EXPECTED_TEST_PATHS = {get_expected_test_path(p, SRC_DIR, TESTS_DIR) for p in SOURCE_MODULES}
EXPECTED_SOURCE_PATHS = {get_expected_source_path(p, TESTS_DIR, SRC_DIR) for p in TEST_MODULES}


def test_untested_source_modules():
    """Check for source modules that don't have a corresponding test module."""
    untested_modules = []
    for src_module in SOURCE_MODULES:
        expected_test = get_expected_test_path(src_module, SRC_DIR, TESTS_DIR)
        if not expected_test.is_file():
            untested_modules.append(src_module.relative_to(WORKSPACE_ROOT))

    if untested_modules:
        file_list = "\n - ".join(map(str, sorted(untested_modules)))
        pytest.fail("Found source modules missing corresponding test files " f"(following convention src/pkg/foo.py -> tests/test_foo.py or " f"src/pkg/subdir/bar.py -> tests/subdir/test_bar.py):\n - {file_list}")


def test_orphan_test_modules():
    """Check for test modules that don't have a corresponding source module."""
    orphan_modules = []
    for test_module in TEST_MODULES:
        try:
            expected_source = get_expected_source_path(test_module, TESTS_DIR, SRC_DIR)
            if not expected_source.is_file():
                orphan_modules.append(test_module.relative_to(WORKSPACE_ROOT))
        except ValueError as e:
            # Catch issues with the naming convention itself from the helper
            pytest.fail(f"Error processing test file {test_module}: {e}")

    if orphan_modules:
        file_list = "\n - ".join(map(str, sorted(orphan_modules)))
        pytest.fail("Found orphan test files whose corresponding source module could not be found " f"(following convention tests/test_foo.py -> src/pkg/foo.py or " f"tests/subdir/test_bar.py -> src/pkg/subdir/bar.py):\n - {file_list}")
