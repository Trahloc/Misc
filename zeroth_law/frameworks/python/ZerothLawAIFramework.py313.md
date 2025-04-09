# Zeroth Law: AI-Driven Python Code Quality Framework

**Co-Author**: Trahloc colDhart
**Version**: 2025-04-09T12:52:30+00:00

---

## 1. PURPOSE
Design a minimal, AI-first framework for Python code quality targeting **Python 3.13+** and **`poetry`** for environment and dependency management. This framework serves as the primary rulebook for an **AI developer**, with human oversight limited to strategic direction and ambiguity resolution. By mandating **Test-Driven Development (TDD)** and **Data-Driven Testing (DDT)** alongside enforcing clarity, simplicity, modular design, opinionated standards, and comprehensive automated checks, this framework ensures every component is demonstrably correct, immediately understandable by AI or human maintainers, verifiable, and optimized for continuous, AI-led evolution. The goal is a codebase where any compliant AI developer can contribute effectively with minimal external context.

## 2. APPLICATION & WORKFLOW
All new or modified code **must** be developed by the AI developer following the strict **Test-Driven Development (TDD)** cycle (Red-Green-Refactor), leveraging **Data-Driven Testing (DDT)** techniques where applicable. Code must pass all associated tests and automated guideline checks before merging into the main development branch (`dev`).

Automated checks (`ruff`, `mypy`, `pylint R0801`, `pytest`) via `pre-commit` and CI act as the primary, non-negotiable feedback loop, applying requirements based on `pyproject.toml` configurations. Merging is blocked until compliance is achieved. The AI developer is expected to use this automated feedback to iteratively correct code. If automated checks present multiple failures, the recommended fixing order is: **Format (`ruff format`) -> Type/Lint (`mypy`, `ruff check`) -> Tests (`pytest`)**.

Development **must** utilize **`poetry`** environments defined by `pyproject.toml` and managed via `poetry install`/`poetry run`. The human collaborator provides high-level goals and resolves only true ambiguities or AI development loops, not routine code review. The target end-state includes a `stable` branch where *all* warnings are treated as errors, representing a higher quality gate.

## 3. GUIDING PRINCIPLES

1.  **Test-Driven Development (TDD) First**: **Require** all production code to be driven by tests. Follow the strict **Red-Green-Refactor** cycle: write a failing test (Red), write the minimum code to pass the test (Green), then improve the code while keeping tests green (Refactor). This ensures inherent testability, verifiable correctness, and drives emergent design.
2.  **Data-Driven Testing (DDT) Efficiency**: **Require** leveraging Data-Driven Testing techniques, primarily using `pytest.mark.parametrize`, when testing the same logic path against multiple input/output variations. Separate test data from test logic for clarity and maintainability, especially for complex inputs (see 4.2). This complements TDD by efficiently handling variations.
3.  **Single Responsibility & Clear API Boundaries**: Keep components focused on one reason to change, making them easier to test and reason about via TDD/DDT. Expose minimal necessary interfaces via `__init__.py` (managed by `autoinit` if desired). Isolation simplifies AI reasoning and independent refinement.
4.  **First Principles Simplicity**: Solve problems directly with minimal complexity, driven by the need to pass the current test. Prefer clear Python 3.13+ features over intricate abstractions. Minimalism reduces error surface and boosts AI refactoring confidence within the TDD cycle.
5.  **Leverage Existing Libraries (Configured Enforcement & No Reinvention)**:
    *   Utilize stable, well-maintained PyPI packages compatible with Python 3.13+ (`poetry` managed). Treat vetted libraries as reliable components.
    *   **Configure standard tools** (`ruff`, `mypy`, `pytest`, `pylint`) via `pyproject.toml` according to ZL specifications. Passing checks from these **configured tools currently serves as the primary enforcement mechanism** for corresponding ZL principles. These tools act as essential "consultants" providing automated feedback.
    *   **Strictly forbid** modifying the internal behavior of third-party libraries at runtime (monkey-patching). Interact only via documented public APIs.
    *   **No Reinvention:** Do not reimplement functionality already provided by the Python standard library or mandated tools unless absolutely necessary and justified. Custom checks (e.g., AST analysis within the ZL tool) are *not* part of the current implementation and require strong justification for future consideration if a core ZL principle cannot be measured by standard tooling.
    *   *(Future Goal: The Zeroth Law tool may eventually act as a higher-level arbiter integrating results, but current compliance relies on the direct, configured output of the mandated tools.)*
6.  **Don't Repeat Yourself (DRY)**: During the Refactor step of TDD, consolidate logic identified via testing or analysis (`pylint R0801`). Eliminate duplication to reduce debt and ensure consistent updates. Apply DRY to test code as well (aided by DDT).
7.  **Self-Documenting Code & Explicit Rationale**:
    *   Use descriptive names (`what`). Code clarity is paramount for AI comprehension.
    *   Employ docstrings/comments to explain the *why* (rationale, context) only for **non-obvious logic**. Assume an AI reader understands Python 3.13+ syntax.
    *   **Triggers for Rationale Comments:** Add comments when the code implements: (a) Workarounds for external library issues, (b) Logic chosen after other attempts failed (documenting the dead-end), (c) Complex algorithms/state management deviating significantly from simple approaches. The goal is to prevent future AI developers from repeating exploration or encountering the same pitfalls.
    *   Documentation follows implementation within the TDD cycle.
8.  **Consistent Style & Idiomatic Usage**: Apply uniform coding style enforced by `ruff format` (project config) and `ruff check`, along with modern type hints (Python 3.13+) and idioms. Style checks are a core part of the automated feedback loop.
9.  **Comprehensive Testing & Automation (Inherent via TDD/DDT)**: TDD/DDT naturally produce high test coverage for correctness and regression prevention. Automate checks (`ruff`, `mypy`, `pylint R0801`, `pytest`) via `pre-commit` and CI as essential, non-negotiable feedback mechanisms supporting the AI developer's workflow.
10. **Explicit Error Handling & Reliable Resource Management**: Design tests that cover expected error conditions. Implement specific exception handling and ensure resources (files, connections, locks) are reliably released via context managers (`with`) or `try...finally`, verified by tests covering success and failure paths.
11. **AI-Led Continuous Refactoring (TDD Refactor Step Scope)**:
    *   Embrace code evolution within the **Refactor** step of the TDD cycle.
    *   **Baseline (Mandatory):** Clean up code added/modified in the Green step to meet all static analysis requirements (`ruff`, `mypy`, `pylint R0801`), format correctly, and adhere to clarity/simplicity principles.
    *   **Incremental Improvement:** Proactively make immediate, localized improvements (simplify conditions, improve names, apply Python 3.13 idioms, extract small helpers) related to the code just touched.
    *   **Larger Refactoring:** Identify opportunities for significant architectural refactoring but typically defer implementation. Add ideas to `REFINEMENT IDEAS` (Sec 5.3) or initiate a *new* TDD cycle specifically for that refactoring, driven by new tests proving its value. The AI should prioritize completing the current cycle cleanly over attempting deep refactoring mid-cycle.
12. **Design for Concurrency Safety (When Required & Testable)**: If concurrency is needed, use TDD to drive the design. Write tests that attempt to expose potential race conditions or safety issues (acknowledging difficulty). Implement solutions using appropriate mechanisms (e.g., `asyncio`, `threading`) driven by tests. Protect shared state with synchronization primitives. Prevent race conditions and document the concurrency model. (See Sec 4.7).
13. **Adhere to Filesystem Standards (XDG & Tooling Configuration)**:
    *   **Runtime:** Applications **must** store user-specific files according to the XDG Base Directory Specification (using environment variables like `$XDG_CONFIG_HOME`). Write tests verifying correct file placement.
    *   **Tooling:** Development/CI tooling **must**, where configurable, be set up to use XDG-compliant directories for caches/config, enforced via `pyproject.toml` and only rely on environment variables as a last resort.

---

## 4. KEY METRICS & PRACTICES

### 4.1 Test-Driven Development (TDD) Workflow
*   **Red-Green-Refactor Cycle:** **Mandatory** adherence for all production code changes.
*   **Test Granularity:** Write small, focused tests targeting specific behaviors or requirements. Use distinct `test_` functions for different behaviors/paths.
*   **Minimum Viable Code (Green Step):** Implement only the code necessary to pass the current failing test before refactoring.
*   **Refactoring Scope (Refactor Step):** Perform baseline cleanup, ensure compliance with all automated checks for the changed code, and make localized improvements. Defer major refactoring (see Principle 11).
*   **Refactoring Safety Net:** Rely on the comprehensive test suite created during TDD/DDT to refactor code confidently.
*   **Test Coverage (Outcome):** High test coverage is an expected outcome of rigorous TDD/DDT. Verify logical coverage via `pytest --cov` and enforce `fail_under` in CI.
*   **AI Feedback Priority:** Address automated check failures in the order: Format -> Type/Lint -> Tests.

### 4.2 Data-Driven Testing (DDT) Practices
*   **When to Use:** **Strongly prefer** DDT (via `pytest.mark.parametrize`) over separate test functions when testing the *exact same logical path* with variations in *input data* or *expected output* (e.g., boundary values, valid/invalid states, different formats).
*   **Separate Functions:** Use separate `test_` functions when testing *distinctly different behaviors*, *control flow paths*, or *failure modes*, even if within the same production function. This clarifies test intent.
*   **Data Separation:** Keep test data separate from test logic. Use tuples/lists within `@pytest.mark.parametrize` for simple cases.
*   **External Test Data:** For complex inputs (e.g., multi-line strings, structured data, source code snippets), **require** storing test data in separate files (e.g., in `tests/test_data/`). Load using mechanisms like `pathlib.Path.read_text()`. This improves readability and maintainability. Consider simple formats like `.txt`, `.yaml`, or `.json` for these files.

### 4.3 AI Quality & Readability
*   **Context Independence**: Aim for components/modules readable and testable with minimal external context.
*   **AI Insight Documentation**: Docstrings clarify purpose (defined by tests), rationale (context, per Principle 7 heuristics), pre/post-conditions, and usage. Include `USAGE EXAMPLES:` for non-trivial public APIs.
*   **Implementation Consistency**: >95% adherence to patterns enforced by tooling. Format with `ruff format`, lint/style/docs with `ruff check`.

### 4.4 File Organization
*   **File Purpose**: Header docstring specifies single responsibility (often corresponding to a test suite focus).
*   **File Size**: Target < 300 lines (excluding docstrings/comments), encouraged by TDD/DDT's focus on small, testable units.
*   **Module Interface**: Strict exposure via `__init__.py` (use `autoinit` if desired).

### 4.5 Code Quality
*   **Semantic Naming**: Descriptive identifiers understandable by AI without context.
*   **Function Size**: Target < 30 lines (excluding docstrings/comments), naturally promoted by TDD/DDT.
*   **Function Signature**: ≤ 4 parameters; use `@dataclass(frozen=True)`/TypedDicts/Pydantic models for more.
*   **Cyclomatic Complexity**: Prefer < 8 (via `ruff mccabe`). Keep units simple for testability.
*   **Code Duplication**: Eliminate duplication during the Refactor TDD step (verify via `pylint R0801`).
*   **Mandatory Type Annotation**: **Require** explicit, modern (Python 3.13+) type hints. Enforce with `mypy --strict`.
*   **Minimize Mutable Global State**: Avoid module-level mutable variables. Pass state explicitly.
*   **Favor Immutability (Mandatory Practice)**:
    *   **Universally prefer** immutable data structures. Mutability requires strong justification.
    *   **Require** using `@dataclass(frozen=True)` for custom data structures unless mutation is essential.
    *   **Require** using `typing.Final` for module/class level constants (enforced by `mypy`).
    *   **Prefer** tuples over lists for fixed collections.
    *   **Prefer** functional style (return new values) over in-place modification.
    *   **Require** writing tests specifically verifying the absence of unintended side effects for functions intended to be pure.

### 4.6 Error Reporting & Logging
*   **Test Error Conditions:** Write specific tests for expected failure modes and exception handling.
*   **Traceability**: Exceptions include context. Use chaining/groups appropriately.
*   **Logging Library:** **Require** using **`structlog`**.
*   **Logging Configuration & Format:**
    *   Configure `structlog` with processor pipelines.
    *   **Require** using `structlog.processors.JSONRenderer()` for output in CI/testing/production environments (for machine parsing).
    *   **Recommend** using `structlog.dev.ConsoleRenderer(colors=True)` for local development (for human readability). Select renderer based on environment context during `structlog.configure()`.
*   **Logging Content:** Include standard fields (`timestamp`, `level`, `event`, `logger`) and relevant context (`structlog.contextvars`).
*   **Logging Testing:** **Require** testing critical log outputs using `structlog.testing.capture_logs()`. Assert on the presence and values of key fields in the captured log entries.
    ```python
    # Example Test:
    # import structlog
    # def test_action_logs_completion():
    #     with structlog.testing.capture_logs() as captured_logs:
    #         perform_action(...) # Function that logs
    #     assert len(captured_logs) > 0
    #     completion_log = next((l for l in captured_logs if l["event"] == "action_completed"), None)
    #     assert completion_log is not None
    #     assert completion_log["success"] is True
    ```
*   **Exception Management**: Raise specific exceptions based on tested failure conditions. Avoid broad `except Exception:`. Enforce with `ruff` rules (e.g., `tryceratops`, `flake8-builtins`).
*   **No Internal Fallbacks**: Fail explicitly based on test expectations.

### 4.7 Data Validation & Parsing
*   **External Data Handling:** **Require** **Pydantic** models for defining, parsing, and validating non-trivial external data structures (e.g., API responses, config files). Write tests covering valid and invalid data scenarios using these models.
*   **Runtime Validation vs. Assertions:** Use Pydantic/explicit checks for *external* inputs (tested); use `assert` for *internal* invariants identified and verified during TDD (see 4.8).

### 4.8 Defensive Programming & Assertions
*   **Strategic Assertions**: Use `assert` liberally for internal invariants, pre-conditions, and post-conditions identified and verified during the TDD Refactor step. Assertions document assumptions the AI developer makes about internal state.
*   **Invariant Checks**: Assert conditions that tests assume must always hold true within a specific scope.
*   **Assertion Density**: Guided by test logic and invariants discovered during development. Err on the side of more assertions for internal checks.
*   **Verbose Testing**: Run `pytest -vv`. Ensure assertion messages clearly explain the invariant violation to aid AI debugging of test failures.

### 4.9 Concurrency and Resource Management
*   **(Applies if project requires concurrency & driven by tests)**
*   **Test Concurrency Issues:** Write tests specifically designed to provoke race conditions or verify synchronization if possible (can be challenging). Test resource handling under concurrent access if applicable.
*   **Use Synchronization Primitives**: Protect necessary shared state with appropriate mechanisms (e.g., `asyncio.Lock`, `threading.Lock`), driven by failing tests where feasible.
*   **Reliable Resource Management**: Always use context managers (`with`) or `try...finally` to ensure resources (files, network connections, locks) are released reliably. Test both success and failure paths for resource release.
*   **Document Concurrency Model**: Specify thread/async safety and strategy (`stateless`, `synchronized`, etc.) in relevant docstrings or `NOTES.md`.
*   **Verify External Calls**: Ensure external library interactions are concurrency-safe or protected appropriately.
*   **`asyncio` Best Practices (if using `asyncio`):** Apply requirements (avoid blocking calls, use `async with/for`, manage tasks correctly) driven by tests for async functionality.

### 4.10 Commit Message Standards
*   **Conventional Commits:** **Require** adherence to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification for all Git commit messages. The AI developer **must** generate compliant messages, often corresponding to TDD cycles (e.g., `feat: implement X`, `test: add test for Y`, `refactor: improve Z`).

### 4.11 Versioning Scheme
*   **Epoch/Date Versioning:** **Require** utilizing a strictly increasing version scheme based on time (e.g., `YYYYMMDD.HHMMSS` or Unix epoch seconds). Define in `pyproject.toml` (`[tool.poetry.version]`). This deterministic scheme is suitable for AI management and relies on the comprehensive TDD suite for compatibility assurance between versions.

### 4.12 Validation Metrics (Outcomes & Enforcements)
*   **Test Coverage**: High coverage (>95% logical) is an expected outcome of TDD/DDT. Verify via `pytest --cov` and enforce with `fail_under` threshold in CI.
*   **Type Coverage**: 100% (enforced via `mypy --strict`).
*   **Code Duplication**: Zero warnings from `pylint R0801` (addressed during Refactor step).
*   **Documentation Coverage**: 100% public APIs (`ruff D` rules). Documentation written after passing tests, before/during Refactor.
*   **Docstring Style Compliance**: Adherence to convention (`ruff D` rules).
*   **Docstring Example Coverage**: **Require** `USAGE EXAMPLES:` for non-trivial public APIs.
*   **Runtime Type Guards**: **Require** validation of external inputs via Pydantic/explicit checks, driven by tests.

### 4.13 Dependencies & Environment
*   **Dependency Specification:** Define runtime dependencies in `pyproject.toml` under `[tool.poetry.dependencies]` and development dependencies under appropriate groups (e.g., `[tool.poetry.group.dev.dependencies]`). AI developer manages this via `poetry add/remove/update`.
*   **Environment Management:** **Require** use of **`poetry`** for managing dependencies and virtual environments based on `pyproject.toml` and `poetry.lock`.
*   **Vetting**: Prefer standard libraries and reputable PyPI packages compatible with Python 3.13+. Check licenses.
*   **Justification**: Document reasons for significant third-party dependencies in `NOTES.md` or relevant docstrings.
*   **Minimize Environment Assumptions**: Strive for OS consistency. Document specific needs.

---

## 5. IN-FILE DOCUMENTATION PATTERN

Employ this consistent Header-Implementation-Footer structure in every Python file. Content should reflect Python 3.13+ features, Pydantic usage, `structlog` patterns, and TDD/DDT principles where applicable.

### 5.1 Header
```python
# FILE: <path/to/file.py>
"""
# PURPOSE: [Single responsibility, often derived from the initial test's goal.]
#          [Should be clear and concise for AI understanding.]
"""
# --- IMPORTS --- (Standard library, 3rd party, own packages)
import logging # Or specific imports
import structlog
# ... other imports ...

# --- CONSTANTS --- (Use typing.Final)
# Example: DEFAULT_TIMEOUT: Final[int] = 10

# --- LOGGING --- (Module-level logger)
log = structlog.get_logger()

# --- DATA STRUCTURES --- (Pydantic models, dataclasses)
# Example: @dataclass(frozen=True) class InputData: ...
```

### 5.2 Implementation Example (Conceptual TDD/DDT Flow)
```python
# Example function developed via TDD/DDT

def process_item(item_data: InputData, config: Config) -> OutputResult:
    """PURPOSE: Processes a validated item based on configuration.
    CONTEXT: Developed via TDD/DDT. Assumes immutable inputs. Handles X, Y, Z cases.
             Rationale for using Algorithm A documented below.
    PRE-CONDITIONS:
     - item_data is validated by Pydantic upstream.
     - config is a valid, immutable Config object.
    POST-CONDITIONS:
     - Returns an OutputResult object.
     - Raises SpecificError on failure condition ZZZ (tested).
    PARAMS:
     - item_data: The input data for the item.
     - config: Application configuration.
    RETURNS:
     - Result of the processing.
    EXCEPTIONS:
     - SpecificError: If condition ZZZ occurs.
    USAGE EXAMPLES:
     >>> item = InputData(...)
     >>> cfg = Config(...)
     >>> result = process_item(item, cfg) # Example from test_process_item_success
     >>> assert isinstance(result, OutputResult)
    """
    # --- ASSERTIONS (Internal Invariants) ---
    assert config.is_valid(), "Internal check: Config should be valid here."
    proc_log = log.bind(item_id=item_data.id)
    proc_log.info("processing_started")

    # --- CORE LOGIC (Driven by Tests) ---
    # Rationale: Using Algorithm A because initial tests showed Algorithm B
    # failed under high load conditions (see NOTES.md section YYYY-MM-DD).
    try:
        # ... Minimum code to pass tests, refactored for clarity ...
        result_value = _perform_complex_step(item_data, config.setting)
        proc_log.debug("complex_step_completed", intermediate=result_value)

        if result_value < 0:
             # Test case test_process_item_negative_result drives this path
             raise SpecificError("Negative result encountered", item_id=item_data.id)

        final_result = OutputResult(id=item_data.id, value=result_value)
        proc_log.info("processing_completed", success=True)
        return final_result

    except Exception as e: # Catch specific expected exceptions if possible
        proc_log.error("processing_failed", exc_info=True)
        # Re-raise or handle as defined by specific failure tests
        raise # Or raise specific error tested for

# --- HELPER FUNCTIONS --- (If extracted during refactoring)
def _perform_complex_step(data: InputData, setting: str) -> int:
    # Developed via its own TDD cycle if sufficiently complex
    ...
```

### 5.3 Footer
```python
"""
## LIMITATIONS & RISKS: [Identified during TDD/Refactoring, e.g., external system dependency]
## REFINEMENT IDEAS: [Ideas for next TDD cycles or future refactoring, e.g., 'Explore caching results']
## ZEROTH LAW COMPLIANCE:
# Framework Version: 2025-04-09T12:52:30+00:00
# Compliance results populated by the Zeroth Law tool based on automated checks.
# Score: [e.g., 100]
# Penalties: [e.g., None]
# Timestamp: [e.g., 2025-04-09T15:00:00+00:00]
"""

```

---

## 6. AUTOMATION

### 6.1 Tools
Employ this mandatory toolset, configured via `pyproject.toml` (within the project directory) and orchestrated by `pre-commit` and CI, supporting the AI developer's TDD/DDT workflow with **`poetry`** environments and Python 3.13+:

1.  **`poetry`**: Required for dependency management, environment creation, and running scripts (`poetry run ...`). AI developer manages dependencies via `poetry add/remove/update`.
2.  **`pre-commit`**: Manages Git hooks executing automated checks. Uses the project-specific `.pre-commit-config.yaml`.
3.  **`ruff`**: Primary tool for linting (`ruff check`), formatting (`ruff format`), import sorting, and docstring checks (`D` rules). Configured in `pyproject.toml [tool.ruff]`.
4.  **`mypy`**: Static type checker. **Must** be run with `--strict` flag. Configured in `pyproject.toml [tool.mypy]`.
5.  **`pylint` (Targeted Usage)**: Used exclusively for code duplication detection (`R0801`). Invoke via `poetry run pylint --disable=all --enable=R0801 <targets>`.
6.  **`pytest`**: **Core testing framework** used continuously during the TDD/DDT Red-Green-Refactor cycle. Includes coverage via `pytest-cov`. Configured in `pyproject.toml [tool.pytest.ini_options]`.
7.  **`structlog`**: Required runtime library for structured JSON/Console logging (see 4.6).
8.  **`autoinit`** (Optional): Manages `__init__.py` files if desired.

### 6.2 Environment & Dependency Workflow (Using Poetry)
This workflow is typically executed by the AI developer or automation scripts:

1.  **Define/Update Dependencies:** AI adds/removes/updates packages in `pyproject.toml` using `poetry add/remove/update`.
2.  **Install Environment & Dependencies:** In project root: `poetry install --all-extras` (or specific groups). Creates `.venv` (if configured) and installs based on `poetry.lock`.
3.  **Run Commands:** Execute tools via `poetry run <command>` (e.g., `poetry run pytest`, `poetry run mypy .`, `poetry run ruff check .`). This ensures execution within the correct environment.
4.  **CI:** CI pipeline uses `poetry install` to set up the environment and `poetry run` for all checks, tests, and builds.

### 6.3 Project Structure Example (Conceptual)
*(Assumes project root contains `pyproject.toml`)*
```
project_root/
│
├── .github/             # CI/CD workflows (e.g., GitHub Actions using Poetry)
│   └── workflows/
│       └── ci.yml
│
├── frameworks/          # Optional: ZL Framework definitions for reference
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
├── tests/               # Tests (following TDD/DDT)
│   ├── __init__.py
│   └── test_data/       # External data files for DDT
│   └── ...
│
├── .gitignore           # Standard Git ignore file
├── .pre-commit-config.yaml # PROJECT-SPECIFIC pre-commit hooks (uses `poetry run`)
├── pyproject.toml       # Defines project metadata, dependencies, tool configs (Poetry)
├── poetry.lock          # Exact dependency versions (Managed by Poetry)
├── README.md            # Project documentation
├── NOTES.md             # Decision log & rationale (See Sec 8)
└── TODO.md              # High-level goals & task tracking (See Sec 8)

```
*(Note: For monorepos where Git root != project root, custom Git hooks managed by the ZL tool might be needed to invoke the project-specific `.pre-commit-config.yaml`.)*

### 6.4 Pre-Commit Configuration (`.pre-commit-config.yaml`)
*   **Location:** Must reside in the project root (alongside `pyproject.toml`).
*   **Execution:** Hooks requiring project dependencies (`mypy`, `pytest`, `pylint`, custom scripts) **must** use `language: system` and `entry: poetry run <command>`.
*   **Activation:** Ensure Git hooks are active (e.g., via `pre-commit install --config .pre-commit-config.yaml -t pre-commit -t pre-push` or ZL tool's hook management).

### 6.5 Example CI Pipeline (GitHub Actions with Poetry)
```yaml
name: Python CI (Zeroth Law)

on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.13"] # Target Python version

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        virtualenvs-create: true
        virtualenvs-in-project: true # Recommended for caching
        installer-parallel: true

    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v4
      with:
        path: .venv
        key: venv-${{ runner.os }}-${{ steps.setup-python.outputs.python-version }}-${{ hashFiles('**/poetry.lock') }}

    - name: Install dependencies (including dev)
      run: poetry install --no-interaction --all-extras

    # Run pre-commit hooks (preferred method)
    - name: Run pre-commit checks (Format, Lint, Types, etc.)
      run: poetry run pre-commit run --all-files --show-diff-on-failure --config .pre-commit-config.yaml

    # OR Run checks individually (Example if not using pre-commit for all in CI)
    # - name: Check Formatting
    #   run: poetry run ruff format --check .
    # - name: Run Linter
    #   run: poetry run ruff check .
    # - name: Run Type Checker
    #   run: poetry run mypy . --strict
    # - name: Check Duplication
    #   run: poetry run pylint --disable=all --enable=R0801 src tests

    - name: Run Tests with Coverage
      run: poetry run pytest --cov=src --cov-report=xml --cov-fail-under=95 # Adjust path & threshold

    # Optional: Upload coverage reports
    # - name: Upload coverage to Codecov
    #   uses: codecov/codecov-action@v4
    #   with:
    #     token: ${{ secrets.CODECOV_TOKEN }}
    #     files: coverage.xml # Ensure file name matches pytest output
    #     fail_ci_if_error: true
```

## 7. COMMON ISSUES & FIXES

### 7.1 `pytest` Import Errors (with Poetry)
Common causes for `ImportError` when using `poetry run pytest`:
1.  **Project Not Installed:** Ensure `poetry install` completed successfully (installs project in editable mode).
2.  **Incorrect `testpaths`:** Verify `[tool.pytest.ini_options].testpaths` in `pyproject.toml` points to `tests`.
3.  **Missing `__init__.py` Files:** Ensure necessary `__init__.py` exist in source (`src/your_package`) and test directories (`tests/`) for package recognition. `autoinit` can manage this.
4.  **Incorrect `PYTHONPATH` (Unlikely with `poetry run`):** `poetry run` usually handles this. Investigate only if other causes are ruled out.

### 7.2 Pre-Commit Failures
*   **Formatters Failing on Change:** Tools like `ruff format` *will* cause `pre-commit` to fail if they modify files. **Solution:** Configure IDE (e.g., VS Code/Cursor with Ruff extension) for format-on-save. The `pre-commit` hook then acts as a safety net, ensuring compliance if IDE formatting fails or is missed. It should pass without modifying files during commit if format-on-save is working.
*   **Hook Configuration Errors:** Ensure paths in `.pre-commit-config.yaml` are correct relative to the project root and that `poetry run` is used for tools needing the project environment.

---

## 8. PROJECT KNOWLEDGE MANAGEMENT
To ensure context is preserved for future AI and human maintainers:

*   **`NOTES.md`:** Maintain a chronological log of significant technical decisions, rationale for framework choices, troubleshooting discoveries, and architectural changes. Use timestamps (`date --iso-8601=seconds`).
*   **`TODO.md`:** Track high-level project goals, milestones, and larger refactoring tasks identified but deferred.
*   **Inline `TODO:` Comments:** Use for small, actionable items directly related to the code section. Consider using a script (potentially via `pre-commit` or manually) to aggregate these into a central `CODE_TODO.md` dashboard for visibility.
*   **Commit History:** Leverage Conventional Commits (Principle 4.10) for a meaningful, navigable history.

---

## 9. ONBOARDING LEGACY CODE
Bringing existing, non-compliant code under Zeroth Law follows a structured, test-driven approach:

1.  **Characterization Tests:** Select a code segment. Write tests (`pytest`) that document its *current* behavior, inputs, and outputs, even if incorrect. These tests should initially pass.
2.  **Identify ZL Violation:** Choose a specific ZL principle the code violates (e.g., >30 lines, untyped, lacks tests for error cases).
3.  **Targeted TDD Cycle:**
    *   **Red:** Write a *new* test (or modify a characterization test) designed to fail now but pass once the specific ZL violation is fixed.
    *   **Green:** Make the *minimum change* to the code to pass the new test, ensuring original characterization tests still pass (unless behavior *must* change).
    *   **Refactor:** Clean the modified code per Principle 11 / Section 4.1, ensuring all tests pass and automated checks (`ruff`, `mypy`) are satisfied.
4.  **Iterate:** Repeat steps 2-3, incrementally refactoring the code towards full ZL compliance, guided by tests and automated checks. Prioritize refactoring code that needs functional changes first, or start with less critical modules.

---

## 10. FRAMEWORK EVOLUTION
*This framework is a living document.* It will adapt as tools evolve and best practices emerge, guided by the core principles of TDD, automation, and AI-centric development. Changes will be documented in `NOTES.md`.
