# Zeroth Law: AI-Driven Python Code Quality Framework

**Co-Author**: Trahloc colDhart
**Version**: 2025-03-17

## 1. PURPOSE

Establishes code quality principles for Python development using AI. Optimizes for AI comprehension, maintainability, and reliability, prioritizing clarity over convention. Emphasizes SRP and `__init__.py` for API definition.

## 3. APPLICATION

This framework is foundational. Code must satisfy these metrics before functional completion. AI assistants should enforce these principles.

## 4. GUIDING PRINCIPLES

1.  `AI Comprehension Priority: AI readability is paramount.`
2.  `In-File Context Sufficiency: All context within the file. Sentence-like function names are preferred.`
3.  `Implementability: Practical application over theory.`
4.  `Incremental Enhancement: Track progress with AI assessments; non-breaking refinements.`
5.  `Use Existing Modules: Well-maintained external dependencies from reputable sources (like PyPI) are considered "free" in terms of added complexity and cost.`
6.  `Single Responsibility Principle (SRP): One function per file (excluding __init__.py). Core principle.`
7.  `Modularity and Composability: Functions are self-contained. __init__.py composes functionality via selective export.`
8.  `Explicit API Design: __init__.py defines the public API. Only import from __init__.py files.`
9.  `First Principles: The best part is no part. The best process is no process. It weighs nothing, costs nothing, can't go wrong.`

## 5. IN-FILE DOCUMENTATION PATTERN

### 5.1 File Header

```python
# FILE: project_head/src/project_module/file_name.example
"""
# PURPOSE: [File's single responsibility.]

## INTERFACES: [function_name(param_type) -> return_type]: [description] (Omit if single function; docstring is interface. For __init__.py, list exported functions.)

## DEPENDENCIES: [module_path]: [What's needed. For __init__.py, list module dependencies.]

## TODO: [Tasks. Remove completed. Add from Future TODOs.]
"""
```

### 5.2 Code Entity (Function)

```python
def a_very_descriptive_function_name(param1: type, param2: type = default) -> return_type:
    """
    PURPOSE: [Single responsibility.]

    CONTEXT: [Local imports, if any.]

    PARAMS: [Description of each parameter.]

    RETURNS: [Description of the return value.]
    """
    # ... implementation ...
```

### 5.3 File Footer

```python
"""
## KNOWN ERRORS: [List with severity.]

## IMPROVEMENTS: [This session's improvements.]

## FUTURE TODOs: [For next session. Consider further decomposition.]
"""
```

## 6. KEY METRICS

### 6.1 AI Quality

*   **Context Independence:** Maximize understandability within the file (descriptive names, single-function files, `__init__.py` for namespaces). *Critical*
*   **AI Insight Documentation:** Document AI suggestions (dates, rationales). *Critical*
*   **Implementation Consistency:** >90% consistency with patterns (header-code-footer, one-function-per-file, `__init__.py`). Use `black` and `flake8` for automated checks. *High*
*   **Project Architecture Visibility:** Use directory structure. Minimal, centralized documentation if needed. Dependencies in `__init__.py`. *Medium*
*   **Test Coverage:** >90% business logic coverage (separate `tests` directory, mirroring source structure). Use `pytest` for testing. *Medium*
*   **Cross-Reference:** Use PEP 8, standard patterns (prioritize one-function-per-file simplicity). Use `flake8` and `black` for enforcement. *Medium*

### 6.2 File Organization

*   **File Purpose:** Docstring describes purpose, role, dependencies (in header). *Critical*
*   **File Size:** ~200-300 lines (excluding documentation). One-function-per-file is primary control. *Low*
*   **Module Interface:** Document public interfaces (docstrings, `__init__.py` defines API).  Use `autoinit` to automate `__init__.py` generation. Only import from `__init__.py`. *High*

### 6.3 Code

*   **Semantic Naming:** Descriptive identifiers (even long names). *Critical*
*   **Function Size:** <30 lines (excluding comments). One-function-per-file largely addresses this. *High*
*   **Function Signature:** Descriptive parameters, ≤4 (use dataclasses if necessary). Use `mypy` for static type checking. *High*
*   **Cyclomatic Complexity:** <8 (guard clauses, polymorphism). *Medium*
*   **Code Duplication:** <2%. Create new single-function modules. *Low*

### 6.4 Error Handling

*   **Traceability:** Function/parameter info in error messages. *Critical*
*   **Logging:** Uniform format (timestamp, severity, message, context). Structured logging. *High*
*   **Exception Management:** Handle or rethrow with context. Custom exceptions. Use `mypy` to enforce consistent exception handling. *High*
*   **Error Recovery:** Graceful fallback/failure. Circuit breakers. *Medium*

### 6.5 Dependencies
*   **Vetting:** Prioritize well-maintained Python Standard and PyPI packages. *Critical*
*   **Discernment** Justify why each external dependency was chosen over Standard or other PyPI packages. *Medium*

## 7. AUTOMATION

*   **`pre-commit` Framework:** Use `pre-commit` to automate code quality checks.
*   **`autoinit`:** Automatically generate and update `__init__.py` files.  Integrate with `pre-commit`.
*   **`pytest`:** Use for unit and integration tests.
*   **`black`:** Automatically format code for consistency. Integrate with `pre-commit`.
*   **`flake8`:** Lint code for style and potential errors. Integrate with `pre-commit`.
*   **`mypy`:** Perform static type checking. Integrate with `pre-commit`.
