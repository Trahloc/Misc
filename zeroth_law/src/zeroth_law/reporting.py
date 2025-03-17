# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/reporting.py
"""
# PURPOSE: Generate reports for Zeroth Law analysis results.

## INTERFACES:
  - generate_report(metrics: dict) -> str: Generate a report for a single file.
  - generate_summary_report(all_metrics: list) -> str: Generate a summary report.

## DEPENDENCIES:
  - None
"""
from typing import Dict, List, Any

def generate_report(metrics: Dict[str, Any]) -> str:
    """Generates a human-readable report for a single file's analysis."""
    if "error" in metrics:
        return f"Error analyzing {metrics.get('file_path', 'file')}: {metrics['error']}"

    report = [
        "ZEROTH LAW ANALYSIS REPORT",
        "=========================",
        f"File: {metrics['file_path']}",
        f"Overall Score: {metrics['overall_score']}/100 - {metrics['compliance_level']}",
        "",
        "File Metrics:",
        f"  - Total Lines: {metrics['total_lines']}",
        f"  - Header Lines: {metrics['header_lines']}",
        f"  - Footer Lines: {metrics['footer_lines']}",
        f"  - Effective Lines: {metrics['effective_lines']}",
        f"  - Executable Lines: {metrics['executable_lines']}",
        f"  - Header/Footer Status: {metrics['header_footer_status']}",  # Changed metric
        f"  - Import Count: {metrics['import_count']}"
    ]

    if metrics["functions"]:
        report.append("")
        report.append("Function Metrics:")
        for func in metrics["functions"]:
            report.extend([
                f"  - {func['name']}:",
                f"    - Lines: {func['lines']}",
                f"    - Cyclomatic Complexity: {func['cyclomatic_complexity']}",
                f"    - Has Docstring: {func['has_docstring']}",
                f"    - Parameter Count: {func['parameter_count']}",
                f"    - Naming score: {func['naming_score']}",
            ])

    if metrics.get("penalties"):
        report.append("")
        report.append("Penalties:")
        for penalty in metrics["penalties"]:
            report.append(f"  - {penalty['reason']}: -{penalty['deduction']}")

    return "\n".join(report)


def generate_summary_report(all_metrics: List[Dict[str, Any]]) -> str:
    """Generates a summary report for multiple files."""
    if not all_metrics:
        return "No files analyzed."

    valid_metrics = [m for m in all_metrics if "error" not in m]
    if not valid_metrics:
        return "Error analyzing all files."

    total_files = len(valid_metrics)
    average_score = sum(m["overall_score"] for m in valid_metrics) / total_files

    compliance_counts = {}
    for m in valid_metrics:
        level = m["compliance_level"]
        compliance_counts[level] = compliance_counts.get(level, 0) + 1

    report = [
        "ZEROTH LAW SUMMARY REPORT",
        "==========================",
        f"Total Files Analyzed: {total_files}",
        f"Average Overall Score: {average_score:.2f}/100",
        "",
        "Compliance Distribution:",
    ]
    for level, count in compliance_counts.items():
        report.append(f"  - {level}: {count} ({count/total_files*100:.2f}%)")

    return "\n".join(report)