# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/utils.py
"""
# PURPOSE: Utility functions for the Zeroth Law analyzer.

## INTERFACES:
 - find_header_footer(source_code: str) -> tuple[str | None, str | None]: Get the header and the footer
 - count_executable_lines(content: str) -> int: Count executable lines
 - replace_footer(content: str, new_footer: str) -> str: Replace the existing footer

## DEPENDENCIES:
 None
"""
import re
from typing import Tuple


def find_header_footer(source_code: str) -> Tuple[str | None, str | None]:
    """Finds the Zeroth Law header and footer in the source code."""
    header_match = re.search(r'""".*?PURPOSE:.*?(""")', source_code, re.DOTALL)
    footer_match = re.search(
        r'""".*?ZEROTH LAW COMPLIANCE:.*?(""")', source_code, re.DOTALL
    )
    if not footer_match:  # Check for old style
        footer_match = re.search(
            r'""".*?(KNOWN ERRORS:|IMPROVEMENTS:|FUTURE TODOs:).*?(""")',
            source_code,
            re.DOTALL,
        )

    header = header_match.group(0) if header_match else None
    footer = footer_match.group(0) if footer_match else None

    return header, footer


def count_executable_lines(content: str) -> int:
    """
    Count only executable lines of code, excluding:
    - Comments (lines starting with # or containing only triple quotes)
    - Blank lines
    - Documentation blocks (lines between triple quotes)

    And including only:
    - Executable statements
    - Declarations
    - Braces
    - Imports
    """
    lines = content.split("\n")
    executable_count = 0
    in_docstring = False

    for line in lines:
        stripped = line.strip()

        # Skip blank lines
        if not stripped:
            continue

        # Check for docstring boundaries
        if '"""' in stripped:
            # Count occurrences of triple quotes
            quotes = stripped.count('"""')
            # Toggle docstring mode if odd number of triple quotes
            if quotes % 2 == 1:
                in_docstring = not in_docstring
            continue

        # Skip comments and lines inside docstrings
        if stripped.startswith("#") or in_docstring:
            continue

        # This is an executable line
        executable_count += 1

    return executable_count


def replace_footer(content: str, new_footer: str) -> str:
    """Replaces the existing footer sections in the content with the new footer."""
    _, old_footer = find_header_footer(content)

    if old_footer:
        # Check if a ZEROTH LAW COMPLIANCE section exists
        if "ZEROTH LAW COMPLIANCE:" in old_footer:
            return content.replace(old_footer, new_footer)  # Replace entire old footer

        # If no compliance section, replace existing sections, and append
        updated_content = content
        for section in ["KNOWN ERRORS:", "IMPROVEMENTS:", "FUTURE TODOs:"]:
            pattern = r'"""\s*' + section + r'.*?(""")'
            match = re.search(pattern, updated_content, re.DOTALL)
            if match:
                updated_content = updated_content.replace(
                    match.group(0), ""
                )  # Remove old

        # Remove last """ if exists
        updated_content = updated_content.rstrip()
        if updated_content.endswith('"""'):
            end_index = updated_content.rfind('"""')
            start_index = updated_content.rfind(
                '"""', 0, end_index
            )  # Find second to last
            if start_index != -1:  # Shouldn't happen, but just in case
                updated_content = updated_content[:start_index]
        return updated_content + "\n" + new_footer

    else:  # No footer
        return content + "\n" + new_footer
