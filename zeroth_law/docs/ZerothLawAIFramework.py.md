# Zeroth Law: AI-Driven Python Code Quality Framework

**Co-Author**: Trahloc colDhart
**Version**: 2025-03-23

---

## 1. PURPOSE
Design a minimal, AI-first framework for Python code quality. By enforcing clarity, simplicity, and modular design, you ensure that every component is immediately understandable and maintainable without external references.

## 2. APPLICATION
All new or modified code must pass these guidelines before merging into the main branch. Automated checks and AI agents apply each requirement, blocking completion until consistency and correctness are assured.

## 3. GUIDING PRINCIPLES

1. **Single Responsibility & Clear API Boundaries**
   Keep each module, class, or function focused on a single reason to change. Expose only what’s necessary in `__init__.py`. By isolating responsibilities, you reduce downstream effects and simplify your own reasoning about how any piece can be replaced or refined.

2. **First Principles Simplicity**
   Solve each problem with the fewest moving parts. Strip away complexities and choose direct, readable solutions over clever abstractions. Minimalism lowers error risk and ensures greater confidence during refactoring or extension.

3. **Follow Exemplary Project Standards**
   Align with conventions seen in reputable Python projects (Requests, Django, NumPy). Embrace their architectural choices, code style, and documentation approaches. These proven patterns guide consistent decision-making and reduce guesswork.

4. **Leverage Existing Libraries (No Reinvention)**
   Before coding from scratch, consult PyPI for stable, well-tested packages. Treat these libraries as complexity-neutral, using them whenever they fit the task. Reuse frees you to focus on unique project challenges and improves overall reliability.

5. **Don’t Repeat Yourself (DRY)**
   Consolidate logic to a single location. Duplicate code grows technical debt and invites inconsistent updates. Maintain one authoritative source for any given functionality to avoid confusion and keep the codebase lean.

6. **Self-Documenting Code Structure**
   Name every function, class, and variable descriptively. Limit files to a single logical unit, with docstrings detailing PURPOSE, CONTEXT, and RETURNS. This embedded clarity enables you (or other AI agents) to navigate the code without external aids.

7. **Consistent Style & Idiomatic Usage**
   Apply a uniform coding style (PEP 8, type hints, established Python idioms). Homogeneity simplifies reading, editing, and automated linting. When everything follows the same rules, you can trust patterns and tools to behave predictably.

8. **Comprehensive Testing & Automation**
   Write tests (unit and integration) for each function, module, and class. Aim for high coverage to confirm correctness and prevent regressions. Let continuous integration run these checks automatically, raising flags if anything fails or violates style conventions.

9. **Explicit Error Handling & Robustness**
   Surface issues early with clear error messages and explicit exceptions. Avoid silent failures or ambiguous error states. When something goes wrong, fail fast so you can pinpoint the problem immediately, maintaining a stable and predictable system.

10. **Continuous Refactoring & Improvement**
   No code remains static. Regularly refine structure, reduce unnecessary complexity, and adapt to new insights. Rely on testing to safeguard existing behaviors. Steady improvement keeps the project vibrant and maintainable over its full lifecycle.

---

## 4. IN-FILE DOCUMENTATION PATTERN

### 4.1 Header
```python
# FILE: project_head/src/project_module/file_name.py
"""
# PURPOSE: [Describe this file's single responsibility.]

## INTERFACES: [function_name(param_type) -> return_type]: [Short description]
## DEPENDENCIES: [List relevant modules if needed]
## TODO: [List tasks or future goals]
"""
```

### 4.2 Implementation
```python
def a_very_descriptive_function_name(param1: type, param2: type = default) -> return_type:
    """
    PURPOSE: [Single responsibility for this function]
    CONTEXT: [Any local or domain-specific context]
    PARAMS:  [Explain parameters in bullet form if needed]
    RETURNS: [Description of the return value or side effects]
    """
    # ... implementation ...
```

### 4.3 Footer
```python
"""
## KNOWN ERRORS: [List error types or scenarios]
## IMPROVEMENTS: [Latest session improvements]
## FUTURE TODOs: [Ideas for next session or releases]
"""
```

Use these sections (Header, Implementation, Footer) as a consistent pattern in every file to maintain clarity and reduce guesswork.

---

## 5. KEY METRICS

### 5.1 AI Quality
- **Context Independence**: Each file should read as a standalone unit, with descriptive names and one-function-per-file.
- **AI Insight Documentation**: Clarify reasons and methods in docstrings, referencing these guidelines where relevant.
- **Implementation Consistency**: Keep a >90% adherence to the standard patterns (header-code-footer, single-function files, docstrings). Format code with `black` and catch errors with `flake8`.

### 5.2 File Organization
- **File Purpose**: Use the file docstring to specify what this file handles and any dependencies.
- **File Size**: Target 200–300 lines or fewer (excluding docstrings).
- **Module Interface**: Expose functionalities through `__init__.py` only. Use tools like `autoinit` if desired.

### 5.3 Code
- **Semantic Naming**: Long, descriptive identifiers are preferable to short or cryptic ones.
- **Function Size**: Under 30 lines (excluding comments), ensuring each function is sharply focused.
- **Function Signature**: Aim for ≤4 parameters. If more are required, consider using data classes. Employ `mypy` for type-checking.
- **Cyclomatic Complexity**: Prefer <8, handled by guard clauses or polymorphic strategies.
- **Code Duplication**: Keep it under 2%. If duplication appears, consolidate into a single-function module.

### 5.4 Error Handling
- **Traceability**: Include function name, parameters, and context in exception messages.
- **Logging**: Use structured logs with timestamps, severity, message, and context fields.
- **Exception Management**: Raise specific exceptions where suitable, avoiding silent catch-all.
- **No Fallbacks**: For internal code, fail explicitly rather than guess. Fallbacks apply only to external dependencies.

### 5.5 Dependencies
- **Vetting**: Prefer standard libraries and widely trusted PyPI packages.
- **Discernment**: Document justification for each third-party dependency over alternatives.

---

## 6. AUTOMATION

- **`pre-commit`**: Automate code formatting, linting, and checks before every commit.
- **`autoinit`**: Auto-generate and update `__init__.py` files, ensuring correct exports.
- **`pytest`**: Standard testing framework for unit and integration tests.
- **`black`**: Enforce uniform formatting.
- **`flake8`**: Lint for stylistic or logical errors.
- **`mypy`**: Provide static type-checking for safer refactoring.

### 6.1 Example Project Layout
```md
project_head/
├── pyproject.toml
├── src/
│   └── project_module/
└── tests/
    └── ...
```

### 6.2 `pyproject.toml`
```toml
# filepath: /project_head/pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "tmux_manager"
version = "100.0.1"
authors = [
  { name = "Trahloc colDhart", email = "github@trahloc.com" }
]
description = "A Python package generated with Zeroth Law"
readme = "README.md"
requires-python = ">=3.8"
classifiers = [
  "Programming Language :: Python :: 3",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent"
]
dependencies = [
  "click",                # Command-line handling
  "cookiecutter>=2.1.1",  # Project scaffolding
]

[project.optional-dependencies]
dev = [
  "pytest>=7.0",
  "black>=23.0",
]

[project.scripts]
tmux_manager = "tmux_manager.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]
```

Use this centralized configuration for building, testing, and packaging. Combine it with `pre-commit` hooks that run `flake8`, `black`, `mypy`, and `pytest` to guarantee every commit meets or exceeds the Zeroth Law standards.
