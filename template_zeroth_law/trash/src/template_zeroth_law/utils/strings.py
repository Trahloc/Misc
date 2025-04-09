"""
PURPOSE: String utility functions for the Zeroth Law template.

INTERFACES:
    - sanitize_filename: Makes a string safe to use as a filename.

DEPENDENCIES:
    - os, re
"""

import os
import re


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    PURPOSE: Make a string safe to use as a filename.

    Args:
        filename: The string to sanitize.
        replacement: Character to replace invalid characters with.

    Returns:
        str: A sanitized string that can be safely used as a filename.

    Example:
        sanitize_filename("Hello: World?")
        'Hello_World_'
    """
    # Get the list of invalid characters for the current OS
    if os.name == "nt":  # Windows
        # Windows has more restrictions
        invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    else:  # Unix-like
        invalid_chars = r"[/\x00]"

    # Replace invalid characters
    sanitized = re.sub(invalid_chars, replacement, filename)

    # Handle reserved filenames on Windows
    if os.name == "nt":
        # Windows reserved filenames (CON, PRN, AUX, etc.)
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]

        name_without_ext, ext = os.path.splitext(sanitized)
        if name_without_ext.upper() in reserved_names:
            sanitized = f"{name_without_ext}{replacement}{ext}"

    # Ensure the filename doesn't start or end with spaces or periods
    # (can cause issues on various operating systems)
    sanitized = sanitized.strip(" .")

    # Handle empty filenames
    if not sanitized:
        sanitized = "unnamed_file"

    return sanitized
