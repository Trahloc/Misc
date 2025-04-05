"""
Plugin loader cleanup utility.

This module helps ensure problematic pytest plugins do not get loaded
by cleaning up sys.modules and other module references.
"""

import sys
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_problematic_modules():
    """
    Remove problematic modules from sys.modules.

    This function cleans up any modules that might cause issues with pytest,
    ensuring they don't interfere with test execution.
    """
    problematic_prefixes = ["_external_plugin", "problematic_plugin"]

    # Clean up sys.modules
    for module_name in list(sys.modules.keys()):
        for prefix in problematic_prefixes:
            if module_name.startswith(prefix):
                sys.modules.pop(module_name, None)
                logger.info(f"Removed {module_name} from sys.modules")

    # Clean up site-packages directory for any temporary files
    try:
        import site

        site_packages = Path(site.getsitepackages()[0])
        temp_files = [
            # No need to reference specific problematic files here
        ]

        for file in temp_files:
            if file.exists():
                logger.warning(f"Found problematic file: {file}")
    except Exception as e:
        logger.warning(f"Error checking site-packages: {e}")

    return True


# Run cleanup when the module is imported
cleanup_result = cleanup_problematic_modules()
logger.info(f"Cleanup completed: {cleanup_result}")
