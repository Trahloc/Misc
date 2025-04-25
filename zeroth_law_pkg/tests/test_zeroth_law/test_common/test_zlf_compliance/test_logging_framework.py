# tests/test_zlf_compliance/test_logging_framework.py
import ast
import logging  # Import standard logging *only for comparison*
import sys
from pathlib import Path
import pytest
import inspect  # To get source file paths

# Define the core modules to check
# Ensure these module names are correct relative to the project structure
MODULES_TO_CHECK = [
    "zeroth_law.cli",
    "zeroth_law.action_runner",
    "zeroth_law.dynamic_commands",
    "zeroth_law.common.config_loader",
    "zeroth_law.dev_scripts.baseline_generator",  # Example of checking dev scripts too
    # Add other core modules as needed
]

# Allow structlog itself and this test file
ALLOWED_LOGGING_MODULES = {"structlog", __name__}


# --- Helper to find standard logging usage ---
class LoggingUsageFinder(ast.NodeVisitor):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.found_violations = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name == "logging":
                self.found_violations.append(f"Standard 'import logging' found at {self.filepath}:{node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "logging":
            # Check if importing something other than basicConfig/levels for comparison
            # You might refine this check if specific logging functions are allowed temporarily
            self.found_violations.append(f"Standard 'from logging import ...' found at {self.filepath}:{node.lineno}")
        self.generic_visit(node)

    # Optional: Add checks for specific calls like logging.getLogger() if needed,
    # but checking imports is often sufficient to detect usage.
    # def visit_Call(self, node):
    #     if isinstance(node.func, ast.Attribute):
    #         if isinstance(node.func.value, ast.Name) and node.func.value.id == 'logging':
    #             # Found a call like logging.getLogger(...) or logging.info(...)
    #             self.found_violations.append(f"Direct call to logging.{node.func.attr} found at {self.filepath}:{node.lineno}")
    #     self.generic_visit(node)


# --- The Pytest Test Function ---
@pytest.mark.zlf_compliance  # Add a marker for easy selection/deselection
def test_enforce_structlog_usage():
    """
    Verify that core modules use structlog instead of the standard logging module,
    as mandated by ZLF Section 4.6.
    """
    violations = []
    project_root = (
        Path(__file__).resolve().parents[4]
    )  # Go up 4 levels from tests/test_zeroth_law/test_common/test_zlf_compliance
    src_root = project_root / "src"

    for module_base_name in MODULES_TO_CHECK:
        try:
            # Construct path relative to src_root
            # e.g., "zeroth_law.cli" -> src/zeroth_law/cli.py
            module_rel_path = Path(*module_base_name.split(".")).with_suffix(".py")
            module_path = src_root / module_rel_path

            if not module_path.is_file():
                pytest.fail(f"Could not find module source file: {module_path}")

            with open(module_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            tree = ast.parse(source_code)
            finder = LoggingUsageFinder(filepath=str(module_path))
            finder.visit(tree)
            violations.extend(finder.found_violations)

        except FileNotFoundError:
            pytest.fail(f"Source file not found for module '{module_base_name}' at expected path: {module_path}")
        except Exception as e:
            pytest.fail(f"Error processing module '{module_base_name}' source ({module_path}): {e}")

    if violations:
        failure_message = (
            "ZLF Compliance Error: Standard 'logging' module usage detected. "
            "ZLF Section 4.6 mandates the use of 'structlog'.\n"
            "Please refactor the following locations to use 'structlog':\n"
            + "\n".join(f"- {v}" for v in violations)
            + "\n\n"
            "Refactoring Steps:\n"
            "1. Ensure 'structlog' is a project dependency in pyproject.toml.\n"
            "2. Configure structlog (e.g., in cli.py or main entry point) using "
            "structlog.configure() with appropriate processors (e.g., "
            "structlog.stdlib.ProcessorFormatter, structlog.dev.ConsoleRenderer "
            "for dev, structlog.processors.JSONRenderer for CI/prod).\n"
            "3. Replace `logging.getLogger(...)` with `structlog.get_logger(...)`.\n"
            "4. Replace standard logging calls (e.g., `logger.info(...)`) with structlog calls, "
            "passing context as keyword arguments (e.g., `log.info('event_name', key=value)`).\n"
            "5. Use `log.bind(**context)` or `structlog.contextvars.bind_contextvars(...)` "
            "to add persistent context.\n"
            "6. Update any tests that assert on log output to use `structlog.testing.capture_logs()` "
            "and check the structured log entries (dictionaries).\n"
            "7. Refer to ZLF Section 4.6 and the structlog documentation for details."
        )
        pytest.fail(failure_message, pytrace=False)
