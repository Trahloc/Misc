"""
# PURPOSE: Configuration file for pytest to ensure proper import paths.

## DEPENDENCIES:
- pytest: For running tests.
- pathlib: For path operations.
- sys: For modifying import paths.

## TODO: None
"""

import sys
import os
import pytest
from pathlib import Path

# Add the project root directory to the Python path so tests can import modules
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
- Added path configuration to ensure tests can import from the project root directory.

## FUTURE TODOs:
- Consider adding fixture factories for common test cases.
"""