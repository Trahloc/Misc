# FILE_LOCATION: {{cookiecutter.project_name}}/src/{{cookiecutter.project_name}}/__init__.py
"""
# PURPOSE: Exposes the public API for the {{ cookiecutter.project_name }} module.

## INTERFACES:
# - greet_user(name: str, formal: bool) -> str: Generates a greeting message.

## DEPENDENCIES:
# - {{ cookiecutter.project_name }}.greeter: Provides the greet_user function.
"""
from .greeter import greet_user

__all__ = [
    "greet_user",
]