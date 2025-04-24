"""Utilities for running subprocesses."""

import logging
import shlex
import subprocess
from typing import Sequence

log = logging.getLogger(__name__)


def run_subprocess_no_check(
    command: Sequence[str] | str,
    capture: bool = True,
    as_text: bool = True,
    timeout_seconds: int | None = 60,
    use_shell: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Runs a subprocess, capturing output by default, without raising on error.

    Args:
    ----
        command: The command sequence or string (if use_shell=True).
        capture: Whether to capture stdout/stderr (default True).
        as_text: Whether to decode stdout/stderr as text (default True).
        timeout_seconds: Optional timeout in seconds (default 60).
        use_shell: Whether to run the command via the shell (default False).
        **kwargs: Additional arguments passed to subprocess.run.

    Returns:    -------
        The CompletedProcess object.
    """
    cmd_str = command if isinstance(command, str) else shlex.join(command)
    log.debug(f"Running subprocess (no check): {cmd_str}")
    try:
        result = subprocess.run(
            command,
            capture_output=capture,
            text=as_text,
            check=False,  # Explicitly set check=False
            shell=use_shell,
            timeout=timeout_seconds,
            errors="replace",  # Handle potential decoding errors
            **kwargs,
        )
        if result.returncode != 0:
            log.debug(
                f"Subprocess finished with non-zero exit code {result.returncode}. "
                f"Stderr: {result.stderr.strip() if result.stderr else '[None]'}"
            )
        return result
    except subprocess.TimeoutExpired as e:
        log.warning(f"Subprocess timed out after {timeout_seconds}s: {cmd_str}")
        # Re-raise or return a custom CompletedProcess object indicating timeout?
        # For now, re-raising to make timeout explicit.
        raise e
    except Exception as e:
        log.exception(f"Unexpected error running subprocess: {cmd_str}")
        # Re-raise to indicate a fundamental issue with the subprocess call itself.
        raise e
