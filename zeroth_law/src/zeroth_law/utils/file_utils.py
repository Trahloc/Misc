"""
# PURPOSE: File operation utilities for the Zeroth Law analyzer.

## INTERFACES:
 - find_header_footer: Find header and footer in source code
 - count_executable_lines: Count executable lines of code
 - replace_footer: Replace footer in source code
 - get_line_range: Get line range for AST node
 - edit_file_with_black: Edit file with Black formatting for Python files
 - get_file_lines: Get lines from a file
 - is_ignored_file: Check if file should be ignored
 - get_file_size: Get file size in bytes

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
 - black
 - zeroth_law.utils.config
"""

import re
import logging
import os
import subprocess
import tempfile
import ast
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path

from zeroth_law.utils.config import load_config

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "max_executable_lines": 300,
    "max_function_lines": 30,
    "max_cyclomatic_complexity": 8,
    "max_parameters": 4,
    "max_line_length": 140,
    "max_locals": 15,
    "missing_header_penalty": 20,
    "missing_footer_penalty": 10,
    "missing_docstring_penalty": 2,
    "unused_import_penalty": 10,
    "ignore_patterns": [
        "**/__pycache__/**",
        "**/.git/**",
        "**/.venv/**",
        "**/venv/**",
        "**/*.pyc",
        "**/.pytest_cache/**",
        "**/.coverage",
        "**/htmlcov/**",
        ".*\\.egg-info.*",
    ],
}


def validate_against_config(content: str, file_path: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Validate content against configuration rules.

    Args:
        content (str): The content to validate
        file_path (str): Path to the file being validated
        config (Optional[Dict[str, Any]]): Configuration to use, or None to load from .zeroth_law.toml

    Returns:
        List[str]: List of validation warnings
    """
    if config is None:
        try:
            config = load_config(".zeroth_law.toml")
        except Exception as e:
            logger.warning(f"Failed to load config, using defaults: {e}")
            config = DEFAULT_CONFIG

    warnings = []

    # Count executable lines
    executable_lines = count_executable_lines(content)
    if executable_lines > config.get("max_executable_lines", 300):
        warnings.append(
            f"File {file_path} has {executable_lines} executable lines, " f"exceeding limit of {config['max_executable_lines']}"
        )

    try:
        # Parse the content and analyze functions
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check function lines
                start_line, end_line = get_line_range(node)
                func_lines = end_line - start_line + 1
                if func_lines > config.get("max_function_lines", 50):
                    warnings.append(f"Function {node.name} has {func_lines} lines, " f"exceeding limit of {config['max_function_lines']}")

                # Check parameters
                params = len(node.args.args)
                if params > config.get("max_parameters", 4):
                    warnings.append(f"Function {node.name} has {params} parameters, " f"exceeding limit of {config['max_parameters']}")
    except SyntaxError:
        logger.warning(f"Failed to parse {file_path} for function analysis")

    return warnings


def find_header_footer(content: str) -> Tuple[Optional[str], Optional[str]]:
    """Find header and footer in source code content.

    Args:
        content (str): The source code content to analyze

    Returns:
        Tuple[Optional[str], Optional[str]]: (header_content, footer_content) or (None, None) if not found
    """
    lines = content.splitlines()

    header = None
    footer = None

    # Find header
    header_start = -1
    header_end = -1
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        if line.strip().startswith("# PURPOSE:"):
            header_start = i
            # Find header end
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip().startswith("##") and not lines[j].strip().startswith("## INTERFACES:"):
                    header_end = j - 1
                    break
            if header_end == -1:  # If no explicit end found, look for end of docstring
                for j in range(i + 1, min(i + 10, len(lines))):
                    if '"""' in lines[j]:
                        header_end = j
                        break
            break

    if header_start != -1:
        header_end = header_end if header_end != -1 else header_start + 5  # Default to 5 lines if no end found
        header = "\n".join(lines[header_start : header_end + 1])

    # Find footer
    footer_start = -1
    footer_end = -1
    for i, line in enumerate(lines):  # Check all lines
        if line.strip().startswith("# ## KNOWN ERRORS:"):
            footer_start = i
        elif line.strip().startswith("# ## ZEROTH LAW COMPLIANCE:"):
            footer_end = i
            # Include any content after ZEROTH LAW COMPLIANCE up to the next non-comment line or end of file
            for j in range(i + 1, len(lines)):
                if j == len(lines) - 1:
                    footer_end = j
                    break
                if not lines[j].strip().startswith("#"):
                    footer_end = j - 1
                    break
            break

    if footer_start != -1 and footer_end != -1:
        footer = "\n".join(lines[footer_start : footer_end + 1])

    return header, footer


def count_executable_lines(content: str) -> int:
    """Count executable lines in source code content.

    This function counts actual executable lines, excluding:
    - Docstrings
    - Comments (both standalone and inline)
    - Blank lines
    - Decorators

    Args:
        content (str): The source code content to analyze

    Returns:
        int: Number of executable lines
    """
    config = load_config()
    max_executable_lines = config.get("max_executable_lines")

    lines = content.splitlines()
    executable_lines = 0
    in_docstring = False
    docstring_quotes = 0

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Handle docstrings
        if '"""' in line:
            docstring_quotes += line.count('"""')
            if docstring_quotes % 2 == 1:
                in_docstring = True
            else:
                in_docstring = False
            continue

        # Skip lines in docstrings
        if in_docstring:
            continue

        # Skip comment lines
        if line.startswith("#"):
            continue

        # Skip decorator lines
        if line.startswith("@"):
            continue

        # Remove inline comments
        if "#" in line:
            line = line[: line.index("#")].strip()
            if not line:
                continue

        executable_lines += 1

    return executable_lines


def replace_footer(content: str, new_footer: str) -> str:
    """Replace the existing footer sections in the content with the new footer.

    Args:
        content (str): The original source code content.
        new_footer (str): The new footer to replace or append.

    Returns:
        str: The updated content with the new footer.
    """
    has_header, has_footer = find_header_footer(content)

    logger.debug("Original content length: %d", len(content))
    logger.debug("Old footer found: %s", bool(has_footer))

    if has_footer:
        # Find the position of the old footer
        lines = content.splitlines()
        footer_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("# ## KNOWN ERRORS:"):
                footer_start = i
                break

        if footer_start != -1:
            # Keep everything before the old footer and append the new footer
            result = "\n".join(lines[:footer_start]) + "\n\n" + new_footer
            logger.debug("Updated content length: %d", len(result))
            return result

    # If no footer exists or footer not found, append the new one
    result = content.rstrip() + "\n\n" + new_footer
    logger.debug("Appended content length: %d", len(result))
    return result


def get_line_range(node) -> Tuple[int, int]:
    """Get the start and end line numbers for an AST node.

    Args:
        node: The AST node to get line numbers for.

    Returns:
        Tuple[int, int]: A tuple containing the start and end line numbers.
    """
    start_line = node.lineno
    end_line = getattr(node, "end_lineno", start_line)
    return start_line, end_line


def edit_file_with_black(file_path: str, content: str) -> str:
    """Edit content with Black formatting if it's a Python file.

    This function will:
    1. Check if the file is a Python file
    2. If it is, run Black formatting on the content
    3. Validate the formatted content against configuration rules
    4. Return the formatted content

    Args:
        file_path (str): Path to the file being edited (for extension check)
        content (str): The content to format

    Returns:
        str: The formatted content if it's a Python file, original content otherwise

    Raises:
        subprocess.CalledProcessError: If Black formatting fails
    """
    if not file_path.endswith(".py"):
        logger.debug(f"Skipping Black formatting for non-Python file: {file_path}")
        return content

    try:
        # Split content into code and footer
        lines = content.splitlines()
        code_lines = []
        footer_lines = []
        in_footer = False

        for line in lines:
            if line.strip().startswith("# ## ZEROTH LAW COMPLIANCE:"):
                in_footer = True
            if line.strip().startswith("# ## KNOWN ERRORS:"):
                in_footer = True

            if in_footer:
                footer_lines.append(line)
            else:
                code_lines.append(line)

        # Format only the code part
        code_content = "\n".join(code_lines)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code_content)
            tmp_path = tmp.name

        try:
            # Run Black on the temporary file
            subprocess.run(["black", "--quiet", tmp_path], check=True, capture_output=True)

            # Read the formatted content
            with open(tmp_path, "r") as f:
                formatted_code = f.read().rstrip()

            # Combine formatted code with footer
            if footer_lines:
                formatted_content = formatted_code + "\n\n" + "\n".join(footer_lines)
            else:
                formatted_content = formatted_code

            # Validate against configuration
            warnings = validate_against_config(formatted_content, file_path)
            for warning in warnings:
                logger.warning(warning)

            return formatted_content

        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {tmp_path}: {e}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Black formatting failed: {e}")
        if e.stdout:
            logger.error(f"Black output: {e.stdout.decode()}")
        if e.stderr:
            logger.error(f"Black errors: {e.stderr.decode()}")
        return content  # Return original content if formatting fails
    except Exception as e:
        logger.error(f"Error formatting {file_path} with Black: {e}")
        return content  # Return original content if formatting fails


def _format_code_block(code: str) -> str:
    """Format a block of Python code using Black.

    Args:
        code (str): The code block to format

    Returns:
        str: The formatted code block
    """
    if not code.strip():
        return code

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # Run Black on the temporary file
            subprocess.run(["black", "--quiet", tmp_path], check=True, capture_output=True)

            # Read the formatted content
            with open(tmp_path, "r") as f:
                return f.read().rstrip()

        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {tmp_path}: {e}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Black formatting failed: {e}")
        if e.stdout:
            logger.error(f"Black output: {e.stdout.decode()}")
        if e.stderr:
            logger.error(f"Black errors: {e.stderr.decode()}")
        return code  # Return original code if formatting fails
    except Exception as e:
        logger.error(f"Error formatting code block: {e}")
        return code  # Return original code if formatting fails


def get_file_lines(file_path: str) -> List[str]:
    """Get lines from a file.

    Args:
        file_path (str): Path to the file

    Returns:
        List[str]: List of lines in the file
    """
    with open(file_path, "r") as f:
        return f.readlines()


def is_ignored_file(file_path: str) -> bool:
    """Check if file should be ignored based on configuration.

    Args:
        file_path (str): Path to the file

    Returns:
        bool: True if file should be ignored
    """
    config = load_config()
    ignore_patterns = config.get("ignore_patterns", [])

    for pattern in ignore_patterns:
        if pattern in file_path:
            return True
    return False


def get_file_size(file_path: str) -> int:
    """Get file size in bytes.

    Args:
        file_path (str): Path to the file

    Returns:
        int: File size in bytes
    """
    return os.path.getsize(file_path)
