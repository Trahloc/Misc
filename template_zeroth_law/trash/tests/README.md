# Zeroth Law Template Tests

## PURPOSE: Document the testing approach for the Zeroth Law template.

## INTERFACES: N/A (Documentation file)

## DEPENDENCIES: N/A

## TODO: Keep updated as the test suite evolves.

## Overview

This directory contains all tests for the Zeroth Law template project. Tests follow the Zeroth Law principles outlined in the main documentation.

## Test Organization

- Each module should have a corresponding test file prefixed with `test_`
- Test functions should be prefixed with `test_`
- Test classes, if any, should be prefixed with `Test`
- Each test file should include docstrings following the Zeroth Law documentation pattern

## Running Tests

Run the complete test suite:

```bash
pytest
```

For verbose output with test names and assertions:

```bash
pytest -xvs
```

To run a specific test file:

```bash
pytest tests/test_specific_file.py
```

## Test Coverage

Aim for at least 90% coverage for business logic. Coverage can be checked with:

```bash
pytest --cov=template_zeroth_law tests/
```

## Test Principles

1. **Single Responsibility**: Each test should verify one aspect of functionality
2. **Clear Assertions**: Use descriptive assertion messages
3. **Complete Coverage**: Test both success and failure paths
4. **Independence**: Tests should not depend on each other's state
5. **Fixtures**: Use pytest fixtures for setup and teardown

## KNOWN ERRORS: None

## IMPROVEMENTS: Created test documentation

## FUTURE TODOs: Add examples of good test patterns
