# FILE_LOCATION: {{ cookiecutter.project_name }}/src/{{ cookiecutter.project_name }}/__main__.py
"""
# PURPOSE: Entry point for the zeroth_law_template package.

## INTERFACES:
 # main(): executes the main function from cli.py

## DEPENDENCIES:
 - zeroth_law_template.cli
"""
from {{ cookiecutter.project_name }}.cli import main

if __name__ == "__main__":
    main()