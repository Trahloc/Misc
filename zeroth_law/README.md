<!--/zeroth_law/README.md-->

# Zeroth Law Analyzer

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

A Python code analyzer to enforce the Zeroth Law of AI-Driven Development.

## What is the Zeroth Law?

The Zeroth Law is a set of coding principles designed to maximize code comprehension for AI assistants. It prioritizes clarity, modularity (one function per file), and explicit API design (using `__init__.py`). See the `ZEROTH_LAW.md` file in this repository for the full specification.

## Features

*   **Analyzes Python code** for compliance with the Zeroth Law.
*   **Uses the `ast` module** for accurate parsing (no fragile regex!).
*   **Modular design:** Follows the Zeroth Law itself (one function per file, mostly).
*   **Provides detailed reports:** Highlights areas for improvement.
*   **Supports file and directory analysis** (including recursive analysis).
*   **Integrates with `pre-commit`:** Automate checks before committing code.
*   **Type-hinted:** For clarity and static analysis.

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

### --init option (Future Development)
```bash
python -m zeroth_law.cli --init <directory>
```
Creates a directory with sample `__init__.py` and a python module file.

## Project Structure

```
zeroth_law_project/
├── src/
│   └── zeroth_law/
│       ├── __init__.py        # Public API
│       ├── analyzer.py      # Main analysis logic
│       ├── cli.py           # Command-line interface
│       ├── metrics/         # Metric calculation modules
│       │   ├── __init__.py
│       │   ├── cyclomatic_complexity.py
│       │   ├── docstring_coverage.py
│       │   ├── file_size.py
│       │   ├── function_size.py
│       │   ├── imports.py
│       │   └── naming.py
│       ├── pyproject.toml   # Python packaging
│       ├── reporting.py     # Report generation
│       └── utils.py         # Utility functions
└── tests/               # Unit tests (mirroring src structure)
    └── zeroth_law/
       ├── __init__.py
       ├── test_analyzer.py
        ...
```

## Contributing

Contributions are welcome! Please follow the Zeroth Law principles when contributing code.

## License

MIT License (see LICENSE file)