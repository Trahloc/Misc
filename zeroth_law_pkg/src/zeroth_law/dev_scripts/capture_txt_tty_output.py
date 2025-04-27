#!/usr/bin/env python3
# FILE: scripts/capture_raw_tty_output.py
"""
# PURPOSE: Executes a command within a pseudo-terminal (PTY) to capture its
#          raw output, mimicking what a user would see in an interactive terminal.
"""

import argparse
import fcntl
import logging
import os
import pty
import select
import shlex
import struct
import subprocess
import sys
import termios
from pathlib import Path
from typing import Final, List, Tuple

# --- CONSTANTS ---
PTY_READ_TIMEOUT: Final[float] = 1.0  # Seconds to wait for pty output
PTY_BUFFER_SIZE: Final[int] = 1024  # Bytes to read at a time
DEFAULT_TERM_ROWS: Final[int] = 24
DEFAULT_TERM_COLS: Final[int] = 80

# --- LOGGING ---
# Configure basic logging for script execution feedback
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


def capture_tty_output(
    command: List[str], rows: int = DEFAULT_TERM_ROWS, cols: int = DEFAULT_TERM_COLS
) -> Tuple[bytes, int]:
    """Executes a command in a pseudo-terminal (pty) and captures raw byte output."""
    command_str = " ".join(shlex.quote(c) for c in command)
    log.info(f"Executing command in PTY ({rows}x{cols}): {command_str}")

    # Create a pseudo-terminal
    master_fd, slave_fd = pty.openpty()

    # Set terminal size
    try:
        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, size)
        log.info(f"Set PTY size to {rows} rows, {cols} columns.")
    except (NameError, ImportError, OSError, termios.error) as e:
        log.warning(f"Could not set pty size (continuing with default): {e}")

    process = None
    output_bytes = b""
    exit_code = -1  # Default error code

    try:
        # Set COLUMNS env var as another attempt to influence width
        # Also set TERM, as some tools check this
        env = os.environ.copy()
        env["COLUMNS"] = str(cols)
        env["LINES"] = str(rows)
        env["TERM"] = os.environ.get("TERM", "xterm")  # Use current TERM or default

        # Start the process with stdin, stdout, stderr connected to the slave pty
        process = subprocess.Popen(
            command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            # preexec_fn=os.setsid # Optional: run in new session
        )

        # Close the slave fd in the parent process, it's used by the child
        os.close(slave_fd)
        slave_fd = -1  # Mark as closed

        # Read output from the master fd until the process finishes
        while True:
            # Wait for data to be available on master_fd or timeout
            readable, _, _ = select.select([master_fd], [], [], PTY_READ_TIMEOUT)
            if master_fd in readable:
                try:
                    data = os.read(master_fd, PTY_BUFFER_SIZE)
                    if not data:  # EOF
                        # DEBUG: Print EOF signal
                        # print("DEBUG: Received EOF from PTY", file=sys.stderr)
                        break
                    # DEBUG: Print raw bytes read
                    # print(f"RAW PTY READ: {data!r}", file=sys.stderr)
                    output_bytes += data
                except OSError:  # EIO means slave PTY has been closed
                    # DEBUG: Print EIO signal
                    # print("DEBUG: Received OSError (EIO) from PTY read", file=sys.stderr)
                    break
            else:
                # Timeout, check if process is still alive
                # DEBUG: Print timeout signal
                # print("DEBUG: PTY read timeout", file=sys.stderr)
                if process.poll() is not None:
                    # DEBUG: Print process ended signal
                    # print("DEBUG: Process ended during timeout check", file=sys.stderr)
                    break  # Process ended

        # Wait for the process to terminate fully and get exit code
        log.info("Waiting for process to terminate...")
        process.wait(timeout=PTY_READ_TIMEOUT * 2)  # Add a timeout here too
        exit_code = process.returncode
        log.info(f"Process terminated with exit code: {exit_code}")

    except FileNotFoundError:
        log.error(f"Command not found: {command[0]}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        log.error("Process timed out during final wait.")
        if process:
            process.terminate()
            process.wait()
        exit_code = -2  # Specific timeout error code
    except Exception as e:
        log.error(f"Error executing command in PTY: {e}")
        # Ensure cleanup happens in finally block
        if process and process.poll() is None:
            process.terminate()
            process.wait()
        exit_code = -1  # Indicate general error
    finally:
        # Ensure file descriptors are closed
        if master_fd is not None and master_fd != -1:
            try:
                os.close(master_fd)
            except OSError:
                pass
        if slave_fd is not None and slave_fd != -1:  # Should be closed already, but double check
            try:
                os.close(slave_fd)
            except OSError:
                pass

    log.info(f"Captured {len(output_bytes)} bytes from PTY.")
    return output_bytes, exit_code


def main():
    parser = argparse.ArgumentParser(description="Capture raw TTY-like output from a command using a pseudo-terminal.")
    parser.add_argument(
        "command",
        help="The command string to execute (e.g., 'ls -l', 'coverage report --help').",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default=None,
        help="Optional file path to save the raw decoded output.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=DEFAULT_TERM_ROWS,
        help=f"Terminal rows for PTY (default: {DEFAULT_TERM_ROWS})",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=DEFAULT_TERM_COLS,
        help=f"Terminal columns for PTY (default: {DEFAULT_TERM_COLS})",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding to use for decoding the raw byte output (default: utf-8).",
    )
    parser.add_argument(
        "--encoding-errors",
        default="replace",
        choices=["strict", "ignore", "replace"],
        help="How to handle decoding errors (default: replace).",
    )

    args = parser.parse_args()

    # Split the command string safely
    command_list = shlex.split(args.command)
    if not command_list:
        log.error("Empty command provided.")
        sys.exit(1)

    # Capture raw bytes and exit code
    raw_bytes, exit_code = capture_tty_output(command_list, args.rows, args.cols)

    # Decode the output
    decoded_output = ""
    if raw_bytes:
        try:
            decoded_output = raw_bytes.decode(args.encoding, errors=args.encoding_errors)
            # Minimal normalization: replace TTY carriage returns
            decoded_output = decoded_output.replace("\r\n", "\n").replace("\r", "\n")
            log.info(f"Successfully decoded {len(raw_bytes)} bytes using {args.encoding}.")
        except Exception as e:
            log.error(f"Failed to decode output using {args.encoding}: {e}")
            # Optionally, print raw bytes representation if decoding fails?
            # print(f"Raw bytes were: {raw_bytes!r}", file=sys.stderr)
            exit_code = -3  # Specific decoding error code
    else:
        log.info("No bytes captured from PTY output.")

    # Print to stdout
    if decoded_output:
        print(decoded_output, end="")  # Avoid adding extra newline

    # Save to file if requested
    if args.output_file:
        log.info(f"Saving decoded output to: {args.output_file}")
        try:
            args.output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output_file, "w", encoding=args.encoding) as f:  # Use specified encoding for writing
                f.write(decoded_output)
            log.info("Successfully saved output to file.")
        except IOError as e:
            log.error(f"Error writing output file {args.output_file}: {e}")
            # Should this affect the exit code?
            # exit_code = -4

    # Exit with the command's exit code (or an error code from this script)
    # Ensure non-negative exit code for shell interpretation
    sys.exit(max(0, exit_code))


if __name__ == "__main__":
    main()
