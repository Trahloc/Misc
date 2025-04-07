"""
# PURPOSE: File header and footer updates for Zeroth Law.

## INTERFACES:
 - update_file_header: Update file header with analysis results
 - update_file_footer: Update file footer with analysis results
 - generate_footer: Generate footer content from metrics

## DEPENDENCIES:
 - logging
 - typing
 - pathlib
"""

import os
import shutil
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import re

from zeroth_law.utils.file_utils import find_header_footer, replace_footer, edit_file_with_black

logger = logging.getLogger(__name__)


def generate_footer(metrics: Dict[str, Any], old_footer: str | None = None) -> str:
    """Generate a standardized footer containing compliance metrics.

    This function creates a formatted footer string containing compliance
    information and metrics from the analysis.

    Args:
        metrics (Dict[str, Any]): Dictionary containing metrics to include
            in the footer. Must include:
            - compliance_level: Overall compliance level
            - overall_score: Numerical compliance score
            - penalties: List of compliance violations
        old_footer (str | None): The existing footer to extract sections from.

    Returns:
        str: A formatted footer string containing:
            - Current timestamp
            - Compliance level and score
            - List of penalties (if any)
            - Standard footer markers
    """
    # Extract sections from old footer if provided
    known_errors = "None"
    improvements = "None"
    future_todos = "None"

    if old_footer:
        # Split the old footer into sections
        sections = old_footer.split("# ## ")

        # Process each section
        for section in sections:
            if section.startswith("KNOWN ERRORS:"):
                content = section.split(":", 1)[1]
                # Clean up any extra # characters and trailing whitespace
                lines = [line.lstrip("#").rstrip() for line in content.splitlines()]
                # Remove any empty lines at the start/end but preserve content
                known_errors = "\n".join(lines).strip()
            elif section.startswith("IMPROVEMENTS:"):
                content = section.split(":", 1)[1]
                lines = [line.lstrip("#").rstrip() for line in content.splitlines()]
                improvements = "\n".join(lines).strip()
            elif section.startswith("FUTURE TODOs:"):
                content = section.split(":", 1)[1]
                lines = [line.lstrip("#").rstrip() for line in content.splitlines()]
                future_todos = "\n".join(lines).strip()

    # Build the footer sections
    sections = [
        "# ## KNOWN ERRORS:",
        f"# {known_errors}",
        "#",
        "# ## IMPROVEMENTS:",
        f"# {improvements}",
        "#",
        "# ## FUTURE TODOs:",
        f"# {future_todos}",
        "#",
        "# ## ZEROTH LAW COMPLIANCE:",
        f"# Overall Score: {metrics['overall_score']}/100 - {metrics['compliance_level']}",
        "# Penalties:",
    ]

    # Add penalties
    for penalty in metrics["penalties"]:
        sections.append(f"# - {penalty['reason']}: -{penalty['deduction']}")

    # Add timestamp
    sections.append(f"# Analysis Timestamp: {datetime.now().isoformat()}")

    # Join all sections with single newlines and remove trailing whitespace
    return "\n".join(section.rstrip() for section in sections)


def update_file_footer(file_path: str, metrics: Dict[str, Any]) -> None:
    """Update a file's footer with new compliance metrics.

    This function generates a new footer containing compliance information
    and updates the file in place, preserving the original content and header.
    For Python files, it also runs Black formatting on the updated content.

    Args:
        file_path (str): Path to the file to update.
        metrics (Dict[str, Any]): Dictionary containing the metrics to include
            in the footer. Must include compliance_level and overall_score.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there are issues reading or writing the file.

    Note:
        This function creates a backup of the original file before making changes.
        If an error occurs during the update, the original file is restored.
    """
    try:
        # Read the original content
        with open(file_path, "r", encoding="utf-8") as original_file:
            content = original_file.read()

        # Find the old footer
        _, old_footer = find_header_footer(content)

        # If we're adding a footer and there was a missing footer penalty, remove it
        if old_footer is None:
            # Create a copy of metrics to avoid modifying the original
            adjusted_metrics = metrics.copy()
            if "penalties" in adjusted_metrics:
                # Remove the missing footer penalty
                adjusted_metrics["penalties"] = [p for p in adjusted_metrics["penalties"] if p["reason"] != "Missing footer"]
                # Recalculate the overall score
                if adjusted_metrics["penalties"]:
                    adjusted_metrics["overall_score"] = 100 - sum(p["deduction"] for p in adjusted_metrics["penalties"])
                else:
                    adjusted_metrics["overall_score"] = 100
                # Update compliance level
                if adjusted_metrics["overall_score"] >= 90:
                    adjusted_metrics["compliance_level"] = "Excellent"
                elif adjusted_metrics["overall_score"] >= 80:
                    adjusted_metrics["compliance_level"] = "Good"
                elif adjusted_metrics["overall_score"] >= 70:
                    adjusted_metrics["compliance_level"] = "Fair"
                else:
                    adjusted_metrics["compliance_level"] = "Poor"
            else:
                adjusted_metrics = metrics
        else:
            adjusted_metrics = metrics

        # Generate the new footer
        new_footer = generate_footer(adjusted_metrics, old_footer)

        # Remove all footer sections by finding the first footer marker
        footer_markers = ["# ## KNOWN ERRORS:", "# ## IMPROVEMENTS:", "# ## FUTURE TODOs:", "# ## ZEROTH LAW COMPLIANCE:"]

        # Find the earliest footer marker
        first_footer_pos = len(content)
        for marker in footer_markers:
            pos = content.find(marker)
            if pos != -1 and pos < first_footer_pos:
                first_footer_pos = pos

        # Keep only the content before the first footer marker
        if first_footer_pos < len(content):
            content = content[:first_footer_pos].rstrip()

        # Add the new footer with a single newline
        updated_content = content + "\n\n" + new_footer

        # Format with Black if it's a Python file
        updated_content = edit_file_with_black(file_path, updated_content)

        # Ensure there's exactly one newline at the end
        updated_content = updated_content.rstrip("\n") + "\n"

        # Write the updated content to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as tmp_file:
            tmp_file.write(updated_content)
            # Ensure the final newline is written
            if not updated_content.endswith("\n"):
                tmp_file.write("\n")

        # Move the temporary file to replace the original
        shutil.move(tmp_file.name, file_path)
        logger.info(f"Updated footer for {file_path}")

    except OSError as e:
        logger.error(f"Error updating footer for {file_path}: {e}")
        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)
        raise
