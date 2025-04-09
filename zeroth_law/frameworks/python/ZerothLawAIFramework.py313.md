# Zeroth Law: AI-Driven Python Code Quality Framework

**Co-Author**: Trahloc colDhart
**Version**: 2025-04-09

---

## 1. PURPOSE
Design a minimal, AI-first framework for Python code quality targeting **Python 3.13+** and **`poetry`** for environment and dependency management. By mandating **Test-Driven Development (TDD)** alongside enforcing clarity, simplicity, modular design, opinionated standards, and comprehensive automated checks, this framework ensures every component is demonstrably correct, immediately understandable, maintainable, and verifiable, leveraging AI assistance for continuous refactoring and adaptation.

## 2. APPLICATION
All new or modified code **must** be developed following the Test-Driven Development cycle and pass all associated tests and guideline checks before merging into the main branch. Automated checks via `pre-commit` and CI apply each requirement based on configurations in `pyproject.toml`, blocking completion until tests pass and consistency is assured. This framework assumes AI actively assists in development (including test generation and refactoring) within the TDD loop, enabling rapid evolution and adherence to modern standards. Development utilizes **`poetry`** environments defined by `pyproject.toml` dependency specifications.

## 3. GUIDING PRINCIPLES

1.  **Test-Driven Development (TDD) First**: **Require** all production code to be driven by tests. Follow the strict **Red-Green-Refactor** cycle: write a failing test (Red), write the minimum code to pass the test (Green), then improve the code while keeping tests green (Refactor). This ensures inherent testability, verifiable correctness, and drives emergent design.
2.  **Single Responsibility & Clear API Boundaries**: Keep components focused on one reason to change, making them easier to test and reason about via TDD. Expose minimal necessary interfaces via `__init__.py` (managed by `autoinit` if desired). Isolation simplifies AI reasoning and independent refinement.
3.  **First Principles Simplicity**: Solve problems directly with minimal complexity, driven by the need to pass the current test. Prefer clear Python 3.13+ features over intricate abstractions. Minimalism reduces error surface and boosts AI refactoring confidence within the TDD cycle.
4.  **Follow Modern Project Standards**: Align with conventions from contemporary, reputable Python projects known for quality. Adopt proven patterns while remaining open to evolution. Use influential standards like `black` formatting as context, but configure `ruff format` to project-specific needs defined herein.
5.  **Leverage Existing Libraries (No Reinvention & No Monkey-Patching)**: Utilize stable, well-maintained PyPI packages compatible with Python 3.13+. Treat vetted libraries as reliable blocks, focusing AI effort on unique project logic tested at integration boundaries. **Strictly forbid** modifying the internal behavior of third-party libraries at runtime (monkey-patching). Interact with libraries only through their documented public APIs. Configure tools via their intended mechanisms (configuration files, command-line arguments), never by altering their code dynamically.
6.  **Don't Repeat Yourself (DRY)**: During the Refactor step of TDD, consolidate logic identified via testing or analysis (`pylint R0801`). Eliminate duplication to reduce debt and ensure consistent updates.
7.  **Self-Documenting Code & Explaining Rationale**: Use descriptive names (`what`). Employ docstrings/comments to explain the *why* (rationale, context) for non-obvious logic discovered during implementation or refactoring. Assume an AI reader understands Python 3.13+ syntax; provide the background needed for maintenance and AI-driven refactoring. Documentation follows implementation within the TDD cycle.
8.  **Consistent Style & Idiomatic Usage**: Apply uniform coding style enforced by `ruff format` (project config) and `ruff check`, along with modern type hints and Python 3.13+ idioms. Style checks are part of the automated feedback loop.
9.  **Comprehensive Testing & Automation (Inherent via TDD)**: TDD naturally produces high test coverage for correctness and regression prevention. Automate checks (`ruff`, `mypy`, `pylint`, `pytest`) via `pre-commit` and CI as essential feedback mechanisms supporting the TDD workflow.
10. **Explicit Error Handling & Reliable Resource Management**: Design tests that cover expected error conditions. Implement specific exception handling and ensure resources (files, connections, locks) are reliably released via context managers (`with`) or `try...finally`, verified by tests covering success and failure paths.
11. **AI-Enabled Continuous Refactoring (TDD Refactor Step)**: Embrace code evolution within the **Refactor** step of the TDD cycle. Regularly refine structure, reduce complexity, and adopt new language/tool features, leveraging AI assistance and the safety net of comprehensive tests created during development.
12. **Design for Concurrency Safety (When Required & Testable)**: If concurrency is needed, use TDD to drive the design. Write tests that expose potential race conditions or safety issues, then implement solutions using appropriate mechanisms (e.g., `asyncio`, `threading`). Prevent race conditions and document the concurrency model. (See Sec 4.8 for specific practices).
13. **Adhere to Filesystem Standards (XDG & Tooling Configuration)**:
    *   **Runtime:** Applications **must** store user-specific files according to the XDG Base Directory Specification (using `$XDG_CONFIG_HOME`, `$XDG_DATA_HOME`, `$XDG_CACHE_HOME`, `$XDG_RUNTIME_DIR`). Write tests that verify correct file placement where applicable.
    *   **Tooling:** Development/CI tooling **must**, where configurable, be set up to use XDG-compliant directories for caches/config, enforced via environment variables or `pyproject.toml`.

---

## 4. KEY METRICS & PRACTICES

### 4.1 Test-Driven Development Workflow
*   **Red-Green-Refactor Cycle:** **Mandatory** adherence to the TDD cycle for all production code changes.
*   **Test Granularity:** Write small, focused tests targeting specific behaviors or requirements.
*   **Minimum Viable Code (Green Step):** Implement only the code necessary to pass the current failing test before proceeding to refactor.
*   **Refactoring Safety Net:** Rely on the comprehensive test suite created during TDD to refactor code confidently.
*   **Test Coverage (Outcome):** High test coverage is an expected outcome of rigorous TDD, not a separate target to be achieved after coding. Aim for logical coverage verified by `pytest --cov`.

### 4.2 AI Quality & Readability
*   **Context Independence**: Aim for files readable as standalone units, often driven by testable components.
*   **AI Insight Documentation**: Docstrings clarify purpose (defined by tests), rationale (context), pre/post-conditions, and usage.
*   **Implementation Consistency**: >95% adherence to patterns. Enforce format with `ruff format` and linting/style/docs with `ruff check`.

### 4.3 File Organization
*   **File Purpose**: Header docstring specifies single responsibility (often corresponding to a test suite focus).
*   **File Size**: Target < 300 lines (excluding docstrings/comments), encouraged by TDD's focus on small units.
*   **Module Interface**: Strict exposure via `__init__.py` (use `autoinit` if desired).

### 4.4 Code Quality
*   **Semantic Naming**: Descriptive identifiers.
*   **Function Size**: Target < 30 lines (excluding docstrings/comments), naturally promoted by TDD.
*   **Function Signature**: ≤ 4 parameters; use data classes/TypedDicts/Pydantic models for more.
*   **Cyclomatic Complexity**: Prefer < 8 (via `ruff mccabe`). Keep units simple for testability.
*   **Code Duplication**: Eliminate duplication during the Refactor TDD step (verify via `pylint R0801`).
*   **Mandatory Type Annotation**: **Require** explicit, modern (Python 3.13+) type hints. Enforce with `mypy --strict`.
*   **Minimize Mutable Global State**: Avoid module-level mutable variables. Pass state explicitly.
*   **Favor Immutability**: **Require** favoring immutable data structures universally unless mutability is essential.

### 4.5 Error Reporting & Logging
*   **Test Error Conditions:** Write tests specifically for expected failure modes and exception handling.
*   **Traceability**: Exceptions include context. Use chaining/groups appropriately.
*   **Logging Format:** **Mandatory JSON format** via **`structlog`**, configured with a JSON processor.
*   **Logging Implementation:** Include standard fields (`timestamp`, `level`, `event`, `logger`) and context. Test logging output where critical.
*   **Exception Management**: Raise specific exceptions based on tested failure conditions. Avoid broad `except Exception:`. Enforce with `ruff` rules.
*   **No Internal Fallbacks**: Fail explicitly internally based on test expectations.

### 4.6 Data Validation & Parsing
*   **External Data Handling:** **Require** **Pydantic** models for defining, parsing, and validating non-trivial external data structures. Write tests covering valid and invalid data scenarios using these models.
*   **Runtime Validation vs. Assertions:** Use Pydantic/explicit checks for *external* inputs (tested); use `assert` for *internal* invariants verified during TDD.

### 4.7 Defensive Programming & Assertions
*   **Strategic Assertions**: Use `assert` for internal invariants/conditions identified and verified during the TDD Refactor step.
*   **Pre/Post-condition Checks**: Verify critical internal states via assertions, driven by test cases.
*   **Invariant Checks**: Assert conditions that tests assume must always hold.
*   **Assertion Density**: Guided by test logic and invariants discovered during development.
*   **Verbose Testing**: `pytest -vv`. Ensure assertion messages aid debugging test failures.

### 4.8 Resource Management Practices *(Apply if project requires concurrency & driven by tests)*
*   **(Note: Universal principles are in Sec 4.4)**
*   **Test Concurrency Issues:** Write tests specifically designed to provoke race conditions or verify synchronization if possible (can be challenging).
*   **Use Synchronization Primitives**: Protect necessary shared state with appropriate mechanisms, driven by failing tests where feasible.
*   **Document Concurrency Model**: Specify thread/async safety and strategy (`stateless`, `synchronized`, etc.) in `CONTEXT`.
*   **Verify External Calls**: Ensure external interactions are concurrency-safe or protected.
*   **`asyncio` Best Practices (if using `asyncio`):** Apply requirements (avoid blocking, use `async with/for`, manage tasks) driven by tests for async functionality.

### 4.9 Concurrency Safety Practices *(Apply if project requires concurrency & driven by tests)*
*   **(Note: Universal principles are in Sec 4.4)**
*   **Test Concurrency Issues:** Write tests specifically designed to provoke race conditions or verify synchronization if possible (can be challenging).
*   **Use Synchronization Primitives**: Protect necessary shared state with appropriate mechanisms, driven by failing tests where feasible.
*   **Document Concurrency Model**: Specify thread/async safety and strategy (`stateless`, `synchronized`, etc.) in `CONTEXT`.
*   **Verify External Calls**: Ensure external interactions are concurrency-safe or protected.
*   **`asyncio` Best Practices (if using `asyncio`):** Apply requirements (avoid blocking, use `async with/for`, manage tasks) driven by tests for async functionality.

### 4.10 Commit Message Standards
*   **Conventional Commits:** **Require** adherence to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification for all Git commit messages. Commits often correspond to TDD cycles (e.g., `feat: implement X`, `test: add test for Y`, `refactor: improve Z`).

### 4.11 Versioning Scheme
*   **Epoch/Date Versioning:** **Require** utilizing a strictly increasing version scheme based on time (Unix epoch seconds or `YYYYMMDD.HHMMSS`). Define in `pyproject.toml` (`[tool.poetry.version]`). Relies on comprehensive TDD suite for compatibility assurance.

### 4.12 Validation Metrics (Outcomes & Enforcements)
*   **Test Coverage**: High coverage is an outcome of TDD. Verify via `pytest --cov` and `fail_under` threshold in CI.
*   **Type Coverage**: 100% (via `mypy --strict`).
*   **Code Duplication**: Zero warnings from `pylint R0801` (addressed during Refactor step).
*   **Documentation Coverage**: 100% public APIs (`ruff D` rules). Documentation written after passing tests, before/during Refactor.
*   **Docstring Style Compliance**: Adherence to convention (`ruff D` rules).
*   **Docstring Example Coverage**: **Require** `USAGE EXAMPLES:` for non-trivial public APIs (review).
*   **Runtime Type Guards**: **Require** validation of external inputs via Pydantic/explicit checks, driven by tests.

### 4.13 Dependencies & Environment
*   **Dependency Specification:** Define in `pyproject.toml` under `[tool.poetry.dependencies]` and development groups (e.g., `[tool.poetry.group.dev.dependencies]`).
*   **Environment Management:** **Require** use of **`poetry`** for managing dependencies and virtual environments based on `pyproject.toml` and `poetry.lock`.
*   **Vetting**: Prefer standard libraries and reputable PyPI packages compatible with Python 3.13+. Check licenses.
*   **Justification**: Document reasons for significant third-party dependencies.
*   **Minimize Environment Assumptions**: Strive for OS consistency. Document specific needs.

---

## 5. IN-FILE DOCUMENTATION PATTERN

Employ this consistent Header-Implementation-Footer structure in every Python file. Content should reflect Python 3.13+ features, Pydantic usage, and `structlog` patterns where applicable.

### 5.1 Header
```python
# FILE: ...
"""
# PURPOSE: [Single responsibility, often derived from the initial test's goal.]
# ...
"""
```### 5.2 Implementation Example (Conceptual TDD Flow)
```python
# 1. Write Test (RED) - test_module.py
# def test_perform_action_success(): ... assert perform_action(...) is True

# 2. Write Minimum Code (GREEN) - module.py
# def perform_action(config: ConfigData, item_id: str) -> bool: return True

# 3. Refactor & Add Docs/Logging (REFACTOR) - module.py
import structlog
from pydantic import BaseModel
# ... (imports, models) ...
log = structlog.get_logger()

def perform_action(config: ConfigData, item_id: str) -> bool:
    """PURPOSE: Performs an action using validated configuration.
    CONTEXT: Developed via TDD. Assumes immutable config.
    ... (PRE/PARAMS/RETURNS/EXCEPTIONS defined by tests) ...
    USAGE EXAMPLES:
      >>> cfg = ConfigData(...)
      >>> perform_action(cfg, "item-001") # Test case
      True
    """
    assert isinstance(item_id, str) and item_id, "Internal check: item_id valid"
    action_log = log.bind(item_id=item_id)
    action_log.info("action_started")
    # ... Refactored logic derived from passing multiple tests ...
    result = True
    action_log.info("action_completed", success=result)
    return result

# 4. Write Next Test (RED) - e.g., test_perform_action_failure()
```### 5.3 Footer
```python
"""
## LIMITATIONS & RISKS: [Identified during TDD/Refactoring]
## REFINEMENT IDEAS: [Ideas for next TDD cycles or future refactoring]
## ZEROTH LAW COMPLIANCE:
# Framework Version: 2025-04-08-tdd
# ... (Score, Penalties, Timestamp) ...
"""
```

---

## 6. AUTOMATION

### 6.1 Tools
Employ this mandatory toolset, configured via `pyproject.toml` and orchestrated by `pre-commit` and CI, supporting the TDD workflow with **`poetry`** environments and Python 3.13+:\n\n1.  **`poetry`**: Required for dependency management, environment creation, and running scripts within the managed environment.\n2.  **`pre-commit`**: Manages Git hooks for automated checks (lint, type, format, etc.).\n3.  **`ruff`**: Primary tool for linting, formatting, import sorting, doc checks.\n4.  **`mypy`**: Static type checker (`--strict` mode).\n5.  **`pylint` (Targeted Usage)**: Used exclusively for code duplication detection (`R0801`).\n6.  **`pytest`**: **Core testing framework** used continuously during the TDD Red-Green-Refactor cycle. Includes coverage via `pytest-cov`.\n7.  **`structlog`**: Required runtime library for structured JSON logging.\n8.  **`autoinit`** (Optional): Manages `__init__.py` files.

### 6.2 Environment & Dependency Workflow (Using Poetry)

1.  **Define Dependencies:** Specify runtime dependencies in `pyproject.toml` under `[tool.poetry.dependencies]` and development dependencies under appropriate groups like `[tool.poetry.group.dev.dependencies]`.
2.  **Install Environment & Dependencies:** Navigate to the project root (containing `pyproject.toml`) and run `poetry install --all-extras` (or specify groups like `--with dev`). This command:
    *   Reads `pyproject.toml`.
    *   Resolves dependencies using `poetry.lock` (creating it if it doesn't exist).
    *   Creates a virtual environment (location configurable via `poetry config virtualenvs.path` or `poetry config virtualenvs.in-project true`).
    *   Installs all specified dependencies into the virtual environment.
3.  **Activate Environment:**
    *   Use `poetry shell` to spawn a new shell session with the virtual environment activated.
    *   Alternatively, if configured with `virtualenvs.in-project true`, activate directly: `source .venv/bin/activate` (adjust path if needed).
4.  **Run Commands:** Execute tools and scripts within the managed environment using `poetry run <command>` (e.g., `poetry run pytest`, `poetry run mypy .`). This ensures the correct dependencies and Python interpreter are used without needing to manually activate the shell.
5.  **Updating Dependencies:**
    *   To update a specific package: `poetry update <package_name>`
    *   To update all dependencies according to `pyproject.toml` constraints: `poetry update`
    *   Commit the updated `poetry.lock` file after updates.
6.  **CI:** The CI pipeline should install `poetry`, then use `poetry install` to set up the environment, and `poetry run` for executing checks, tests, and builds.

### 6.3 Project Structure Example (Conceptual)
```
project_root/
│
├── .github/             # CI/CD workflows (e.g., GitHub Actions using Poetry)
│   └── workflows/
│       └── ci.yml
│
├── frameworks/          # Core framework definitions
│   └── python/
│       └── ZerothLawAIFramework-*.md
│
├── scripts/             # Helper scripts (run via `poetry run`)
│   └── ...
│
├── src/                 # Source code for the project/tool
│   └── project_package/ # The main Python package
│       ├── __init__.py
│       └── ...
│
├── tests/               # Tests for the project/tool
│   ├── __init__.py
│   └── ...
│
├── .gitignore           # Standard Git ignore file
├── .pre-commit-config.yaml # Pre-commit hook definitions (using `poetry run` where needed)
├── pyproject.toml       # Defines project metadata, dependencies, tool configs (Poetry)
├── poetry.lock          # Exact dependency versions (Managed by Poetry)
└── README.md            # Project documentation (using Poetry setup instructions)
```

### 6.4 Pre-Commit Configuration
*   Hooks requiring project dependencies (like `mypy`, `pylint`, custom scripts) should use `language: system` and invoke the tool via `entry: poetry run <command>`.
*   Ensure `pre-commit install` is run after `poetry install`.

### 6.5 Example CI Pipeline (GitHub Actions with Poetry)
```yaml
name: Python CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.13"] # Test against target Python version

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        virtualenvs-create: true # Let Poetry manage the venv
        virtualenvs-in-project: true # Optional: Keep venv in project dir
        installer-parallel: true

    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v4
      with:
        path: .venv
        key: venv-${{ runner.os }}-${{ steps.setup-python.outputs.python-version }}-${{ hashFiles('**/poetry.lock') }}

    - name: Install dependencies
      if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
      run: poetry install --no-interaction --no-root --all-extras # Install deps without project root

    - name: Install project
      run: poetry install --no-interaction --all-extras # Install the project itself

    - name: Run linters and formatters (via pre-commit or poetry run)
      run: poetry run pre-commit run --all-files --show-diff-on-failure
      # Or run tools individually:
      # run: |
      #   poetry run ruff check .
      #   poetry run ruff format --check .
      #   poetry run mypy .

    - name: Run tests
      run: poetry run pytest --cov=src --cov-report=xml # Or your specific test command

    # Optional: Upload coverage report
    # - name: Upload coverage reports to Codecov
    #   uses: codecov/codecov-action@v4
    #   with:
    #     token: ${{ secrets.CODECOV_TOKEN }} # Required for private repos
    #     fail_ci_if_error: true
```

## 7. FIXING PYTEST IMPORT ERRORS (with Poetry)

Common causes for `ImportError` when running `pytest` using `poetry run pytest`:

1.  **Project Not Installed:** Ensure `poetry install` has been run successfully. This installs the project itself in editable mode within the virtual environment.
2.  **Incorrect `testpaths`:** Verify `[tool.pytest.ini_options].testpaths` in `pyproject.toml` points to your test directory (e.g., `tests`).
3.  **Missing `__init__.py` Files:** Ensure necessary `__init__.py` files exist in your source directories (`src/your_package`) and test directories (`tests/`) to allow Python to recognize them as packages.
4.  **Incorrect `PYTHONPATH` (Less Common with Poetry):** `poetry run` usually handles the path correctly. If issues persist, investigate potential `PYTHONPATH` conflicts, although this is unlikely if using `poetry run`.

---

## 8. FRAMEWORK EVOLUTION
*This framework is a living document.*
