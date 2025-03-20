# FILE_LOCATION: hfais/src/hfais/__init__.py
"""
# PURPOSE: Exposes the public API for the hfais module.

## INTERFACES:
# - greet_user(name: str, formal: bool) -> str: Generates a greeting message.

## DEPENDENCIES:
# - hfais.greeter: Provides the greet_user function.
"""
from .greeter import greet_user

__all__ = [
    "greet_user",
]