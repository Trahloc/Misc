# Template Zeroth Law

## PURPOSE: Provides a universal base project template implementing the Zeroth Law AI Framework for Python.

## INTERFACES: N/A (Documentation file)

## DEPENDENCIES: N/A

## TODO: Review and refine documentation as project evolves.

<!-- Implementation section -->
## Overview

This project serves as a universal base template for Python applications that follow the Zeroth Law AI Framework. It provides a foundation for creating well-structured, maintainable, and AI-friendly Python code with minimal customization required.

## Features

- Comprehensive error handling framework
- Consistent documentation patterns
- Automated code quality checks
- Type checking with mypy
- Test infrastructure with pytest
- Project structure optimized for AI readability

## Getting Started

### Using This Template

#### Method 1: Direct Installation and Project Creation

1. Install the template package:
   ```bash
   pip install git+https://github.com/yourusername/template_zeroth_law.git
   ```

2. Create a new project:
   ```bash
   python -m template_zeroth_law init my_new_project
   cd my_new_project
   ```

3. Set up your new project:
   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```

#### Method 2: Manual Copy

1. Clone the template repository:
   ```bash
   git clone https://github.com/yourusername/template_zeroth_law.git
   ```

2. Customize the template for your project:
   ```bash
   # Run the built-in customization script (recommended)
   python -m template_zeroth_law customize

   # Or manually rename the package
   # - Update package name in pyproject.toml
   # - Rename src/template_zeroth_law to src/your_package_name
   # - Update imports throughout the codebase
   ```

3. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Template Structure

The template follows the recommended Zeroth Law project layout:

```
your_project/
├── pyproject.toml      # Project configuration
├── .pre-commit-config.yaml  # Code quality automation
├── README.md           # Project documentation
├── src/                # Source code
│   └── package_name/   # Your package (initially template_zeroth_law)
│       ├── __init__.py # Package exports
│       ├── __main__.py # CLI entry point
│       └── exceptions.py # Error handling
└── tests/              # Test suite
    ├── conftest.py     # Test fixtures
    └── test_*.py       # Test modules
```

### Usage

Basic usage of the template's error handling:

```python
from your_package import ZerothLawError

# Use the framework's error handling
try:
    # Your code here
    pass
except ZerothLawError as e:
    print(f"A Zeroth Law error occurred: {e}")
    print(f"Additional context: {e.attributes}")
```

## Configuration

### Configuration File

The project uses a configuration file to manage settings. The following formats are supported:

- **TOML**: Recommended for its simplicity and readability.
- **YAML**: Useful for complex configurations.
- **JSON**: Commonly used but less human-readable.

### Example Configuration (template_zeroth_law.toml)

```toml
[app]
name = "template_zeroth_law"
version = "0.1.0"
description = "A project created with the Zeroth Law AI Framework"
debug = false

[logging]
level = "INFO"
format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"
log_file = null

[paths]
data_dir = "data"
output_dir = "output"
cache_dir = ".cache"
```

## Development

### Testing

Run tests with pytest:

```bash
pytest
```

For detailed output:

```bash
pytest -xvs
```

### Code Quality

This project enforces code quality using:

- **black**: Code formatting
- **flake8**: Style and logical linting
- **mypy**: Type checking
- **pydocstyle**: Documentation style
- **interrogate**: Documentation coverage

These are automated through pre-commit hooks.

## Extending the Template

This template is designed to be extended with your project-specific modules. When adding new modules:

1. Follow the Zeroth Law documentation pattern with Header, Implementation, and Footer sections
2. Keep functions focused on a single responsibility
3. Include comprehensive type hints
4. Write tests for all new functionality
5. Add appropriate exports to your package's `__init__.py`

## Contributing to the Template

If you'd like to improve the base template itself, contributions are welcome! Please make sure to:

1. Follow the Zeroth Law principles as outlined in `docs/ZerothLawAIFramework.py.md`
2. Add tests for new functionality
3. Ensure all tests pass before submitting a pull request
4. Update documentation as needed

## License

MIT License

## KNOWN ERRORS: None

## IMPROVEMENTS: Enhanced documentation with template usage instructions and customization guide.

## FUTURE TODOs: Add automated customization script, expand usage examples, and integrate automated documentation generation.
