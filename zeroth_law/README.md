# Zeroth Law Tool

Enforcer for the Zeroth Law AI Framework.

## Overview

This tool ensures adherence to the rules and guidelines defined in the Zeroth Law AI Framework (`frameworks/python/ZerothLawAIFramework.py313.md`).

## Setup

This project uses `micromamba` for environment management and `poetry` for dependency management.

1.  **Install Micromamba:** Follow the instructions at [https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)
2.  **Install Poetry:** Follow the instructions at [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)
3.  **Enable Poetry Conda Plugin:** `poetry self add poetry-plugin-conda`
4.  **Create Conda Environment:**
    ```bash
    # Ensure requirements files are up-to-date (if pyproject.toml changed)
    # ./scripts/generate_requirements.sh

    # Create the environment using the minimal environment.yml
    micromamba env create -f environment.yml
    ```
    *Alternatively, update an existing environment:* `micromamba env update -f environment.yml --prune`
5.  **Activate Environment:**
    ```bash
    micromamba activate zeroth_law # Or the name defined in environment.yml
    ```
6.  **Install Development Dependencies:**
    ```bash
    # Ensure requirements files are up-to-date first if needed:
    # ./scripts/generate_requirements.sh

    # Install dev dependencies using pip
    pip install -r requirements-dev.txt
    ```
7.  **Install Project in Editable Mode (for development):**
    ```bash
    pip install -e .
    ```
8.  **Install Pre-commit Hooks:**
    ```bash
    pre-commit install
    # pre-commit install --hook-type commit-msg # If using commitlint
    ```

## Usage

*(To be added during development)*

## Development

This project follows strict Test-Driven Development (TDD).

*   **Run Checks:** `ruff check .`, `ruff format .`, `mypy --strict .`, `pylint --disable=all --enable=R0801 src/ tests/`
*   **Run Tests:** `pytest`
*   **Run Tests with Coverage:** `pytest --cov=src/zeroth_law tests/`

## Contributing

*(To be added later - include details on Conventional Commits)*
