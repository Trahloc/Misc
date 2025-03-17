# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/templates/__main__.py.template
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