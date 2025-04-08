# Legacy Zeroth Law Tool Analysis Summary

This document summarizes the core functionality and structure of the legacy `zeroth_law` tool found in the `.legacy` directory. This analysis serves as a reference for the goals and features to be reimplemented using the new framework and TDD methodology.

**Overall Purpose:**

The legacy tool was a configurable static analysis tool focused on enforcing a specific set of coding standards within Python projects, based on its own interpretation of "Zeroth Law" principles at the time.

**Key Features & Functionality:**

1.  **AST-Based Analysis:**
    *   Used Python's built-in `ast` module to parse Python source code into an Abstract Syntax Tree.
    *   Traversed the AST to identify code structures (functions, imports, etc.).

2.  **Metric Calculation (`metrics/` directory):**
    *   **Cyclomatic Complexity:** Calculated per function using an `ast.NodeVisitor`. Also counted branches, returns, and statements. Compared against configurable thresholds. (`metrics/cyclomatic_complexity.py`)
    *   **Line Counts:** Calculated total lines, executable lines (excluding comments, blank lines, docstrings), header/footer lines, and lines per function. (`utils/file_utils.py`, `metrics/file_size.py`, `metrics/function_size.py`)
    *   **Docstring Coverage:** Checked for the presence of docstrings in modules, classes, and functions using `ast.get_docstring`. (`metrics/docstring_coverage.py`)
    *   **Parameter Count:** Counted parameters per function using AST information.
    *   **Import Count:** Counted import statements. (`metrics/imports.py`)
    *   **Naming Conventions:** Checked naming (details TBD, likely basic checks). (`metrics/naming.py`)

3.  **Rule Enforcement & Compliance Scoring (`analyzer/evaluator.py`):**
    *   Checked for mandatory **Header Comments** (module-level docstring).
    *   Checked for mandatory **Footer Comments** (specific `## ZEROTH LAW COMPLIANCE:` block in a trailing docstring).
    *   Compared calculated metrics against configurable thresholds (e.g., max executable lines, max complexity, max function lines, max parameters).
    *   Calculated an `overall_score` (0-100) based on penalties applied for rule violations.
    *   Determined a qualitative `compliance_level` (e.g., "Excellent", "Good") based on the score.

4.  **Reporting (`reporting/` directory):**
    *   Generated detailed, human-readable compliance reports for individual files (`reporting/formatter.py::format_compliance_report`).
    *   Generated summary reports for directory analysis (`reporting/formatter.py::format_summary_report`).

5.  **Auto-Updating Footers (`reporting/updater.py`):**
    *   Could automatically update or add the standard Zeroth Law footer comment block to analyzed files (`-u` flag).
    *   Embedded the latest analysis results (score, level, penalties, timestamp) into the footer.
    *   Crucially, attempted to preserve existing content under specific sub-sections within the footer (`## KNOWN ERRORS:`, `## IMPROVEMENTS:`, `## FUTURE TODOs:`).
    *   Ran `black` formatting on Python files after updating the footer.

6.  **Configuration (`utils/config.py`):**
    *   Loaded settings (thresholds, penalties, ignore patterns) from `pyproject.toml` under `[tool.zeroth_law]`.
    *   Also read some settings from `[tool.black]` (line length) and `[tool.pylint]` (max args, locals, statements) if present.
    *   Provided built-in default values for all settings.

7.  **Templating & Skeleton (`skeleton.py`, `template_converter.py`):**
    *   Included features to create new project skeletons using `cookiecutter` (`--skel` flag). (`skeleton.py`)
    *   Could convert an existing project directory into a reusable `cookiecutter` template (`--template-from` flag). (`template_converter.py`)
    *   Managed template discovery and listing.

8.  **Test File Checks (`test_coverage.py`):**
    *   Verified the *existence* of corresponding `test_*.py` files for source files (e.g., `src/module/foo.py` should have `tests/module/test_foo.py`). This was *not* code execution coverage.
    *   Could automatically generate basic test stub files (`--create-test-stubs`) if corresponding test files were missing.

9.  **Command-Line Interface (`cli.py`):**
    *   Provided a CLI using `click`.
    *   Handled argument parsing for analysis targets, reporting options, configuration, auto-updating, templating, and test checks.
    *   Orchestrated calls to the relevant analyzer, reporter, and utility functions.

10. **File Handling (`analyzer/file_validator.py`, `analyzer/template_handler.py`):**
    *   Ignored files based on configured patterns.
    *   Validated files (existence, `.py` extension).
    *   Distinguished between regular Python files and template files (usually files in a `templates/` dir), applying only basic checks to templates.
    *   Checked for unrendered template syntax (`{{ ... }}`) in non-template files.

11. **Custom Exceptions (`exceptions.py`):**
    *   Defined specific error types (e.g., `AnalysisError`, `ConfigError`, `CoverageError`).

**Core Modules Summary:**

*   `.legacy/src/zeroth_law/`
    *   `analyzer/`: Core logic for parsing (`ast`), metric calculation delegation, rule evaluation. (`core.py`, `evaluator.py`, `file_validator.py`, `template_handler.py`)
    *   `metrics/`: Modules for calculating specific code metrics.
    *   `reporting/`: Modules for formatting output reports and updating file footers. (`formatter.py`, `updater.py`)
    *   `utils/`: Helper functions for file operations, config loading, AST manipulation. (`config.py`, `file_utils.py`)
    *   `templates/`: Contained `cookiecutter` templates.
    *   `cli.py`: Command-line interface definition (`click`).
    *   `skeleton.py`: Project skeleton creation (`cookiecutter`).
    *   `template_converter.py`: Conversion of projects to templates.
    *   `test_coverage.py`: Test file existence checks and stub generation.
    *   `exceptions.py`: Custom exception classes.
