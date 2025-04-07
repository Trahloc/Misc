"""
# PURPOSE: Commands module initialization.

## INTERFACES:
 - test_coverage: Test coverage commands
 - check: System check commands
 - info: Project information command

## DEPENDENCIES: None
"""

from template_zeroth_law.commands.test_coverage import command as test_coverage_command
from template_zeroth_law.commands.test_coverage import command_create_test_stubs
from template_zeroth_law.commands.check import command as check_command
from template_zeroth_law.commands.info import command as info_command

__all__ = [
    "test_coverage_command",
    "command_create_test_stubs",
    "check_command",
    "info_command",
]

"""
## KNOWN ERRORS: None
## IMPROVEMENTS: Export commands for easy import
## FUTURE TODOs: Add more commands as needed
"""
