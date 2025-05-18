# Example Project Structure

The following is the recommended project structure when using the Zeroth Law framework:

```
your_project/
├── .github/                      # GitHub workflows and templates
│   ├── workflows/                # CI/CD workflows
│   │   └── ci.yml                # Continuous integration workflow
│   └── ISSUE_TEMPLATE/           # Issue templates
├── docs/                         # Documentation
│   ├── architecture.md           # High-level system design
│   ├── api.md                    # API documentation
│   └── development.md            # Development guidelines
├── src/                          # Source code
│   └── your_package/             # Main package
│       ├── __init__.py           # Package exports
│       ├── __main__.py           # CLI entry point
│       ├── config.py             # Configuration handling
│       ├── exceptions.py         # Error handling
│       ├── core/                 # Core functionality
│       │   ├── __init__.py       # Module exports
│       │   └── ...               # Core modules
│       ├── utils/                # Utility functions
│       │   ├── __init__.py       # Module exports
│       │   └── ...               # Utility modules
│       └── cli/                  # Command-line interface
│           ├── __init__.py       # Module exports
│           └── ...               # CLI commands
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest configuration
│   ├── test_config.py            # Configuration tests
│   ├── test_exceptions.py        # Exception tests
│   ├── core/                     # Core module tests
│   │   └── ...                   # Core test modules
│   ├── utils/                    # Utility tests
│   │   └── ...                   # Utility test modules
│   └── cli/                      # CLI tests
│       └── ...                   # CLI test modules
├── .gitignore                    # Git ignore rules
├── .pre-commit-config.yaml       # Pre-commit hooks
├── pyproject.toml                # Project configuration
├── README.md                     # Project documentation
└── LICENSE                       # License file
```

## Key Organizing Principles

1. **Module Hierarchy**: Group related functionality into modules with clear responsibilities
2. **Parallel Structure**: Mirror source code structure in tests directory
3. **Separation of Concerns**: Split core logic, utilities, and interfaces
4. **Documentation**: Maintain comprehensive documentation alongside code
5. **Automation**: Configure CI/CD workflows to enforce code quality

## Adapting This Structure

When customizing the template for your project, you can:

1. Rename `your_package` to your actual package name
2. Add or remove subdirectories based on your project's complexity
3. Expand the `core` directory with domain-specific modules
4. Create a `models` directory if your project uses data models

The structure should reflect your project's specific needs while maintaining the Zeroth Law principles of clarity, responsibility isolation, and self-documentation.
