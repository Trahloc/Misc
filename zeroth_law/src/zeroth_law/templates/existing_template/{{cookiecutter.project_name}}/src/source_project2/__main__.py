# FILE_LOCATION: source_project2/src/source_project2/__main__.py
"""
# PURPOSE: Entry point for the source_project2 package.

## INTERFACES:
 # main(): executes the main function from cli.py

## DEPENDENCIES:
 - source_project2.cli
"""
from {{ cookiecutter.project_name }}.cli import main

if __name__ == "__main__":
    main()