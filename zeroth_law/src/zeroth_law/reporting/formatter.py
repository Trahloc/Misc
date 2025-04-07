"""
# PURPOSE: Format compliance reports and metrics for Zeroth Law.

## INTERFACES:
 - format_file_metrics: Format file-level metrics
 - format_function_metrics: Format function-level metrics
 - format_compliance_report: Format detailed compliance report
 - format_summary_report: Format summary report

## DEPENDENCIES:
 - logging
 - typing
 - tabulate
"""

from typing import Dict, List, Any


def format_file_metrics(metrics: Dict[str, Any]) -> str:
    """Format the file-level metrics into a readable string.

    Args:
        metrics (Dict[str, Any]): The file metrics to format.

    Returns:
        str: A formatted string of file metrics.
    """
    file_metrics = [
        "File Metrics:",
        f"  - Total Lines: {metrics['total_lines']}",
        f"  - Header Lines: {metrics['header_lines']}",
        f"  - Footer Lines: {metrics['footer_lines']}",
        f"  - Effective Lines: {metrics['effective_lines']}",
        f"  - Executable Lines: {metrics['executable_lines']}",
        f"  - Header/Footer Status: {metrics['header_footer_status']}",
        f"  - Import Count: {metrics['import_count']}",
    ]

    return "\n".join(file_metrics)


def format_function_metrics(functions: List[Dict[str, Any]]) -> str:
    """Format the function-level metrics into a readable string.

    Args:
        functions (List[Dict[str, Any]]): List of function metrics to format.

    Returns:
        str: A formatted string of function metrics.
    """
    if not functions:
        return ""

    func_metrics = ["Function Metrics:"]
    for func in functions:
        metrics = func.get("metrics", {})
        func_metrics.extend(
            [
                f"  - {func['name']}:",
                f"    - Lines: {metrics.get('lines', 0)}",
                f"    - Cyclomatic Complexity: {metrics.get('cyclomatic_complexity', 0)}",
                f"    - Has Docstring: {metrics.get('has_docstring', False)}",
                f"    - Parameter Count: {metrics.get('parameter_count', 0)}",
                f"    - Naming score: {metrics.get('naming_score', 0)}",
            ]
        )

    return "\n".join(func_metrics)


def format_compliance_report(metrics: Dict[str, Any]) -> str:
    """Generate a human-readable report for a single file's analysis.

    Args:
        metrics (Dict[str, Any]): The analysis metrics for a file.

    Returns:
        str: A formatted report string.
    """
    if "error" in metrics:
        return f"Error analyzing {metrics.get('file_path', 'file')}: {metrics['error']}"

    report = [
        "ZEROTH LAW ANALYSIS REPORT",
        "=========================",
        f"File: {metrics['file_path']}",
    ]

    # Handle template files differently
    if metrics.get("is_template", False):
        report.extend(
            [
                "Template File - Not Scored",
                "",
                "Basic Metrics:",
                f"  - Executable Lines: {metrics['executable_lines']}",
                f"  - Header/Footer Status: {metrics['header_footer_status']}",
            ]
        )
        return "\n".join(report)

    # Regular file reporting
    report.extend(
        [
            f"Overall Score: {metrics['overall_score']}/100 - {metrics['compliance_level']}",
            "",
        ]
    )

    # Add file metrics
    report.append(format_file_metrics(metrics))

    # Add function metrics if available
    if metrics["functions"]:
        report.append("")
        report.append(format_function_metrics(metrics["functions"]))

    # Add penalties if available
    if metrics.get("penalties"):
        report.append("")
        report.append("Penalties:")
        for penalty in metrics["penalties"]:
            report.append(f"  - {penalty['reason']}: -{penalty['deduction']}")

    return "\n".join(report)


def format_summary_report(results: Dict[str, Any]) -> str:
    """Generate a summary report for multiple files.

    Args:
        results (Dict[str, Any]): Analysis results containing files and metrics.

    Returns:
        str: A formatted summary report string.
    """
    if not results["files"]:
        return "No files analyzed."

    metrics = results["metrics"]
    report = [
        "ZEROTH LAW SUMMARY REPORT",
        "========================",
        "",
        f"Total Files Analyzed: {metrics['total_files']}",
        f"Total Functions: {metrics['total_functions']}",
        f"Total Lines of Code: {metrics['total_lines']}",
        f"Average Overall Score: {metrics['average_score']:.2f}/100",
        f"Files with Issues: {metrics['files_with_issues']}",
        "",
    ]

    if metrics["common_issues"]:
        report.extend(
            [
                "Common Issues:",
                *[f"  - {issue}: {count}" for issue, count in metrics["common_issues"].items()],
                "",
            ]
        )

    # Add file details
    report.extend(
        [
            "File Details:",
            *[f"  - {f['path']}: {f['results']['overall_score']}/100" for f in results["files"]],
        ]
    )

    return "\n".join(report)
