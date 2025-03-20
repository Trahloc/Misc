# Zeroth Law Template - TODO List

## Eternal Reminders
- [∞] Reminder that this project exists to be a template for future Zeroth Law based projects

## Current Issues
- [ ] Review and resolve any existing issues in the codebase to ensure stability.

## Testing
- [ ] Create sample tests for each essential command to demonstrate best practices.
- [ ] Add fixtures for common testing scenarios to reduce duplication and standardize test setup.
- [ ] Consider adding property-based testing examples to improve code robustness.

## Future Enhancements
- [ ] Add schema validation for configuration files to prevent configuration errors.
- [ ] Implement dynamic config reloading to apply changes without restarting the application.
- [ ] Add support for encrypted secrets to securely manage sensitive information.
- [ ] Enhance environment variable parsing to improve reliability and usability.

## Documentation
- [ ] Update README.md with configuration examples to help users understand setup.
- [ ] Add documentation about configuration file formats and precedence to clarify how settings are applied.
- [ ] Document environment variable configuration options to explain naming patterns and available options.
- [ ] Create a CONTRIBUTING.md file to provide clear guidelines for contributions.

## Project Structure and Files
- [ ] Add a Makefile with common development tasks to simplify project management.
- [ ] Ensure .pre-commit-config.yaml is comprehensive and up-to-date for code quality enforcement.
- [ ] Add .gitignore templates for common IDE files to keep the repository clean.
- [ ] Consider adding a .github directory with workflow templates for CI/CD processes.

## Configuration and Features
- [ ] Add command discovery mechanism to allow new commands to be added easily.
- [ ] Implement command group management for larger projects to improve organization.

## Design Philosophy
- [ ] Document which files are essential vs. optional to help users tailor the template to their needs.
- [ ] Explain the rationale behind the template structure to provide context for design decisions.

## Completed Changes
- [x] Fixed the structure of DEFAULT_CONFIG to put limit settings in a nested 'limits' dictionary.
- [x] Fixed invalid JSON error handling in load_config to properly raise ValueError.
- [x] Ensured Config.__getitem__ handles nested attributes correctly.
- [x] Added proper docstrings to all functions according to project standards.
- [x] Fixed failing test_load_config_invalid_json test.
- [x] Created .markdownlint.yaml for markdown linting.
- [x] Created zeroth_law_template.toml project-specific config file.
- [x] Verified pytest.ini is configured to use ~/.cache/python/pytest_cache/zeroth_law_template.
- [x] Removed example-specific files (greeter.py, hello.py).
- [x] Enhanced the info.py command to be more useful.
- [x] Updated commands/__init__.py to include only essential commands.
- [x] Modified cli.py to use configuration properly.
- [x] Ensured all config tests pass successfully.