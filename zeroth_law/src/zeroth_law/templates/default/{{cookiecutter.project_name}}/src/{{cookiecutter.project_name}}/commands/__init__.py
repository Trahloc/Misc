"""
# PURPOSE: Exposes CLI commands as a module

## INTERFACES:
 - hello.command: Implements the hello command
 - info.command: Implements the info command

## DEPENDENCIES:
 - .hello: Hello command implementation
 - .info: Info command implementation
"""
from . import hello
from . import info

__all__ = ['hello', 'info']
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Explicit exports
 - Clear module documentation

## FUTURE TODOs:
 - Consider command discovery mechanism
"""
