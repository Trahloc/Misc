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

Use these sections (Header, Implementation, Footer) as a consistent pattern in every file to maintain clarity and reduce guesswork.

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
  PRE-CONDITIONS & ASSUMPTIONS: [What must be true before calling]
  PARAMS:
    param1 (type): [Ranges/constraints]
    param2 (type): [Ranges/constraints]
  POST-CONDITIONS & GUARANTEES: [What changes or conditions are ensured]
  RETURNS:
    [Return value semantics and special cases]
  EXCEPTIONS:
    [Exceptions that may be raised]
  USAGE EXAMPLES:
    [Illustrative sample usage]
  """
  # ... implementation ...

### 4.3 Footer
```python
"""
## KNOWN ERRORS: [List error types or scenarios]
## IMPROVEMENTS: [Latest session improvements]
## FUTURE TODOs: [Ideas for next session or releases]
"""
```

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
- **Mandatory Type Annotation**: Every function parameter, return value, and variable declaration must include explicit type hints. Use specialized types from the `typing` module (Union, Optional, Callable, etc.) where appropriate. Enforce with strict mypy configuration that rejects any functions lacking complete annotations.

### 5.4 Error Handling
- **Traceability**: Include function name, parameters, and context in exception messages.
- **Logging**: Use structured logs with timestamps, severity, message, and context fields.
- **Exception Management**: Raise specific exceptions where suitable, avoiding silent catch-all.
- **No Fallbacks**: For internal code, fail explicitly rather than guess. Fallbacks apply only to external dependencies.

### 5.5 Error Handling

- **Strategic Assertions**: Place assertions in code to validate internal assumptions and catch invalid states early.
- **Pre-conditions**: Verify input parameters at function entry points to ensure they meet expected formats or ranges.
- **Post-conditions**: Check return values and state before exiting functions, confirming correct or expected outcomes.
- **Invariants**: Maintain consistent properties throughout processing, asserting these remain unchanged where needed.
- **State Transitions**: Ensure objects only move between valid states, raising clear errors when transitions are violated.
- **Assertion Coverage**: Require at least one entry and one exit assertion in every non-trivial function, each with descriptive error messages.
- **Verbose Testing**: Run pytest with the “-xvs” flag so assertion messages are fully visible, ensuring quick detection of unexpected states.

### 5.6 Validation Metrics
- **Type Coverage**: 100% of code has type annotations
- **Assertion Density**: Minimum 1 assertion per 10 lines of code
- **Documentation Coverage**: 100% of public APIs documented
- **Docstring Example Coverage**: All complex functions include usage examples
- **Runtime Type Guards**: Validate external inputs even when type hints exist

### 5.7 Dependencies
- **Vetting**: Prefer standard libraries and widely trusted PyPI packages.
- **Discernment**: Document justification for each third-party dependency over alternatives.

---

## 6. AUTOMATION

### 6.1 Tools

Use the following tools and checks to maintain code quality and consistency:

1. **pre-commit**
  Configure hooks to run formatters, linters, type-checkers, docstyle validators, and tests before every commit. This prevents incomplete or inconsistent commits from reaching the repository.

2. **autoinit**
  Automatically generate and maintain `__init__.py` files for each module, ensuring that only necessary functions and classes are exported.

3. **pytest**
  Serve as the main testing framework, covering both unit and integration scenarios. Use the “--enable-assertions” flag so assertion-based checks remain active, capturing unexpected failures.

4. **black**
  Enforce a consistent code format so that diffs focus on logic rather than style adjustments.

5. **flake8**
  Lint for style and logical errors, flagging anything that violates PEP 8 or recognized best practices.

6. **mypy**
  Employ strict type-checking (“--strict”) to enforce explicit type annotations in every function and data definition, reducing runtime surprises.

7. **pydocstyle**
  Validate the presence and format of docstrings, keeping inline documentation consistent and instructive.

8. **Custom Assert Validator**
  Inspect the volume and placement of assertions in relation to function complexity. Encourage thorough coverage of pre-conditions and post-conditions.

9. **interrogate**
  Measure documentation coverage, aiming for 100% to ensure every module, function, and class is clearly explained.

Integrate these tools into continuous integration (CI) so any violations produce error cli errors and block merges until resolved. This comprehensive approach automates compliance with Zeroth Law standards, reducing risk while improving code clarity.

### 6.2 Example Project Layout
```md
project_head/
├── pyproject.toml
├── src/
│   └── project_module/
└── tests/
    └── ...
```

### 6.3 `pyproject.toml`
```toml
# filepath: /project_head/pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "example_zeroth"
version = "1742729946"
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
example_zeroth = "example_zeroth.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]
```

Use this centralized configuration for building, testing, and packaging. Combine it with `pre-commit` hooks that run `flake8`, `black`, `mypy`, and `pytest` to guarantee every commit meets or exceeds the Zeroth Law standards.
