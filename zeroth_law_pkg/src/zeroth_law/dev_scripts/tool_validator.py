"""Checks the availability of a tool in the uv-managed environment."""

import subprocess
import logging
from typing import Optional

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10 # Timeout for the which command

def is_tool_available(tool_name: str, timeout: Optional[int] = None) -> bool:
    """Checks if a tool is likely runnable via 'uv run which tool_name'.

    Args:
        tool_name: The name of the tool executable to check.
        timeout: Optional timeout in seconds for the subprocess call.
                 Defaults to DEFAULT_TIMEOUT.

    Returns:
        True if 'uv run which <tool_name>' succeeds (exit code 0),
        False otherwise (command fails, uv not found, timeout, etc.).
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    command = ["uv", "run", "--quiet", "--", "which", tool_name]
    log.debug(f"Checking tool availability: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # We check the return code manually
            timeout=timeout,
        )
        # Exit code 0 means the command was found
        if result.returncode == 0:
            log.debug(f"Tool '{tool_name}' found at: {result.stdout.strip()}")
            return True
        else:
            log.debug(f"Tool '{tool_name}' not found via 'uv run which' (exit code {result.returncode}).")
            return False

    except FileNotFoundError:
        log.error("Command 'uv' not found. Cannot check tool availability.")
        return False
    except subprocess.TimeoutExpired:
        log.warning(f"Command '{" ".join(command)}' timed out after {timeout}s.")
        return False
    except Exception as e:
        log.exception(f"Unexpected error checking availability for '{tool_name}': {e}")
        return False