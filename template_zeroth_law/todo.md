# Template Zeroth Law Refinement Plan

## Purpose
This document outlines how to refine the `template_zeroth_law` project into a minimal but complete scaffold that will serve as the foundation for the cookiecutter template used by 95%+ of Zeroth Law projects throughout their lifecycle.

## Forever TODOs (evaluated every time code or tasks are changed)

[∞] [Critical] Follow the Zeroth Law defined in [ZerothLawAIFramework.py.md](/docs/ZerothLawAIFramework.py.md)

[∞] [High] After completing any task:
    • Mark the task as done in todo.md
    • Add notes if anything unexpected happened

[∞] [Medium] When adding or changing a feature:
    • Check if it violates the Single Responsibility Principle (SRP)
    • If it does, create a new TODO: "[Refactor] Split [feature_name] to follow SRP"

[∞] [High] For every feature in the codebase:
    • Check if there is a pytest for it
    • If missing, create a TODO: "[Test] Write pytest for [feature_name]"

## Implementation Checklist

### Understanding the Template's Role
- [✓] Template provides universal file structure and minimal implementation examples
- [✓] Structure prepared for conversion to a cookiecutter template
- [✓] Design allows content to be heavily customized by users

### Core Structure (Keep)
- [✓] Basic project layout following section 6.2 in the framework:
  - [✓] `pyproject.toml`
  - [✓] `.pre-commit-config.yaml`
  - [✓] `src/package_name/`
  - [✓] `tests/`
- [✓] `README.md` with minimal but sufficient getting started instructions
- [✓] `docs/ZerothLawAIFramework.py.md` for reference

### Core Functionality (Keep)
- [✓] Base error handling framework (`exceptions.py` with `ZerothLawError`)
- [✓] Minimal CLI framework with basic entry point and testable commands
- [✓] Simple configuration management
- [✓] Package exports in `__init__.py`
- [✓] Basic test examples demonstrating proper testing patterns

## Simplifications Implemented

### 1. Base Error System
- [✓] Kept `ZerothLawError` as the foundational class
- [✓] Included only 3 canonical exception examples (ConfigError, ValidationError, FileError)
- [✓] Removed domain-specific error types

### 2. CLI Structure
- [✓] Kept a minimal but functional CLI with 2 example commands (hello, init)
- [✓] Ensured commands are testable with pytest
- [✓] Included proper error handling for CLI functions
- [✓] Implemented proper docstrings following 5.5 (Pre/Post conditions)
- [✓] Focused on the pattern rather than complex functionality

### 3. Configuration
- [✓] Kept minimal config loading code as an example
- [✓] Simplified implementation while maintaining core functionality
- [✓] Added proper testing for configuration

### Removed Components
- [✓] Excessive error types that were application-specific
- [✓] Complex CLI commands beyond basic examples
- [✓] Domain-specific logic
- [✓] Redundant documentation

## Remaining Tasks

### Medium Priority
- [ ] Update README.md to clearly explain this is a scaffold for cookiecutter
- [ ] Create brief examples showing ideal usage patterns
- [ ] Ensure all components are properly connected (imports, etc.)

### Low Priority
- [ ] Add comments explaining which parts are meant to be customized vs. kept
- [ ] Check for consistency in naming conventions
- [ ] Verify pre-commit hooks cover all required checks

## Clean Up
The following files should be moved to a trash folder for removal:

### Files to Remove (Move to `/home/trahloc/code/Misc/template_zeroth_law/trash/`)
- Duplicate or excessive exception types
- Any domain-specific modules not part of the universal scaffold
- Redundant documentation files
- Complex CLI implementation files beyond the simplified version

## Success Criteria
- [✓] Every file serves a clear, universal purpose aligned with the framework
- [✓] Documentation is minimal but sufficient
- [✓] Testing demonstrates key principles from section 5.5 (Strategic Assertions, Pre/Post conditions)
- [✓] The structure demonstrates core principles from sections 1-6 of the framework
- [✓] Converting to cookiecutter requires no structural changes

## Conclusion
The template now represents a better balance between minimalism and completeness - providing just enough structure and examples to guide projects while avoiding anything project-specific or overly complex.
