# Zeroth Law Auditor

Enforcer for the [Zeroth Law AI Framework](frameworks/python/ZerothLawAIFramework.py313.md).

## Setup

This project uses Python 3.13+ and `poetry` for dependency management.

1.  **Install Poetry:** Follow the instructions at [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)
2.  **Configure Poetry (Optional):** You might want to configure Poetry to create virtual environments inside the project directory:
    ```bash
    poetry config virtualenvs.in-project true
    ```
3.  **Install Dependencies:** Navigate to the project root directory (where `pyproject.toml` is located) and run:
    ```bash
    poetry install --all-extras # Installs main and development dependencies
    ```
    This creates a virtual environment (usually in `.venv/` if configured as above) and installs all necessary packages.

4.  **Activate Virtual Environment:**
    *   If you configured `virtualenvs.in-project`, activate using:
        ```bash
        source .venv/bin/activate
        ```
    *   Otherwise, use Poetry's shell command:
        ```bash
        poetry shell
        ```

5.  **Install Pre-commit Hooks:** While the virtual environment is active, install the pre-commit hooks:
    ```bash
    pre-commit install
    ```

## Usage

Once the environment is activated and the package installed (`poetry install`), you can run the auditor using:

```bash
zeroth-law [OPTIONS] [PATHS]...
```

Or via `poetry run`:

```bash
poetry run zeroth-law [OPTIONS] [PATHS]...
```

Run `zeroth-law --help` for a list of options.

## Running Tests

Activate the virtual environment and run:

```bash
poetry run pytest
```

## Contributing

Please follow the setup instructions and ensure pre-commit hooks pass before submitting changes.
