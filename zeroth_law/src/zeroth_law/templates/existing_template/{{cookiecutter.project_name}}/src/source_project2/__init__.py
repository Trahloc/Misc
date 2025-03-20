# FILE_LOCATION: source_project2/src/source_project2/__init__.py
"""
# PURPOSE: Exposes the public API for the source_project2 module.

## INTERFACES:
# - greet_user(name: str, formal: bool) -> str: Generates a greeting message.

## DEPENDENCIES:
# - source_project2.greeter: Provides the greet_user function.
"""
from .greeter import greet_user

__all__ = [
    "greet_user",
]