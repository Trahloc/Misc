# Zeroth Law: AI-Driven Python Code Quality Framework

**Co-Author**: Trahloc colDhart
**Version**: 2025-04-08

---

## 1. PURPOSE
Design a minimal, AI-first framework for Python code quality targeting **Python 3.13+** and the **`micromamba`** environment manager. By mandating **Test-Driven Development (TDD)** alongside enforcing clarity, simplicity, modular design, opinionated standards, and comprehensive automated checks, this framework ensures every component is demonstrably correct, immediately understandable, maintainable, and verifiable, leveraging AI assistance for continuous refactoring and adaptation.

## 2. APPLICATION
All new or modified code **must** be developed following the Test-Driven Development cycle and pass all associated tests and guideline checks before merging into the main branch. Automated checks via `pre-commit` and CI apply each requirement based on configurations in `pyproject.toml`, blocking completion until tests pass and consistency is assured. This framework assumes AI actively assists in development (including test generation and refactoring) within the TDD loop, enabling rapid evolution and adherence to modern standards. Development utilizes `micromamba` environments derived from `pyproject.toml` dependency specifications.

## 3. GUIDING PRINCIPLES

1.  **Test-Driven Development (TDD) First**: **Require** all production code to be driven by tests. Follow the strict **Red-Green-Refactor** cycle: write a failing test (Red), write the minimum code to pass the test (Green), then improve the code while keeping tests green (Refactor). This ensures inherent testability, verifiable correctness, and drives emergent design.
2.  **Single Responsibility & Clear API Boundaries**: Keep components focused on one reason to change, making them easier to test and reason about via TDD. Expose minimal necessary interfaces via `__init__.py` (managed by `autoinit` if desired). Isolation simplifies AI reasoning and independent refinement.
3.  **First Principles Simplicity**: Solve problems directly with minimal complexity, driven by the need to pass the current test. Prefer clear Python 3.13+ features over intricate abstractions. Minimalism reduces error surface and boosts AI refactoring confidence within the TDD cycle.
4.  **Follow Modern Project Standards**: Align with conventions from contemporary, reputable Python projects known for quality. Adopt proven patterns while remaining open to evolution. Use influential standards like `black` formatting as context, but configure `ruff format` to project-specific needs defined herein.
5.  **Leverage Existing Libraries (No Reinvention)**: Utilize stable, well-maintained PyPI/Conda packages compatible with Python 3.13+. Treat vetted libraries as reliable blocks, focusing AI effort on unique project logic tested at integration boundaries.
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
*   **Dependency Specification:** Define in `pyproject.toml` under `[tool.poetry.dependencies]` and `[tool.poetry.group.dev.dependencies]` for use with `poetry export` (via the `poetry-plugin-export` plugin) to generate requirement files.
*   **Environment Management:** **Require** use of **`micromamba`** based on generated `environment.yml`.
*   **Vetting**: Prefer standard libraries and reputable PyPI/Conda packages compatible with Python 3.13+. Check licenses.
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
Employ this mandatory toolset, configured via `pyproject.toml` and orchestrated by `pre-commit` and CI, supporting the TDD workflow with `micromamba` environments and Python 3.13+:

1.  **`micromamba`**: Required environment manager.
2.  **`poetry` & `poetry-plugin-export`**: Required for dependency management in `pyproject.toml` and exporting to `requirements.txt` format. (`poetry-plugin-export` should be installed in the environment used for generation, e.g., a bootstrap env or added to dev dependencies).
3.  **`pre-commit`**: Manages Git hooks for automated checks (lint, type, format, etc.).
4.  **`ruff`**: Primary tool for linting, formatting, import sorting, doc checks.
5.  **`mypy`**: Static type checker (`--strict` mode).
6.  **`pylint` (Targeted Usage)**: Used exclusively for code duplication detection (`R0801`).
7.  **`pytest`**: **Core testing framework** used continuously during the TDD Red-Green-Refactor cycle. Includes coverage via `pytest-cov`.
8.  **`structlog`**: Required runtime library for structured JSON logging.
9.  **`autoinit`** (Optional): Manages `__init__.py` files.

### 6.2 Environment & Dependency Workflow

1.  **Define Dependencies:** Specify runtime dependencies in `pyproject.toml` under `[tool.poetry.dependencies]` and development dependencies under `[tool.poetry.group.dev.dependencies]` (using Poetry's group syntax is recommended).
2.  **Generate Requirement Files:** Run `poetry export` (requires the `poetry-plugin-export` plugin to be installed in the environment running the command, e.g., `localbin` or the activated project env if added to dev deps) to generate **two** requirement files:
    *   `poetry export --without-hashes -o requirements.txt` (for main runtime dependencies)
    *   `poetry export --without-hashes --only dev -o requirements-dev.txt` (for development-only dependencies)
    These steps **must** be re-run whenever dependencies in `pyproject.toml` change. Automation via a script (like `scripts/generate_requirements.sh`) or `Makefile` target is highly recommended. These generated files (`requirements.txt`, `requirements-dev.txt`) should typically be added to `.gitignore`.
3.  **Define `environment.yml` for Micromamba:** Create a minimal `environment.yml` that specifies the base Python version, includes `pip`, and instructs `pip` to install the main runtime dependencies from the generated `requirements.txt`. Example:
    ```yaml
    name: <env_name>
    channels:
      - conda-forge
      - defaults
    dependencies:
      - python>=3.13,<4.0
      - pip
      - pip:
          - -r requirements.txt
    ```
    This `environment.yml` file **should be committed** to version control.
4.  **Create Environment:** Use `micromamba env create -f environment.yml -n <env_name>`. Note that this only installs the *main* dependencies specified in `requirements.txt`.
5.  **Activate Environment:** Use `micromamba activate <env_name>` before running development tasks.
6.  **Install Development Dependencies:** After activating the environment, install the development dependencies using pip: `pip install -r requirements-dev.txt`.
7.  **CI:** The CI pipeline automates steps 2, 4, 5, and 6 within its workflow.

project_root/
│
├── .github/             # CI/CD workflows (e.g., GitHub Actions)
│   └── workflows/
│       └── ci.yml
│
├── frameworks/          # Core framework definitions, organized by language
│   └── python/
│       └── ZerothLawAIFramework-*.md  # Specific Python framework versions
│   # └── rust/ (Example for future language)
│   #     └── ZerothLawAIFramework-*.md
│
├── scripts/             # Helper scripts (e.g., env generation, release)
│   └── generate_requirements.sh # Or similar if needed
│
├── src/                 # Source code for the zeroth_law *tool* itself
│   └── zeroth_law/      # The Python package for the tool
│       ├── __init__.py
│       └── ... (modules/subpackages for the tool)
│
├── templates/           # Project templates for bootstrapping new projects using ZL
│   └── python/
│       └── cookiecutter-zeroth-law-py/ # Example Python project template
│           └── ...
│   # └── rust/ (Example for future language template)
│   #     └── ...
│
├── tests/               # Tests for the zeroth_law *tool* itself
│   ├── __init__.py
│   └── ... (test files mirroring src structure)
│
├── .gitignore           # Standard Git ignore file
├── .pre-commit-config.yaml # Pre-commit hook definitions
├── CHANGELOG.md         # Optional but recommended: Log of changes
├── CONTRIBUTING.md      # Optional but recommended: Contribution guidelines
├── LICENSE                # Project license file
├── Makefile             # Optional but useful: Define common tasks (e.g., make env, make test)
├── README.md            # Main project README (explaining the tool and the framework)
├── environment.yml      # Minimal file for micromamba env creation (uses requirements.txt)
├── requirements.txt     # Generated main dependencies (usually .gitignored)
├── requirements-dev.txt # Generated dev dependencies (usually .gitignored)
└── pyproject.toml       # Central configuration & dependency spec (Poetry format for deps)

### 6.4 `pyproject.toml` Example Configuration (Python 3.13+, Poetry Deps)

```toml
# filepath: /project_root/pyproject.toml

[build-system]
requires = ["setuptools>=61.0", "wheel"] # Standard build system deps
build-backend = "setuptools.build_meta"

# --- Project Metadata (PEP 621) ---
# Include standard metadata primarily for packaging tools (e.g., building wheels/sdists).
# Dependency and version information are duplicated under [tool.poetry] for compatibility
# with the poetry2conda workflow required for micromamba.
[project]
name = "example_zeroth_tdd" # Keep consistent with tool.poetry.name
# Version is managed under [tool.poetry] - DO NOT DUPLICATE here
authors = [
  { name = "Trahloc colDhart", email = "github@trahloc.com" }
]
description = "Python package via Zeroth Law (TDD, Python 3.13+, Micromamba)" # Keep consistent
readme = "README.md"
requires-python = ">=3.13" # Primary Python constraint
license = { text = "MIT" } # Standard license expression
classifiers = [
  "Development Status :: 3 - Alpha", # Example status
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.13",
  # Add future Python versions as they are supported
]
keywords = ["zeroth-law", "ai-framework", "quality", "tdd", "python313"] # Example keywords

# Define any command-line scripts provided by the package
# [project.scripts]
# my_cli = "package_name.cli:main"

# --- Poetry Section (Primary Source for Dependencies & Version for poetry2conda) ---
[tool.poetry]
name = "example_zeroth_tdd" # Must match [project] name
# Version uses Epoch/Date format (e.g., Unix timestamp)
# Replace dynamically in release process or manually update.
version = "1712601600" # Example timestamp: 2025-04-08 ~18:00 UTC
description = "Python package via Zeroth Law (TDD, Python 3.13+, Micromamba)" # Matches [project]
authors = ["Trahloc colDhart <github@trahloc.com>"] # Poetry author format
license = "MIT" # Matches [project]
readme = "README.md" # Matches [project]
# Define where the package source code is located for Poetry build tools
packages = [{include = "package_name", from = "src"}]
# Explicitly state Python compatibility for Poetry
[tool.poetry.dependencies]
python = ">=3.13,<4.0" # Align with project.requires-python

# --- Runtime Dependencies (Managed by Poetry) ---
# Add essential runtime libraries here
structlog = "^24.1.0"
pydantic = "^2.6.0"
# Example other dependencies:
# click = "^8.1.0" # If building a CLI
# requests = "^2.31.0" # If making HTTP requests

# --- Development Dependencies (Managed by Poetry under Groups) ---
[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.4.0"
pytest-cov = "^4.1.0" # For test coverage

# Type Checking
mypy = "^1.8.0" # Ensure version supports Python 3.13 robustly

# Linting, Formatting, Doc Checks, Import Sorting
ruff = "^0.2.2" # Use a specific recent version

# Duplication Check (Targeted Use)
pylint = "^3.1.0" # Ensure version supports Python 3.13 robustly

# Environment Generation Tool - USE poetry-plugin-export instead
# poetry2conda = "^1.0.0"
poetry-plugin-export = "^1.8.0" # Check for the latest compatible version

# Git Hooks Manager
pre-commit = "^3.6.0"

# Optional Tools
autoinit = "^0.3.0" # If used for __init__.py management

# Build/Publishing Tools (Optional)
# build = "^1.0.0"
# twine = "^5.0.0"

# --- MyPy Configuration ---
[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true # Set to false for stricter checks if all stubs are present
# Enable strict mode for comprehensive checks
strict = true
# Define cache directory *name*; actual location controlled by MYPY_CACHE_DIR env var
# which should point inside $XDG_CACHE_HOME (e.g., $XDG_CACHE_HOME/mypy) per Principle #12
cache_dir = "mypy_cache"

# --- Pytest Configuration ---
[tool.pytest.ini_options]
minversion = "7.0"
# -ra: show extra test summary info for failed/skipped/passed tests
# -q: quiet mode (less verbose overall)
# -vv: max verbosity for failures to aid debugging
# --cov=src: measure coverage within the src directory
# --cov-report=term-missing: show coverage summary and missing lines in terminal
# --cov-fail-under=95: fail the run if coverage is below 95%
addopts = "-ra -q -vv --cov=src --cov-report=term-missing --cov-fail-under=95"
testpaths = [
    "tests", # Directory where tests are located
]
# Pytest cache location relies on XDG_CACHE_HOME environment variable being set and respected
# by pytest cacheprovider plugin per Principle #12. No explicit cache_dir setting here.

# --- Coverage Configuration (for pytest-cov) ---
[tool.coverage.run]
branch = true     # Measure branch coverage
source = ["src"]  # Measure coverage only for code within the src directory

[tool.coverage.report]
# fail_under = 95 # Already enforced by pytest addopts --cov-fail-under
show_missing = true # Show line numbers of statements not covered

# --- Ruff Configuration ---
[tool.ruff]
line-length = 140      # Project-specific formatting standard
target-version = "py313" # Target Python 3.13 features/syntax

# Define rule sets to enable. Explicitly select desired checks.
# See Ruff documentation for available rule codes.
select = [
    "E", "W", # pycodestyle errors and warnings
    "F",      # pyflakes (undefined names, unused imports/variables)
    "I",      # isort (import sorting)
    "UP",     # pyupgrade (modernize syntax)
    "B",      # flake8-bugbear (potential logic errors/style issues)
    "SIM",    # flake8-simplify (simplify code constructs)
    "C4",     # flake8-comprehensions (use comprehensions effectively)
    "BLE",    # flake8-blind-except (avoid broad exception handlers)
    "A",      # flake8-builtins (avoid shadowing builtins)
    "RUF",    # Ruff-specific rules
    "D",      # pydocstyle (docstring presence, format, content)
    "T20",    # flake8-print (detect leftover print statements)
    "ISC",    # flake8-implicit-str-concat (detect implicit string concatenation)
    "N",      # pep8-naming (naming conventions)
]
ignore = [
    "D203", # Conflicts with some formatter styles (space before class docstring)
    "D213", # Conflicts with some formatter styles (multi-line doc summary)
    # Add any other specific rules to ignore project-wide if necessary, with justification.
    # e.g., "N803" # Allow lowercase arg names if preferred style
]
exclude = [
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".nox",
    ".pants.d",
    ".direnv",
    "__pypackages__",
    "_build",
    "buck-out",
    "build",
    "dist",
    "node_modules",
    "venv",
    ".venv",
    ".micromamba", # Exclude potential micromamba metadata if stored locally
    "*/migrations/*", # Exclude database migrations
    # Cache directories expected to be managed via XDG variables
    # ".mypy_cache", # Controlled by MYPY_CACHE_DIR / tool.mypy.cache_dir name
    # ".pytest_cache", # Controlled by XDG_CACHE_HOME ideally
    # ".ruff_cache", # Controlled by XDG_CACHE_HOME
]

# Configure Ruff's formatter component (used if `ruff format` is run)
[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "lf"

# Configure Ruff's documentation style checking (pydocstyle integration)
[tool.ruff.pydocstyle]
convention = "google" # Choose preferred convention (google, numpy, pep257)

# Configure Ruff's import sorting (isort integration)
[tool.ruff.isort]
force-single-line = true # Example: prefer single line imports where possible
known-first-party = ["package_name"] # Help Ruff identify local project imports

# Configure Ruff's McCabe complexity checker
[tool.ruff.mccabe]
max-complexity = 8 # Fail functions exceeding this complexity

# --- Pylint Configuration (SIMILARITY ONLY) ---
[tool.pylint.'MESSAGES CONTROL']
# Disable ALL checks by default. Ruff handles standard linting.
disable = "all"
# Explicitly enable ONLY the similarity check message ID.
enable = "R0801" # R0801: Similar lines in %s files

[tool.pylint.similarities]
# Fine-tune the similarity detection:
min-similarity-lines = 5    # Minimum number of identical lines to trigger R0801. Adjust as needed.
ignore-comments = true      # Ignore differences in comments
ignore-docstrings = true    # Ignore differences in docstrings
ignore-imports = true       # Ignore differences in import statements
ignore-signatures = false   # Treat functions with different signatures as different code

# --- Setuptools configuration (minimal, if needed for build) ---
# Used if building packages with setuptools backend
[tool.setuptools.packages.find]
where = ["src"] # Tell setuptools where to find the source package
```

### 6.5 Example `pre-commit` Configuration
```yaml
# filepath: /project_root/.pre-commit-config.yaml
minimum_pre_commit_version: '3.0.0'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: check-toml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      # Optional: Hook to ensure requirements*.txt stay synced with pyproject.toml/poetry.lock
      # Requires a script/Makefile target `make generate-reqs-check` or similar
      # that generates & diffs, fails on diff.
      # - id: run-make-generate-reqs-check # Custom hook name
      #   name: Check requirements*.txt sync
      #   entry: make generate-reqs-check
      #   language: system
      #   files: ^pyproject.toml$|^poetry.lock$ # Trigger on relevant changes
      #   pass_filenames: false
      #   stages: [commit] # Run on commit, not push

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.2 # Pin to match project version
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0 # Pin to match project version
    hooks:
      - id: mypy
        files: ^src/
        # Relies on MYPY_CACHE_DIR environment variable being set correctly
        # to place cache according to XDG standard (Principle #12)
        additional_dependencies: [] # Add type stubs if needed

  # Pylint - Exclusively for Similarity Checks (R0801)
  - repo: https://github.com/pycqa/pylint
    rev: v3.1.0 # Pin to match project version
    hooks:
      - id: pylint
        name: pylint (similarities only)
        files: ^src/.*\.py$
        # Configuration comes from pyproject.toml [tool.pylint.*] sections.
        # Execution must happen within the activated micromamba environment
        # where pylint and project dependencies are installed.
        # Using `language: python` assumes pre-commit can find the active conda env python.
        # If imports fail, switch to `language: system`.
        language: python
        # types: [python] # Already implied by language: python

  # Autoinit (Optional)
  # - repo: https://github.com/python-useful-helpers/autoinit
  #   rev: v0.3.0
  #   hooks:
  #     - id: autoinit
```

### 6.6 Example CI Pipeline (GitHub Actions with Micromamba)
```yaml
# filepath: /project_root/.github/workflows/ci.yml

name: CI Checks

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  lint_test:
    runs-on: ubuntu-latest
    defaults:
      run:
        # Ensure subsequent steps run in the conda environment shell
        shell: bash -l {0}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      # Setup Micromamba
      - name: Setup Micromamba
        uses: mamba-org/setup-micromamba@v1
        with:
          environment-name: zeroth-law-ci-env
          # Use environment-file: environment.yml *after* it's generated
          # We will create env from file in a later step
          create-args: >-
            python=${{ matrix.python-version }} # Specify Python version for base env

      # Set XDG environment variables for subsequent steps
      # Use workspace-relative paths for cache persistence via actions/cache
      - name: Set XDG Environment Variables
        run: |
          echo "XDG_CACHE_HOME=${{ github.workspace }}/.cache" >> $GITHUB_ENV
          echo "XDG_CONFIG_HOME=${{ github.workspace }}/.config" >> $GITHUB_ENV
          echo "XDG_DATA_HOME=${{ github.workspace }}/.local/share" >> $GITHUB_ENV
          # Set specific tool env vars pointing within XDG_CACHE_HOME
          echo "MYPY_CACHE_DIR=${{ github.workspace }}/.cache/mypy" >> $GITHUB_ENV
          echo "PIP_CACHE_DIR=${{ github.workspace }}/.cache/pip" >> $GITHUB_ENV
        shell: bash # Use default shell for setting GITHUB_ENV

      # Cache Micromamba packages and pip downloads
      - name: Cache Mamba Pkgs & Pip Cache
        uses: actions/cache@v4 # Use v4
        with:
          path: |
            ${{ env.MAMBA_ROOT_PREFIX }}/pkgs
            ${{ github.workspace }}/.cache/pip
            ${{ github.workspace }}/.cache/mypy # Cache mypy results too
          key: ${{ runner.os }}-micromamba-${{ hashFiles('**/pyproject.toml', '**/poetry.lock') }} # Include poetry.lock in hash
          restore-keys: |
            ${{ runner.os }}-micromamba-

      # Install poetry and export plugin (needed to generate requirements files)
      # Assumes poetry & plugin are NOT part of the final env's dev dependencies
      # If they ARE in dev dependencies, install them AFTER creating the env.
      - name: Install Poetry & Export Plugin (Bootstrap)
        run: pip install poetry poetry-plugin-export

      # Generate requirement files from pyproject.toml/poetry.lock
      - name: Generate requirements.txt files
        run: |
          poetry export --without-hashes -o requirements.txt
          poetry export --without-hashes --only dev -o requirements-dev.txt
        shell: bash # Use default shell

      # Create/Update Micromamba environment using the *minimal* environment.yml
      # This installs Python, pip, and main dependencies via requirements.txt
      - name: Create/Update Micromamba Environment
        run: micromamba env update --file environment.yml --name zeroth-law-ci-env --prune

      # --- Run Checks within the Activated Environment ---
      # The 'shell: bash -l {0}' default ensures these run activated

      # Install Development Dependencies
      - name: Install Dev Dependencies
        run: pip install -r requirements-dev.txt

      - name: Run Ruff Linter and Format Check
        run: |
          ruff check src/ tests/
          ruff format --check src/ tests/

      - name: Run Pylint (Similarities only)
        run: pylint src/

      - name: Run Mypy
        run: mypy src/

      - name: Run Tests with Pytest
        run: pytest --cov=src --cov-report=term-missing --cov-fail-under=95

      # Optional: Upload coverage report artifact
      # - name: Upload coverage reports ...
```

### 6.7 AI Assistant Responsibilities
> **AI Assistant Context Management:** AI assistants **must** proactively utilize file reading (`read_file`), history inspection (`git log`), and search tools (`grep_search`, `codebase_search`) to establish or re-establish context before proceeding with tasks, especially when resuming work or encountering ambiguity. Reliance solely on potentially incomplete or lost conversational history is prohibited. Adherence to this principle is part of Zeroth Law compliance for AI-driven development within this framework.

---

## 7. FIXING PYTEST IMPORT ERRORS (with Micromamba)

Common causes for `ImportError` when running `pytest` in a `micromamba` environment:

1.  **Environment Not Activated:** Ensure the correct `micromamba` environment (`micromamba activate <env_name>`) is active in your terminal session *before* running `pytest`.
2.  **Missing `__init__.py`:** Ensure directories within `src/package_name` and `tests` intended as packages have an `__init__.py`.
3.  **Running `pytest` Incorrectly:** Always run `pytest` from the project root (`project_root/`).
4.  **Package Not Installed:** Although `micromamba` installs dependencies listed in `environment.yml` (which includes main deps via `requirements.txt`), development dependencies and the project code itself might not be installed or visible. Ensure:
    *   The correct environment is activated (`micromamba activate <env_name>`).
    *   Development dependencies were installed (`pip install -r requirements-dev.txt`).
    *   The project is installed in editable mode (`pip install -e .`). This is often the crucial step for `pytest` to find your local source code.
5.  **`PYTHONPATH` Issues:** Avoid manipulating `PYTHONPATH` directly; use editable installs.
6.  **Stale Files:** Ensure `requirements.txt` and `requirements-dev.txt` were regenerated via `poetry export` after any `pyproject.toml` dependency changes, and the environment was updated (`micromamba env update ...`, followed by `pip install -r requirements-dev.txt` if dev deps changed).

---

## 8. APPENDIX: RECOMMENDED ISSUE LABELS
*(Optional section for project management consistency)*

Using a standard set of labels in issue trackers (e.g., GitHub Issues) improves clarity and organization. Consider adopting labels like:

*   **Type:** `type:bug`, `type:feature`, `type:docs`, `type:refactor`, `type:test`, `type:ci`, `type:chore`
*   **Status:** `status:needs-triage`, `status:todo`, `status:in-progress`, `status:needs-review`, `status:blocked`, `status:done`
*   **Priority:** `priority:critical`, `priority:high`, `priority:medium`, `priority:low`
*   **Breaking Change:** `breaking-change` (Useful for Conventional Commits/Versioning context)
