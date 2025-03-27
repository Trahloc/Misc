<!--# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/README.md-->

# Zeroth Law Analyzer

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

A Python code analyzer to enforce the Zeroth Law of AI-Driven Development.

## What is the Zeroth Law?

The Zeroth Law is a set of coding principles designed to maximize code comprehension for AI assistants. It prioritizes clarity, modularity (one function per file), and explicit API design (using `__init__.py`). See the `ZEROTH_LAW.md` file in this repository for the full specification.

## Features

*   **Comprehensive Code Analysis:**
    - Cyclomatic complexity measurement
    - Docstring coverage verification
    - Semantic naming evaluation
    - Import usage analysis
    - File and function size metrics
*   **High-Quality Implementation:**
    - Comprehensive docstrings with examples
    - 100% test coverage for core modules
    - Type hints throughout
    - Modular design following Zeroth Law principles
*   **Developer-Friendly Tools:**
    - Detailed compliance reports
    - Automatic footer updates with metrics
    - Pre-commit integration
    - Test coverage verification
    - Template project generation

## Recent Improvements

*   **Enhanced Documentation:**
    - Added comprehensive docstrings to all core modules
    - Included usage examples in complex functions
    - Improved type hints and parameter descriptions
*   **Code Quality:**
    - Removed unused imports
    - Fixed deprecation warnings
    - Enhanced test coverage
*   **Metrics Calculation:**
    - Improved cyclomatic complexity calculation
    - Enhanced semantic naming score algorithm
    - Better docstring coverage detection

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install (editable mode recommended for development):**

    ```bash
    pip install -e .
    ```

## Usage

### Command-Line Interface

```bash
python -m zeroth_law.cli <path> [options]
```

*   **`<path>`:**  Path to a Python file or directory.
*   **`-r` or `--recursive`:** Analyze directories recursively.
*   **`-s` or `--summary`:** Generate a summary report (for directories).
*   **`-u` or `--update`:** Update file footers with analysis results.
*   **`--skel DIRECTORY`:** Create a new Zeroth Law project skeleton.
*   **`--test-coverage`:** Verify test coverage for the project.
*   **`--create-test-stubs`:** Create test stubs for files without tests.

**Examples:**

*   Analyze a single file:
    ```bash
    python -m zeroth_law.cli my_module/my_function.py
    ```
*   Analyze a directory (non-recursive):
    ```bash
    python -m zeroth_law.cli my_module/
    ```
*   Analyze a directory recursively:
    ```bash
    python -m zeroth_law.cli my_project/ -r
    ```
*   Generate a summary report:
    ```bash
    python -m zeroth_law.cli my_project/ -r -s
    ```
*   Create a new project skeleton:
    ```bash
    python -m zeroth_law.cli --skel my_new_project
    ```
*   Verify test coverage for a project:
    ```bash
    python -m zeroth_law.cli my_project --test-coverage
    ```
*   Create test stubs for files without tests:
    ```bash
    python -m zeroth_law.cli my_project --test-coverage --create-test-stubs
    ```

### Pre-commit Integration

1.  **Install `pre-commit`:**

    ```bash
    pip install pre-commit
    ```

2.  **Add to your `.pre-commit-config.yaml`:**

    ```yaml
    repos:
      - repo: local
        hooks:
          - id: zeroth-law
            name: Zeroth Law Analyzer
            entry: python -m zeroth_law.cli
            language: python
            files: '\.py$'
            args: [-r]  # Add -s for summary reports
    ```

3.  **Install the hooks:**

    ```bash
    pre-commit install
    ```

Now, the Zeroth Law analyzer will run automatically before each commit.

## Project Structure

```
zeroth_law_project/
├── src/
│   └── zeroth_law/
│       ├── __init__.py        # Public API
│       ├── analyzer.py        # Main analysis logic
│       ├── cli.py            # Command-line interface
│       ├── metrics/          # Metric calculation modules
│       │   ├── __init__.py
│       │   ├── cyclomatic_complexity.py
│       │   ├── docstring_coverage.py
│       │   ├── file_size.py
│       │   ├── function_size.py
│       │   ├── imports.py
│       │   └── naming.py
│       ├── pyproject.toml    # Python packaging
│       ├── reporting.py      # Report generation
│       └── utils.py          # Utility functions
└── tests/                    # Unit tests (mirroring src structure)
    └── zeroth_law/
        ├── __init__.py
        ├── test_analyzer.py
        ├── test_utils.py
        └── test_reporting.py
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Follow the Zeroth Law principles in your code
2. Add comprehensive docstrings with examples
3. Include unit tests for new functionality
4. Use type hints consistently
5. Run the analyzer on your code before submitting

## License

MIT License (see LICENSE file)