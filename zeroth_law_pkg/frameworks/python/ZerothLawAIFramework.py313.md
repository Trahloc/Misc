# Zeroth Law Framework (ZLF): AI-Driven Python Code Quality

**Co-Author**: Trahloc colDhart
**Version**: 2025-04-18T14:29:24+08:00 # AI run `date --iso-8601=seconds` to update

---

## Table of Contents

*   [Glossary & Acronyms](#glossary--acronyms)
*   [1. PURPOSE](#1-purpose)
*   [2. APPLICATION & WORKFLOW](#2-application--workflow)
*   [3. GUIDING PRINCIPLES](#3-guiding-principles)
*   [4. KEY METRICS & PRACTICES](#4-key-metrics--practices)
    *   [4.1 Test-Driven Development (TDD) Workflow](#41-test-driven-development-tdd-workflow)
    *   [4.2 Data-Driven Testing (DDT) Practices](#42-data-driven-testing-ddt-practices)
    *   [4.3 AI Quality & Readability](#43-ai-quality--readability)
    *   [4.4 File Organization](#44-file-organization)
    *   [4.5 Code Quality](#45-code-quality)
    *   [4.6 Error Reporting & Logging](#46-error-reporting--logging)
    *   [4.7 Data Validation & Parsing](#47-data-validation--parsing)
    *   [4.8 Defensive Programming & Assertions](#48-defensive-programming--assertions)
    *   [4.9 Concurrency and Resource Management](#49-concurrency-and-resource-management)
    *   [4.10 Commit Message Standards](#410-commit-message-standards)
    *   [4.11 Versioning Scheme](#411-versioning-scheme)
    *   [4.12 Validation Metrics (Outcomes & Enforcements)](#412-validation-metrics-outcomes--enforcements)
    *   [4.13 Dependencies & Environment](#413-dependencies--environment)
*   [5. IN-FILE DOCUMENTATION PATTERN](#5-in-file-documentation-pattern)
    *   [5.1 Header](#51-header)
    *   [5.2 Implementation Example](#52-implementation-example-conceptual-tddddt-flow)
    *   [5.3 Footer](#53-footer)
*   [6. AUTOMATION](#6-automation)
    *   [6.1 Tools (Consultants)](#61-tools-consultants)
    *   [6.2 Environment & Dependency Workflow (Using `uv`)](#62-environment--dependency-workflow-using-uv)
    *   [6.3 Project Structure Example (Conceptual)](#63-project-structure-example-conceptual)
    *   [6.4 Pre-Commit Configuration (`.pre-commit-config.yaml`)](#64-pre-commit-configuration-pre-commit-configyaml)
    *   [6.5 Example CI Pipeline (GitHub Actions with `uv`)](#65-example-ci-pipeline-github-actions-with-uv)
*   [7. COMMON ISSUES & FIXES](#7-common-issues--fixes)
    *   [7.1 `pytest` Import Errors (with `uv`)](#71-pytest-import-errors-with-uv)
    *   [7.2 Pre-Commit Failures](#72-pre-commit-failures)
*   [8. PROJECT KNOWLEDGE MANAGEMENT](#8-project-knowledge-management)
*   [9. ONBOARDING LEGACY CODE](#9-onboarding-legacy-code)
*   [10. FRAMEWORK EVOLUTION](#10-framework-evolution)

---

## Glossary & Acronyms

*   **AI Developer**: The Artificial Intelligence entity responsible for writing and modifying code according to this framework.
*   **CI**: Continuous Integration. Automated processes for building, testing, and validating code changes.
*   **Consultant Model**: The concept where the ZLT orchestrates specialized tools (like `ruff`, `mypy`, `pytest`, fuzzers) to gather specific compliance data, treating them as expert "consultants".
*   **DDT**: Data-Driven Testing. A testing technique where test logic is separated from test data, often using parameterization to run the same logic with multiple inputs/outputs. (See Section [4.2](#42-data-driven-testing-ddt-practices)).
*   **Framework**: Refers to this entire document and the system it describes (used interchangeably with ZLF).
*   **Programmatic Ground Truth**: The principle that ZLP compliance is determined by the deterministic, repeatable results of executing automated tools (orchestrated by ZLT), minimizing subjective judgment.
*   **TDD**: Test-Driven Development. A development methodology where tests are written before the implementation code. Involves the Red-Green-Refactor cycle. (See Section [4.1](#41-test-driven-development-tdd-workflow)).
*   **ZLF**: **Zeroth Law Framework**. The complete set of principles, practices, standards, and automation defined in this document for AI-driven Python development.
*   **ZLT**: **Zeroth Law Tool**. The software tool designed to programmatically enforce the ZLF by orchestrating consultant tools and evaluating compliance. (See Section [1](#1-purpose), [6.1](#61-tools-consultants)).

---

## 1. PURPOSE

Design a minimal, AI-first **Zeroth Law Framework (ZLF)** for Python code quality targeting **Python 3.13+** and **`uv`** for environment and dependency management. This ZLF serves as the primary rulebook for an **AI developer**, with human oversight limited to strategic direction and ambiguity resolution.

The **Zeroth Law Tool (ZLT)** serves as the programmatic embodiment and enforcer of this framework. Its long-term vision is to orchestrate the execution of specialized 'consultant' tools (e.g., `ruff`, `mypy`, `pytest`, fuzzers; see Section [6.1](#61-tools-consultants)) based on ZLF rules and project configuration, providing a unified, deterministic judgment of compliance (the **Programmatic Ground Truth**). While ZLT development progresses towards this goal, adherence currently relies on both direct tool usage and ZLT's existing capabilities.

By mandating **Test-Driven Development (TDD)** (Section [4.1](#41-test-driven-development-tdd-workflow)) and **Data-Driven Testing (DDT)** (Section [4.2](#42-data-driven-testing-ddt-practices)) alongside enforcing clarity, simplicity, modular design, opinionated standards, and comprehensive automated checks, this ZLF ensures every component is demonstrably correct, immediately understandable by AI or human maintainers, verifiable, and optimized for continuous, AI-led evolution. The goal is a codebase where any compliant AI developer can contribute effectively with minimal external context, guided by ZLT's enforcement.

## 2. APPLICATION & WORKFLOW

All new or modified code **must** be developed by the AI developer following the strict **Test-Driven Development (TDD)** cycle (Red-Green-Refactor; see Section [4.1](#41-test-driven-development-tdd-workflow)), leveraging **Data-Driven Testing (DDT)** techniques where applicable (see Section [4.2](#42-data-driven-testing-ddt-practices)). Code **must** pass all associated tests and automated guideline checks (orchestrated or verified by ZLT) before merging into the main development branch (`dev`).

Automated checks (`ruff`, `mypy`, `pylint R0801`, `pytest` - the "consultant tools") via `pre-commit` (Section [6.4](#64-pre-commit-configuration-pre-commit-configyaml)) and CI (Section [6.5](#65-example-ci-pipeline-github-actions-with-uv)) act as the primary, non-negotiable feedback loop, applying requirements based on `pyproject.toml` configurations. Merging is blocked until compliance is achieved. The AI developer **must** use this automated feedback (ideally presented unifiedly by ZLT) to iteratively correct code. If automated checks present multiple failures, the **recommended** fixing order is: **Format (`ruff format`) -> Type/Lint (`mypy`, `ruff check`) -> Tests (`pytest`)**.

Development **must** utilize **`uv`** environments defined by `pyproject.toml` and managed via `uv venv`/`uv pip sync`/`uv run` (see Section [6.2](#62-environment--dependency-workflow-using-uv)). The human collaborator provides high-level goals and resolves only true ambiguities or AI development loops, not routine code review. The target end-state includes a `stable` branch where *all* warnings are treated as errors, representing a higher quality gate enforced by ZLT.

## 3. GUIDING PRINCIPLES

These principles form the foundation of the ZLF and guide the AI developer's actions. ZLT aims to enforce these programmatically where possible.

1.  **Test-Driven Development (TDD) First**: **Require** all production code to be driven by tests. Follow the strict **Red-Green-Refactor** cycle: write a failing test (Red), write the minimum code to pass the test (Green), then improve the code while keeping tests green (Refactor). This ensures inherent testability, verifiable correctness, and drives emergent design. (Enforced via `pytest` results and coverage checks by ZLT).
2.  **Data-Driven Testing (DDT) Efficiency**: **Require** leveraging DDT techniques, primarily using `pytest.mark.parametrize`, when testing the same logic path against multiple input/output variations. Separate test data from test logic for clarity and maintainability, especially for complex inputs (see Section [4.2](#42-data-driven-testing-ddt-practices)). This complements TDD by efficiently handling variations. (Verification relies on test structure analysis, potentially a future ZLT feature).
3.  **Single Responsibility & Clear API Boundaries**: Keep components focused on one reason to change, making them easier to test and reason about via TDD/DDT. Expose minimal necessary interfaces via `__init__.py` (managed by `autoinit` if desired). Isolation simplifies AI reasoning and independent refinement. (Partially assessed via complexity/size metrics).
4.  **First Principles Simplicity**: Solve problems directly with minimal complexity, driven by the need to pass the current test. **Prefer** clear Python 3.13+ features over intricate abstractions. Minimalism reduces error surface and boosts AI refactoring confidence within the TDD cycle. (Assessed via complexity/size metrics).
5.  **Minimize Backslash Escape Fragility**: **Strongly prefer** methods that avoid complex backslash (`\\`) escaping, especially when dealing with text parsing (e.g., command-line help output) or regular expressions that need to pass through the AI-Tool-File-Python toolchain. Backslashes are highly prone to misinterpretation or corruption at various layers (AI generation, tool application, shell interaction, file encoding, Python string literals, regex engine parsing). **Favor** procedural parsing (string methods, loops, conditional logic based on indentation or simple markers) over intricate regex patterns requiring heavy escaping. While standard escapes like `\\n` or `\\t` are acceptable, avoid relying on complex sequences (e.g., excessive escaping of regex metacharacters) where simpler, more direct parsing logic can achieve the same result. (Verification via code review and analysis of parsing logic complexity, potentially a future ZLT check).
6.  **Leverage Existing Libraries (Configured Enforcement & No Reinvention)**:
    *   Utilize stable, well-maintained PyPI packages compatible with Python 3.13+ (`uv` managed). Treat vetted libraries as reliable components.
    *   **Configure standard tools** (`ruff`, `mypy`, `pytest`, `pylint`) via `pyproject.toml` according to ZLF specifications. Passing checks from these **configured tools currently serves as the primary enforcement mechanism** for corresponding ZLF principles. These tools act as essential "consultants" providing automated feedback, orchestrated ideally by ZLT.
    *   **Strictly forbid** modifying the internal behavior of third-party libraries at runtime (monkey-patching). Interact only via documented public APIs.
    *   **No Reinvention:** Do not reimplement functionality already provided by the Python standard library or mandated tools unless absolutely necessary and justified by tests. Custom checks (e.g., AST analysis within ZLT) require strong justification if a core ZLF principle cannot be measured by standard tooling.
7.  **Don't Repeat Yourself (DRY)**: During the Refactor step of TDD, consolidate logic identified via testing or analysis (`pylint R0801`). Eliminate duplication to reduce debt and ensure consistent updates. Apply DRY to test code as well (aided by DDT). (Enforced via `pylint R0801` check by ZLT).
8.  **Self-Documenting Code & Explicit Rationale**:
    *   Use descriptive names (`what`). Code clarity is paramount for AI comprehension.
    *   Employ docstrings/comments to explain the *why* (rationale, context) only for **non-obvious logic**. Assume an AI reader understands Python 3.13+ syntax.
    *   **Triggers for Rationale Comments:** Add comments when the code implements: (a) Workarounds for external library issues, (b) Logic chosen after other attempts failed (documenting the dead-end), (c) Complex algorithms/state management deviating significantly from simple approaches. The goal is to prevent future AI developers from repeating exploration or encountering the same pitfalls.
    *   Documentation follows implementation within the TDD cycle. (Partially enforced via `ruff D` rules by ZLT).
9.  **Consistent Style & Idiomatic Usage**: Apply uniform coding style enforced by `ruff format` (project config) and `ruff check`, along with modern type hints (Python 3.13+) and idioms. Style checks are a core part of the automated feedback loop, executed by ZLT.
10. **Comprehensive Testing & Automation (Inherent via TDD/DDT)**: TDD/DDT naturally produce high test coverage for correctness and regression prevention. Automate checks (`ruff`, `mypy`, `pylint R0801`, `pytest`, potentially fuzzers) via `pre-commit` and CI, ideally orchestrated by ZLT as essential, non-negotiable feedback mechanisms supporting the AI developer's workflow. (Enforced via tool execution by ZLT).
11. **Explicit Error Handling & Reliable Resource Management**: Design tests that cover expected error conditions. Implement specific exception handling and ensure resources (files, connections, locks) are reliably released via context managers (`with`) or `try...finally`, verified by tests covering success and failure paths. (Enforced via `pytest` results and specific `ruff` rules by ZLT).
12. **AI-Led Continuous Refactoring (TDD Refactor Step Scope)**:
    *   Embrace code evolution within the **Refactor** step of the TDD cycle.
    *   **Baseline (Mandatory):** Clean up code added/modified in the Green step to meet all static analysis requirements (`ruff`, `mypy`, `pylint R0801`), format correctly, and adhere to clarity/simplicity principles (Principles #4, #8).
    *   **Incremental Improvement:** Proactively make immediate, localized improvements (simplify conditions, improve names, apply Python 3.13 idioms, extract small helpers) related to the code just touched.
    *   **Larger Refactoring:** Identify opportunities for significant architectural refactoring but typically defer implementation. Add ideas to `REFINEMENT IDEAS` (Section [5.3](#53-footer)) or initiate a *new* TDD cycle specifically for that refactoring, driven by new tests proving its value. The AI **should** prioritize completing the current cycle cleanly over attempting deep refactoring mid-cycle.
13. **Design for Concurrency Safety (When Required & Testable)**: If concurrency is needed, use TDD to drive the design. Write tests that attempt to expose potential race conditions or safety issues (acknowledging difficulty). Implement solutions using appropriate mechanisms (e.g., `asyncio`, `threading`) driven by tests. Protect shared state with synchronization primitives. Prevent race conditions and document the concurrency model. (See Section [4.9](#49-concurrency-and-resource-management)). (Verification relies on test results and potentially specialized concurrency analysis tools, future ZLT scope).
14. **Adhere to Filesystem Standards (XDG & Tooling Configuration)**:
    *   **Runtime:** Applications **must** store user-specific files according to the XDG Base Directory Specification (using environment variables like `$XDG_CONFIG_HOME`). Write tests verifying correct file placement.
    *   **Tooling:** Development/CI tooling **must**, where configurable, be set up to use XDG-compliant directories for caches/config, enforced via `pyproject.toml` and only rely on environment variables as a last resort. (Verification via configuration checks, potentially by ZLT).
15. **Input Robustness (Where Applicable)**: Modules processing complex or untrusted external data (e.g., parsers, network handlers) **must** demonstrate resilience against malformed or unexpected inputs. (Enforced via fuzz testing orchestrated by ZLT, see Section [4.X](#4x-input-robustness-verification-via-fuzz-testing) - *To be added*).

---

## 4. KEY METRICS & PRACTICES

This section details specific practices and metrics used to assess compliance with the ZLF Guiding Principles (Section [3](#3-guiding-principles)), primarily enforced via ZLT and its consultant tools.

### 4.1 Test-Driven Development (TDD) Workflow
*(Supports Principle #1, #9)*
*   **Red-Green-Refactor Cycle:** **Mandatory** adherence for all production code changes.
*   **Test Granularity:** Write small, focused tests targeting specific behaviors or requirements. Use distinct `test_` functions for different behaviors/paths.
*   **Minimum Viable Code (Green Step):** Implement only the code necessary to pass the current failing test before refactoring.
*   **Refactoring Scope (Refactor Step):** Perform baseline cleanup, ensure compliance with all automated checks (via ZLT) for the changed code, and make localized improvements. Defer major refactoring (see Principle #11).
*   **Refactoring Safety Net:** Rely on the comprehensive test suite created during TDD/DDT to refactor code confidently.
*   **Test Coverage (Outcome):** High test coverage is an expected outcome of rigorous TDD/DDT. Verify logical coverage via `pytest --cov` (run by ZLT) and enforce `fail_under` in CI (configured in `pyproject.toml`). See Section [4.12](#412-validation-metrics-outcomes--enforcements).
*   **AI Feedback Priority:** Address automated check failures reported by ZLT in the order: Format -> Type/Lint -> Tests.

### 4.2 Data-Driven Testing (DDT) Practices
*(Supports Principle #2, #9)*
*   **When to Use:** **Strongly prefer** DDT (via `pytest.mark.parametrize`) over separate test functions when testing the *exact same logical path* with variations in *input data* or *expected output* (e.g., boundary values, valid/invalid states, different formats).
*   **Separate Functions:** Use separate `test_` functions when testing *distinctly different behaviors*, *control flow paths*, or *failure modes*, even if within the same production function. This clarifies test intent.
*   **Data Separation:** Keep test data separate from test logic. Use tuples/lists within `@pytest.mark.parametrize` for simple cases.
*   **External Test Data:** For complex inputs (e.g., multi-line strings, structured data, source code snippets), **require** storing test data in separate files (e.g., in `tests/test_data/`). Load using mechanisms like `pathlib.Path.read_text()`. This improves readability and maintainability. Consider simple formats like `.txt`, `.yaml`, or `.json` for these files.

### 4.3 AI Quality & Readability
*(Supports Principle #3, #7)*
*   **Context Independence**: Aim for components/modules readable and testable with minimal external context.
*   **AI Insight Documentation**: Docstrings clarify purpose (defined by tests), rationale (context, per Principle #7 heuristics), pre/post-conditions, and usage. **Require** `USAGE EXAMPLES:` for non-trivial public APIs. (Checked by `ruff D` rules via ZLT).
*   **Implementation Consistency**: >95% adherence to patterns enforced by tooling. Format with `ruff format`, lint/style/docs with `ruff check`. (Checked by ZLT via `ruff`).

### 4.4 File Organization
*(Supports Principle #3)*
*   **File Purpose**: Header docstring (Section [5.1](#51-header)) **must** specify single responsibility (often corresponding to a test suite focus).
*   **File Size**: Target < 300 lines (excluding docstrings/comments), encouraged by TDD/DDT's focus on small, testable units. (Potentially checked by ZLT).
*   **Module Interface**: Strict exposure via `__init__.py` (use `autoinit` if desired).

### 4.5 Code Quality
*(Supports Principle #3, #4, #6, #8, #10)*
*   **Semantic Naming**: **Require** descriptive identifiers understandable by AI without context.
*   **Function Size**: Target < 30 lines (excluding docstrings/comments), naturally promoted by TDD/DDT. (Potentially checked by ZLT).
*   **Function Signature**: **Require** ≤ 4 parameters; use `@dataclass(frozen=True)`/TypedDicts/Pydantic models for more. (Potentially checked by ZLT or `ruff`).
*   **Cyclomatic Complexity**: **Prefer** < 8 (via `ruff mccabe` check executed by ZLT). Keep units simple for testability.
*   **Code Duplication**: Eliminate duplication during the Refactor TDD step (verify via `pylint R0801` check executed by ZLT). See Section [4.12](#412-validation-metrics-outcomes--enforcements).
*   **Mandatory Type Annotation**: **Require** explicit, modern (Python 3.13+) type hints. Enforce with `mypy --strict` (executed by ZLT). See Section [4.12](#412-validation-metrics-outcomes--enforcements).
*   **Minimize Mutable Global State**: **Require** avoiding module-level mutable variables. Pass state explicitly. (Checked by `ruff` rules via ZLT).
*   **Favor Immutability (Mandatory Practice)**:
    *   **Universally prefer** immutable data structures. Mutability requires strong justification documented via Principle #7.
    *   **Require** using `@dataclass(frozen=True)` for custom data structures unless mutation is essential.
    *   **Require** using `typing.Final` for module/class level constants (enforced by `mypy` via ZLT).
    *   **Prefer** tuples over lists for fixed collections.
    *   **Prefer** functional style (return new values) over in-place modification.
    *   **Require** writing tests specifically verifying the absence of unintended side effects for functions intended to be pure.

### 4.6 Error Reporting & Logging
*(Supports Principle #10)*
*   **Test Error Conditions:** **Require** writing specific tests for expected failure modes and exception handling (`pytest` executed by ZLT).
*   **Traceability**: Exceptions **must** include context. Use chaining/groups appropriately.
*   **Logging Library:** **Require** using **`structlog`**.
*   **Logging Configuration & Format:**
    *   **Require** configuring `structlog` with processor pipelines.
    *   **Require** using `structlog.processors.JSONRenderer()` for output in CI/testing/production environments (for machine parsing).
    *   **Recommend** using `structlog.dev.ConsoleRenderer(colors=True)` for local development (for human readability). Select renderer based on environment context during `structlog.configure()`.
*   **Logging Content:** **Require** including standard fields (`timestamp`, `level`, `event`, `logger`) and relevant context (`structlog.contextvars`).
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
*   **Exception Management**: **Require** raising specific exceptions based on tested failure conditions. Avoid broad `except Exception:`. Enforce with `ruff` rules (e.g., `tryceratops`, `flake8-builtins`) via ZLT.
*   **No Internal Fallbacks**: **Require** failing explicitly based on test expectations.

### 4.7 Data Validation & Parsing
*(Supports Principle #10, #14)*

*   **External Data Handling:** **Require** **Pydantic** models for defining, parsing, and validating non-trivial external data structures. **Require** writing tests covering valid and invalid data scenarios using these models. (Validation occurs at runtime, tests verified by ZLT via `pytest`).
*   **Mandatory Pydantic Use Cases:** Pydantic **must** be used for:
    1.  **Configuration Loading:** Validating the structure and types of data loaded from `pyproject.toml` (specifically `[tool.zeroth-law]` sections) via `config_loader.py`.
    2.  **Tool Definition JSON Parsing:** Validating the AI-generated `.json` tool definition files (`src/zeroth_law/tools/<tool>/<id>.json`) against their schema (`tools/zlt_schema_guidelines.md`) when read by ZLT or related tooling.
    3.  **Tool Index Parsing:** Validating the structure of `src/zeroth_law/tools/tool_index.json` when read by ZLT or related tooling.
    4.  **Action Mapping Parsing:** Validating the structure of `tool_mapping.yaml` if/when it is loaded programmatically by ZLT.
    5.  **(Future) API Interactions:** Validating external API request/response schemas.
    6.  **(Future) Complex Tool Output Parsing:** Validating structured output from consultant tools if needed.
*   **Runtime Validation vs. Assertions:** Use Pydantic/explicit checks for *external* inputs (tested); use `assert` for *internal* invariants identified and verified during TDD (see Section [4.8](#48-defensive-programming--assertions)).

### 4.8 Defensive Programming & Assertions
*(Supports Principle #10)*
*   **Strategic Assertions**: Use `assert` liberally for internal invariants, pre-conditions, and post-conditions identified and verified during the TDD Refactor step. Assertions document assumptions the AI developer makes about internal state.
*   **Invariant Checks**: Assert conditions that tests assume **must** always hold true within a specific scope.
*   **Assertion Density**: Guided by test logic and invariants discovered during development. **Prefer** more assertions for internal checks.
*   **Verbose Testing**: **Require** running `pytest -vv` (via ZLT configuration). Ensure assertion messages clearly explain the invariant violation to aid AI debugging of test failures.

### 4.9 Concurrency and Resource Management
*(Supports Principle #10, #12)*
*   **(Applies if project requires concurrency & driven by tests)**
*   **Test Concurrency Issues:** **Require** writing tests specifically designed to provoke race conditions or verify synchronization if possible (can be challenging). Test resource handling under concurrent access if applicable.
*   **Use Synchronization Primitives**: Protect necessary shared state with appropriate mechanisms (e.g., `asyncio.Lock`, `threading.Lock`), driven by failing tests where feasible.
*   **Reliable Resource Management**: **Require** always using context managers (`with`) or `try...finally` to ensure resources (files, network connections, locks) are released reliably. Test both success and failure paths for resource release.
*   **Document Concurrency Model**: **Require** specifying thread/async safety and strategy (`stateless`, `synchronized`, etc.) in relevant docstrings or `NOTES.md`.
*   **Verify External Calls**: Ensure external library interactions are concurrency-safe or protected appropriately.
*   **`asyncio` Best Practices (if using `asyncio`):** **Require** applying best practices (avoid blocking calls, use `async with/for`, manage tasks correctly) driven by tests for async functionality.

### 4.10 Commit Message Standards
*(Supports Principle #7)*
*   **Conventional Commits:** **Require** adherence to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification for all Git commit messages. The AI developer **must** generate compliant messages, often corresponding to TDD cycles (e.g., `feat: implement X`, `test: add test for Y`, `refactor: improve Z`). (Potentially linted by `pre-commit` hook, outside ZLT's direct execution scope but part of the overall workflow).

### 4.11 Versioning Scheme
*   **Epoch/Date Versioning:** **Require** utilizing a strictly increasing version scheme based on time (e.g., `YYYYMMDD.HHMMSS` or Unix epoch seconds). Define in `pyproject.toml` (`[project.version]`). This deterministic scheme is suitable for AI management and relies on the comprehensive TDD suite for compatibility assurance between versions.

### 4.12 Validation Metrics (Outcomes & Enforcements)
These metrics represent the **Programmatic Ground Truth** assessed by ZLT:
*   **Test Coverage**: High coverage (>95% logical) is an expected outcome of TDD/DDT. Verify via `pytest --cov` and enforce with `fail_under` threshold in `pyproject.toml` (interpreted by ZLT).
*   **Type Coverage**: 100% (enforced via `mypy --strict` execution by ZLT).
*   **Code Duplication**: Zero warnings from `pylint R0801` (check executed by ZLT).
*   **Documentation Coverage**: 100% public APIs (`ruff D` rules enforced by ZLT). Documentation written after passing tests, before/during Refactor.
*   **Docstring Style Compliance**: Adherence to convention (`ruff D` rules enforced by ZLT).
*   **Docstring Example Coverage**: **Require** `USAGE EXAMPLES:` for non-trivial public APIs. (Manual check or future ZLT enhancement).
*   **Runtime Type Guards**: **Require** validation of external inputs via Pydantic/explicit checks, driven by tests (`pytest` results verified by ZLT).
*   **Input Robustness Checks (Fuzzing):** Pass/Fail status for required fuzz targets (check executed by ZLT).

### 4.13 Dependencies & Environment
*(Supports Principle #5)*
*   **Dependency Specification:** **Require** defining runtime dependencies in `pyproject.toml` under `[project.dependencies]` (PEP 621) and development dependencies under `[project.optional-dependencies.<group>]` (e.g., `[project.optional-dependencies.dev]`). AI developer manages this via `uv pip install <pkg>` (which modifies `pyproject.toml`) or direct edits followed by `uv lock`/`uv pip sync`.
*   **Environment Management:** **Require** use of **`uv`** for managing dependencies and virtual environments based on `pyproject.toml` and `uv.lock` (if used, or potentially `poetry.lock` for transition). ZLT **must** be run within this environment (e.g., via `uv run zlt ...`).
*   **Vetting**: **Prefer** standard libraries and reputable PyPI packages compatible with Python 3.13+. Check licenses.
*   **Justification**: Document reasons for significant third-party dependencies in `NOTES.md` or relevant docstrings.
*   **Locking:** **Recommend** using a lock file (`uv lock > uv.lock` or using `poetry.lock`) for reproducible environments, especially in CI.

---

## 5. IN-FILE DOCUMENTATION PATTERN

**Require** employing this consistent Header-Implementation-Footer structure in every Python file. Content **must** reflect Python 3.13+ features, Pydantic usage (Section [4.7](#47-data-validation--parsing)), `structlog` patterns (Section [4.6](#46-error-reporting--logging)), and TDD/DDT principles (Sections [4.1](#41-test-driven-development-tdd-workflow), [4.2](#42-data-driven-testing-ddt-practices)) where applicable.

### 5.1 Header
```python
# FILE: <path/to/file.py>
"""
# PURPOSE: [Single responsibility, often derived from the initial test's goal.]
#          [Should be clear and concise for AI understanding.]
"""
# --- IMPORTS --- (Standard library, 3rd party, own packages - Follow ruff sorting)
import logging # Or specific imports
import structlog
# ... other imports ...

# --- CONSTANTS --- (Use typing.Final)
from typing import Final
# Example: DEFAULT_TIMEOUT: Final[int] = 10

# --- LOGGING --- (Module-level logger)
log = structlog.get_logger()

# --- DATA STRUCTURES --- (Pydantic models, dataclasses - See Sec 4.7)
# Example: from pydantic import BaseModel
# Example: @dataclass(frozen=True) class InputData: ...
```

### 5.2 Implementation Example (Conceptual TDD/DDT Flow)
```python
# Example function developed via TDD/DDT

# Assumes InputData, Config, OutputResult, SpecificError are defined (e.g., in Header or imported)

def process_item(item_data: InputData, config: Config) -> OutputResult:
    """PURPOSE: Processes a validated item based on configuration.
    CONTEXT: Developed via TDD/DDT. Assumes immutable inputs (Principle #4.5). Handles X, Y, Z cases.
             Rationale for using Algorithm A documented below (Principle #7).
    PRE-CONDITIONS:
     - item_data is validated by Pydantic upstream (Sec 4.7).
     - config is a valid, immutable Config object.
    POST-CONDITIONS:
     - Returns an OutputResult object.
     - Raises SpecificError on failure condition ZZZ (tested per Sec 4.6).
    PARAMS:
     - item_data: The input data for the item.
     - config: Application configuration.
    RETURNS:
     - Result of the processing.
    EXCEPTIONS:
     - SpecificError: If condition ZZZ occurs.
    USAGE EXAMPLES:
     >>> item = InputData(...) # Example data
     >>> cfg = Config(...)   # Example config
     >>> result = process_item(item, cfg) # Example from test_process_item_success
     >>> assert isinstance(result, OutputResult)
    """
    # --- ASSERTIONS (Internal Invariants - Sec 4.8) ---
    assert config.is_valid(), "Internal check: Config should be valid here."
    proc_log = log.bind(item_id=item_data.id) # Structured logging context (Sec 4.6)
    proc_log.info("processing_started")

    # --- CORE LOGIC (Driven by Tests - Sec 4.1) ---
    # Rationale (Principle #7): Using Algorithm A because initial tests showed Algorithm B
    # failed under high load conditions (see NOTES.md section YYYY-MM-DD).
    try:
        # ... Minimum code to pass tests, refactored for clarity ...
        result_value = _perform_complex_step(item_data, config.setting)
        proc_log.debug("complex_step_completed", intermediate=result_value)

        if result_value < 0:
             # Test case test_process_item_negative_result drives this path (Sec 4.6)
             raise SpecificError("Negative result encountered", item_id=item_data.id)

        final_result = OutputResult(id=item_data.id, value=result_value)
        proc_log.info("processing_completed", success=True)
        return final_result

    except SpecificError: # Catch specific, tested exceptions first
        proc_log.warning("processing_failed_specific", reason="Negative result")
        raise # Re-raise the specific error
    except Exception as e: # Catch broader exceptions only if necessary and tested
        proc_log.error("processing_failed_unexpected", exc_info=True)
        # Re-raise or handle as defined by specific failure tests (Sec 4.6)
        raise SpecificError(f"Unexpected processing error: {e}", item_id=item_data.id) from e

# --- HELPER FUNCTIONS --- (If extracted during refactoring - Principle #11)
def _perform_complex_step(data: InputData, setting: str) -> int:
    # Developed via its own TDD cycle if sufficiently complex
    # ... implementation ...
    pass # Placeholder
```

### 5.3 Footer
```python
"""
## LIMITATIONS & RISKS: [Identified during TDD/Refactoring, e.g., external system dependency, potential scaling issues not covered by current tests]
## REFINEMENT IDEAS: [Ideas for next TDD cycles or future refactoring, e.g., 'Explore caching results', 'Apply fuzz testing (Sec 4.X)', 'Refactor helper X for clarity']
## ZEROTH LAW COMPLIANCE (ZLF):
# Framework Version: YYYY-MM-DDTHH:MM:SS+ZZ:ZZ
# Compliance results populated by the Zeroth Law Tool (ZLT).
# Overall Status: [e.g., PASS/FAIL]
# Score: [e.g., 98/100] (Optional scoring metric TBD)
# Penalties: [List of ZLF sections/rules violated, e.g., 'FAIL: 4.5 Cyclomatic Complexity > 8', 'FAIL: 4.12 Test Coverage < 95%']
# Timestamp: [e.g., YYYY-MM-DDTHH:MM:SS+ZZ:ZZ] (Timestamp of ZLT assessment)
"""

```

---

## 6. AUTOMATION

This section details the tooling and configurations used to automate ZLF enforcement, ideally orchestrated by ZLT.

### 6.1 Tools (Consultants)

ZLT utilizes the following mandatory 'consultant' tools. ZLT **requires** these tools to be available in the project's `uv`-managed environment (Section [4.13](#413-dependencies--environment)) to perform its compliance checks. Configuration **must** reside in `pyproject.toml`.

1.  **`uv`**: Required for dependency management, environment creation, and running scripts (`uv run ...`). ZLT relies on the environment managed by `uv`.
2.  **`pre-commit`**: Manages Git hooks executing automated checks (ideally just `zlt validate`). Uses the project-specific `.pre-commit-config.yaml` (Section [6.4](#64-pre-commit-configuration-pre-commit-configyaml)).
3.  **`ruff`**: Primary consultant for linting (`ruff check`), formatting (`ruff format`), import sorting, and docstring checks (`D` rules). ZLT executes `ruff` based on `pyproject.toml [tool.ruff]`.
4.  **`mypy`**: Consultant for static type checking. ZLT **must** execute `mypy` with the `--strict` flag, configured via `pyproject.toml [tool.mypy]`.
5.  **`pylint` (Targeted Usage)**: Consultant used exclusively for code duplication detection (`R0801`). ZLT executes `pylint --disable=all --enable=R0801 <targets>`. Configured via `pyproject.toml [tool.pylint.*]`.
6.  **`pytest`**: **Core testing framework consultant**. ZLT executes `pytest` to run tests developed via TDD/DDT and collects coverage using `pytest-cov`, configured in `pyproject.toml [tool.pytest.ini_options]`.
7.  **`structlog`**: Required runtime library for structured JSON/Console logging (see Section [4.6](#46-error-reporting--logging)).
8.  **`Atheris`** (or other designated fuzzer): Consultant for Input Robustness checks. ZLT executes configured fuzz targets. *(Integration TBD)*.
9.  **`autoinit`** (Optional): Manages `__init__.py` files.
10. **Poetry (Legacy/Transitional)**: May be present in migrating projects but **must not** be the primary manager for new ZLF projects. `uv` can install from `poetry.lock` using `uv pip sync --resolver=poetry poetry.lock`.

### 6.2 Environment & Dependency Workflow (Using `uv`)
This workflow is typically executed by the AI developer or automation scripts:

1.  **Create Environment (First time):** `uv venv` (creates `.venv` by default).
2.  **Activate Environment (Optional):** `source .venv/bin/activate` (or equivalent for shell/OS).
3.  **Add/Update Dependencies:** `uv pip install <package>[==<version>] [--dev]` (or modify `pyproject.toml [project]` directly). Use `--dev` to add to `[project.optional-dependencies.dev]`.
4.  **Sync Environment:** `uv pip sync pyproject.toml [--all-extras | --extras <group>]` installs/updates based on `pyproject.toml` (or `uv pip sync uv.lock` / `uv pip sync --resolver=poetry poetry.lock` if using lock files).
5.  **Run Commands:** Execute tools via `uv run <command>` (e.g., `uv run zlt validate`, `uv run pytest`). This ensures execution within the correct environment without explicit activation.
6.  **CI:** CI pipeline uses `uv venv` and `uv pip sync` to set up the environment and `uv run zlt validate` (ideally) or individual tool commands for checks.

### 6.3 Project Structure Example (Conceptual)
*(Assumes project root contains `pyproject.toml`)*

**Mandate:** To prevent ambiguity and ensure clear distinction, the ZLF **requires** that the project root directory name and the primary Python package directory name (typically inside `src/`) **must not** be identical.

**Recommendation:** The **recommended** structure to achieve this distinction is `project_pkg/src/project/`. This keeps the importable Python package name clean (`project`) which aligns well with standard Python imports and tooling focus, while clearly identifying the project root directory via the `_pkg` suffix.

```
project_pkg/         # Project Root (Recommended naming convention)
│
├── .github/             # CI/CD workflows (e.g., GitHub Actions using Poetry)
│   └── workflows/
│       └── ci.yml       # Runs `poetry run zlt validate` or individual checks
│
├── frameworks/          # Optional: ZLF definitions for reference
│   └── python/
│       └── ZerothLawAIFramework-*.md
│
├── scripts/             # Helper scripts (run via `poetry run`)
│   └── ...
│
├── src/                 # Source code for the project/tool
│   └── project/         # The main Python package (Matches intended import name)
│       ├── __init__.py
│       └── ...
│
├── tests/               # Tests (following TDD/DDT)
│   ├── __init__.py
│   └── test_data/       # External data files for DDT (Sec 4.2)
│   └── fuzz/            # Fuzzing targets and corpus (Sec 4.X)
│       ├── __init__.py
│       ├── fuzz_parser.py # Example fuzz target script
│       └── corpus_parser/ # Example corpus directory
│   └── ...
│
├── .gitignore           # Standard Git ignore file
├── .pre-commit-config.yaml # PROJECT-SPECIFIC pre-commit hooks (Sec 6.4)
├── pyproject.toml       # Defines project metadata, dependencies, tool configs (Poetry, ZLT)
├── poetry.lock          # Exact dependency versions (Managed by Poetry)
├── README.md            # Project documentation
├── NOTES.md             # Decision log & rationale (See Sec 8)
└── TODO.md              # High-level goals & task tracking (See Sec 8)

```
*(Note: For monorepos where Git root != project root, custom Git hooks managed by ZLT might be needed to invoke the project-specific ZLT validation. See Section [8](#8-project-knowledge-management) & NOTES.md for context).*

### 6.4 Pre-Commit Configuration (`.pre-commit-config.yaml`)
*   **Location:** **Must** reside in the project root (alongside `pyproject.toml`).
*   **Ideal Hook:** The primary hook **should** be `entry: poetry run zlt validate`.
*   **Interim Hooks:** Until ZLT fully orchestrates, hooks may call individual tools. Hooks requiring project dependencies (`mypy`, `pytest`, `pylint`, custom scripts, ZLT itself) **must** use `language: system` and `entry: uv run <command>`. Ensure the environment where `pre-commit` runs has `uv` available, or use a `language: python` hook with `uv` listed in `additional_dependencies` to bootstrap it.
*   **Activation:** Ensure Git hooks are active (e.g., via `pre-commit install --config .pre-commit-config.yaml -t pre-commit -t pre-push` or ZLT's hook management if implemented).
*   **Monorepo Hook Management:** The `zlt install-git-hook` mechanism remains valid. The generated hook script should be updated to invoke project-specific hooks using `uv run ...` if necessary, or ensure the hook environment setup correctly activates the project's `uv` environment.

### 6.5 Example CI Pipeline (GitHub Actions with `uv`)
```yaml
name: Python CI (Zeroth Law Framework with uv)

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

    - name: Install uv
      uses: yezz123/setup-uv@v4 # Or official uv action if available
      # Or: run: curl -LsSf https://astral.sh/uv/install.sh | sh
      #     run: echo "$HOME/.cargo/bin" >> $GITHUB_PATH

    - name: Create venv and cache dependencies
      uses: actions/cache@v4
      with:
        path: .venv
        # Key includes Python version and lock file hash (or pyproject.toml hash if no lock)
        key: venv-uv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/uv.lock', '**/poetry.lock', '**/pyproject.toml') }}
      id: cache-venv

    - name: Create venv
      run: uv venv
      if: steps.cache-venv.outputs.cache-hit != 'true'

    - name: Install dependencies (using uv)
      # Sync based on lock file if present, otherwise pyproject.toml
      # Use --all-extras or specific extras as needed for dev deps
      run: |
        if [ -f uv.lock ]; then
          uv pip sync uv.lock
        elif [ -f poetry.lock ]; then
          uv pip sync --resolver=poetry poetry.lock
        else
          uv pip sync pyproject.toml --all-extras
        fi

    # Preferred Method: Single ZLT command run via uv
    - name: Run ZLF Compliance Checks via ZLT
      run: uv run zlt validate --ci

    # --- Fallback/Interim Method (If ZLT not fully orchestrating) ---
    # - name: Run pre-commit checks (via uv run)
    #   run: uv run pre-commit run --all-files --show-diff-on-failure --config .pre-commit-config.yaml
    # - name: Run Tests with Coverage (via uv run)
    #   run: uv run pytest --cov=src --cov-report=xml --cov-fail-under=95

    # Optional: Upload coverage reports (if generated separately)
    # - name: Upload coverage to Codecov ...
```

## 7. COMMON ISSUES & FIXES

### 7.1 `pytest` Import Errors (with `uv`)
Common causes for `ImportError` when using `uv run pytest` (or via ZLT):
1.  **Project Not Installed:** Ensure `uv venv` completed successfully (installs project in editable mode).
2.  **Incorrect `testpaths`:** Verify `[tool.pytest.ini_options].testpaths` in `pyproject.toml` points to `tests`.
3.  **Missing `__init__.py` Files:** Ensure necessary `__init__.py` exist in source (`src/your_package`) and test directories (`tests/`) for package recognition. `autoinit` can manage this.
4.  **Incorrect `PYTHONPATH` (Unlikely with `uv run`):** `uv run` usually handles this. ZLT **must** operate within the `uv` environment. Investigate only if other causes are ruled out.

### 7.2 Pre-Commit Failures
*   **Formatters Failing on Change:** Tools like `ruff format` *will* cause `pre-commit` to fail if they modify files. **Solution:** **Require** configuring the IDE (e.g., VS Code/Cursor with Ruff extension) for format-on-save (see Section [8](#8-project-knowledge-management), `NOTES.md`). The `pre-commit` hook (or ZLT running the formatter check) then acts as a safety net.
*   **Hook Configuration Errors:** Ensure paths in `.pre-commit-config.yaml` are correct relative to the project root and that `uv run` is used for tools needing the project environment (if not using ZLT directly). ZLT will rely on configurations in `pyproject.toml`.

---

## 8. PROJECT KNOWLEDGE MANAGEMENT

To ensure context is preserved for future AI and human maintainers:

*   **`NOTES.md`:** Maintain a chronological log of significant technical decisions, rationale for framework choices or deviations, troubleshooting discoveries, and architectural changes. Use timestamps (`date --iso-8601=seconds`).
*   **`TODO.md`:** Track high-level project goals, milestones, and larger refactoring tasks identified but deferred.
*   **Inline `TODO:` Comments:** Use for small, actionable items directly related to the code section. Consider using a script (potentially via `pre-commit` or manually) to aggregate these into a central `CODE_TODO.md` dashboard for visibility.
*   **Commit History:** Leverage Conventional Commits (Section [4.10](#410-commit-message-standards)) for a meaningful, navigable history.

---

## 9. ONBOARDING LEGACY CODE

Bringing existing, non-compliant code under the ZLF follows a structured, test-driven approach:

1.  **Characterization Tests:** Select a code segment. Write tests (`pytest`) that document its *current* behavior, inputs, and outputs, even if incorrect. These tests should initially pass.
2.  **Identify ZLF Violation:** Run `zlt validate` (or individual tools) to identify specific ZLF rule violations (e.g., complexity, typing, test coverage). Choose one violation to address.
3.  **Targeted TDD Cycle:**
    *   **Red:** Write a *new* test (or modify a characterization test) designed to fail now but pass once the specific ZLF violation is fixed and the desired behavior is implemented.
    *   **Green:** Make the *minimum change* to the code to pass the new test, ensuring original characterization tests still pass (unless behavior *must* change).
    *   **Refactor:** Clean the modified code per Principle #11 / Section [4.1](#41-test-driven-development-tdd-workflow), ensuring all tests pass and ZLT reports compliance for the addressed violation(s).
4.  **Iterate:** Repeat steps 2-3, incrementally refactoring the code towards full ZLF compliance, guided by ZLT reports and the TDD cycle. Prioritize refactoring code that needs functional changes first, or start with less critical modules.

---

## 10. FRAMEWORK EVOLUTION

*This ZLF document is a living specification.* It will adapt as tools evolve and best practices emerge, guided by the core principles of TDD, automation, and AI-centric development. Changes **must** be documented in `NOTES.md`.
