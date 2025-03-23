"""
# PURPOSE: Exposes CLI commands as a module

## INTERFACES:
 - version.command: Implements the version command
 - check.command: Implements the check command
 - info.command: Implements the info command
 - test_coverage.command_test_coverage: Implements the test-coverage command
 - test_coverage.command_create_test_stubs: Implements the create-test-stubs command

## DEPENDENCIES:
 - .version: Version command implementation
 - .check: System check command implementation
 - .info: Info command implementation
 - .test_coverage: Test coverage and test stub generation implementation
"""
from . import version
from . import check
from . import info
from . import test_coverage

__all__ = ['version', 'check', 'info', 'test_coverage']
"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Explicit exports
 - Updated to include only essential commands 
 - Removed example-specific commands
 - Added test coverage commands

## FUTURE TODOs:
 - Consider command discovery mechanism for plugin-like architecture
"""
