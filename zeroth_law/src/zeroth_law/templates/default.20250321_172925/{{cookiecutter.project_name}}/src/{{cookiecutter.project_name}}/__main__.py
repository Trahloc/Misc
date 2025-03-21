# FILE_LOCATION: {{ cookiecutter.project_name }}/src/{{ cookiecutter.project_name }}/__main__.py
"""
# PURPOSE: Entry point for the {{ cookiecutter.project_name }} package.

## INTERFACES:
 # main(): executes the main function from cli.py

## DEPENDENCIES:
 - {{ cookiecutter.project_name }}.cli
"""
from {{ cookiecutter.project_name }}.cli import main

if __name__ == "__main__":
    main()