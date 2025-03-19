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
    ]

    # Handle template files differently
    if metrics.get("is_template", False):
        report.extend([
            "Template File - Not Scored",
            "",
            "Basic Metrics:",
            f"  - Executable Lines: {metrics['executable_lines']}",
            f"  - Header/Footer Status: {metrics['header_footer_status']}"
        ])
        return "\n".join(report)

    # Regular file reporting
    report.extend([
        f"Overall Score: {metrics['overall_score']}/100 - {metrics['compliance_level']}",
        "",
        "File Metrics:",
        f"  - Total Lines: {metrics['total_lines']}",
        f"  - Header Lines: {metrics['header_lines']}",
        f"  - Footer Lines: {metrics['footer_lines']}",
        f"  - Effective Lines: {metrics['effective_lines']}",
        f"  - Executable Lines: {metrics['executable_lines']}",
        f"  - Header/Footer Status: {metrics['header_footer_status']}",
        f"  - Import Count: {metrics['import_count']}"
    ])

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

    # Filter out error files and template files
    valid_metrics = [m for m in all_metrics if "error" not in m]
    if not valid_metrics:
        return "Error analyzing all files."

    # Separate template and non-template files
    template_files = [m for m in valid_metrics if m.get("is_template", False)]
    scored_files = [m for m in valid_metrics if not m.get("is_template", False)]

    total_files = len(valid_metrics)
    total_scored_files = len(scored_files)

    # Calculate average score only for non-template files
    average_score = sum(m["overall_score"] for m in scored_files) / total_scored_files if scored_files else 0

    # Track files by compliance level
    compliance_files = {
        "Needs Improvement": [],
        "Adequate": [],
        "Good": [],
        "Excellent": []
    }

    for m in scored_files:
        level = m["compliance_level"]
        compliance_files[level].append({
            "file": m["file_path"],
            "score": m["overall_score"]
        })

    # Sort files within each category by score (ascending, so worst comes first)
    for level in compliance_files:
        compliance_files[level].sort(key=lambda x: x["score"])

    # Generate the report
    report = [
        "ZEROTH LAW SUMMARY REPORT",
        "==========================",
        f"Total Files Analyzed: {total_files}",
        f"Template Files: {len(template_files)}",
        f"Scored Files: {total_scored_files}",
    ]

    if scored_files:
        report.extend([
            f"Average Overall Score: {average_score:.2f}/100",
            "",
            "Compliance Distribution:",
        ])

        for level, files in compliance_files.items():
            count = len(files)
            if count > 0:
                report.append(f"  - {level}: {count} ({count/total_scored_files*100:.2f}%)")
                report.append("    Worst performing files:")
                # Show up to 3 worst files
                for i, file_info in enumerate(files[:3]):
                    report.append(f"      {i+1}. {file_info['file']} (Score: {file_info['score']:.1f})")
                report.append("")

    return "\n".join(report)