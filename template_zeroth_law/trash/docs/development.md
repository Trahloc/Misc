# Development Guide

## PURPOSE: Provides guidelines for developing with the Zeroth Law template.

## INTERFACES: N/A (Documentation file)

## DEPENDENCIES: N/A

## Overview

This guide outlines the development process for projects using the Zeroth Law framework. It covers coding standards, workflows, and best practices.

## Development Workflow

1. **Setup**
   - Clone the repository
   - Install development dependencies: `pip install -e ".[dev]"`
   - Install pre-commit hooks: `pre-commit install`

2. **Feature Development**
   - Create a feature branch: `git checkout -b feature/my-feature`
   - Implement changes following Zeroth Law guidelines
   - Add tests for new functionality
   - Run tests locally: `pytest`
   - Commit changes (pre-commit hooks will verify quality)

3. **Code Review**
   - Submit a pull request
   - Address review feedback
   - Ensure CI checks pass

4. **Integration**
   - Merge to main branch
   - CI will run comprehensive checks

## Code Organization

### Module Structure

Follow the Single Responsibility Principle when organizing code:

- One primary function or class per file
- Group related files into modules
- Use descriptive file and directory names

### Import Hierarchy

Organize imports in the following order:

1. Standard library imports
2. Third-party package imports
3. Local application imports

Separate each group with a blank line and sort alphabetically within groups.

### Documentation Requirements

All public APIs must include:

- File-level docstrings with PURPOSE, INTERFACES, and DEPENDENCIES
- Function/class docstrings following the Zeroth Law pattern
- Usage examples for complex functionality
- Footer sections with KNOWN ERRORS and FUTURE TODOs

## Error Handling Patterns

### Exception Hierarchy

- Derive all exceptions from the base `ZerothLawError` class
- Create specific exception types for different error categories
- Include relevant context in exception instances

### Best Practices

- Fail early and explicitly with clear error messages
- Use descriptive attribute names in error objects
- Document all possible exceptions in function docstrings

### Example Pattern

```python
try:
    # Operation that might fail
    result = perform_operation(data)
except ZerothLawError as e:
    # Handle known framework errors
    logger.error(f"Operation failed: {e}", extra=e.attributes)
    # Consider whether to re-raise or recover
except Exception as e:
    # Convert unexpected errors to framework errors
    raise ZerothLawError(f"Unexpected error: {str(e)}") from e
```

## Assertion Strategy

### Strategic Placement

- Entry assertions: Validate inputs at function start
- Exit assertions: Verify results before returning
- Invariant assertions: Check state consistency during operations

### Assertion Density

Follow the Zeroth Law guideline of minimum 1 assertion per 10 lines of code.

### Example Pattern

```python
def process_data(data: Dict[str, Any]) -> List[Result]:
    """
    PURPOSE: Process input data and return results
    ...
    """
    # Entry assertion
    assert isinstance(data, dict) and data, "Data must be a non-empty dictionary"

    # Process data
    results = []
    for key, value in data.items():
        # Invariant assertion
        assert key, "Empty keys are not allowed"
        results.append(create_result(key, value))

    # Exit assertion
    assert all(isinstance(r, Result) for r in results), "All items must be Results"
    return results
```

## Testing Strategy

### Test Organization

- Mirror the source code structure in the test directory
- Name test files with `test_` prefix
- Group related tests into classes where appropriate

### Test Coverage

- Aim for 100% code coverage
- Include both happy path and error case tests
- Test edge cases and boundary conditions

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output and stop on first failure
pytest -xvs

# Run with coverage report
pytest --cov=src/template_zeroth_law --cov-report=html
```

## Continuous Integration

CI workflows automatically run:

- Linting with flake8, black, and isort
- Type checking with mypy
- Style checking with pydocstyle
- Documentation coverage with interrogate
- Unit tests with pytest

Ensure all CI checks pass before merging code.

## Troubleshooting Common Issues

### Test Import Errors

If you encounter import errors when running tests, check for the following common issues:

1. **Missing Module Functions**
   - Error: `ImportError: cannot import name 'get_project_root' from 'template_zeroth_law.utils'`
   - Solution: Ensure the function is implemented in the utils module and properly exported in `__init__.py`

2. **Missing CLI Entry Points**
   - Error: `ImportError: cannot import name 'main' from 'template_zeroth_law.cli'`
   - Solution: Verify that the CLI module correctly exposes the main function

3. **Renamed or Refactored Classes**
   - Error: `ImportError: cannot import name 'AppConfig' from 'template_zeroth_law.config'`
   - Solution: Update imports to use the correct class names (e.g., 'Config' instead of 'AppConfig')

### Resolving Import Issues

When you encounter import errors, follow these steps:

1. Check that the referenced module exists
2. Verify that the function or class is defined in the module
3. Ensure the function or class is exported in the module's `__init__.py` file
4. Check for typos or name changes in both the import statement and the implementation
5. If you've renamed something, update all references in test files

Example of properly exporting functions in `__init__.py`:

```python
# In src/template_zeroth_law/utils/__init__.py
from .project import get_project_root
from .config import load_config
# Export other utility functions...
```

### Synchronizing Tests With Implementation

After making changes to the API:

1. Run `pytest --collect-only` to identify import issues without running tests
2. Update test imports to match the current implementation
3. Consider using a test fixture to mock missing dependencies during development

## KNOWN ERRORS: None

## IMPROVEMENTS: Initial development guide, added troubleshooting section

## FUTURE TODOs: Add examples of good and bad code, expand testing guidelines
