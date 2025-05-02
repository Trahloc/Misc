"""Core logic for the ZLT audit command."""

import json
import structlog
from pathlib import Path
from typing import Any, Dict, List, Tuple

import click

# Assuming imports are relative to 'src'
from zeroth_law.analysis_runner import (
    analyze_files,
    format_violations_as_json,
    log_violations_as_text,
    run_all_checks,  # Placeholder
)
from zeroth_law.analyzers.precommit_analyzer import analyze_precommit_config
from zeroth_law.file_processor import find_files_to_audit

log = structlog.get_logger()


def _run_audit_logic(
    config: Dict[str, Any],
    verbosity: int,  # Keep verbosity if needed by logic
    project_root: Path | None,
    paths_cli: tuple[Path, ...],
    recursive_cli: bool | None,
    output_json_cli: bool,
) -> int:
    """Performs the audit analysis and returns an exit code."""
    exit_code = 0
    all_violations: Dict[Path, Dict[str, List[Any]]] = {}
    combined_stats: Dict[str, int] = {
        "files_analyzed": 0,
        "files_with_violations": 0,
        "compliant_files": 0,
        "configs_analyzed": 0,
        "configs_with_violations": 0,
    }

    try:
        # Determine paths and recursive flag
        paths_to_check: list[Path]
        if paths_cli:
            paths_to_check = list(paths_cli)
            log.debug(f"Using paths provided via CLI: {paths_to_check}")
        else:
            default_paths = config.get("audit", {}).get("paths", ["."])
            paths_to_check = [Path(p) for p in default_paths]
            log.debug(f"Using default/configured paths: {paths_to_check}")

        if recursive_cli is None:
            recursive = config.get("audit", {}).get("recursive", True)
            log.debug(f"Using default/configured recursive setting: {recursive}")
        else:
            recursive = recursive_cli
            log.debug(f"Using recursive setting from CLI: {recursive}")

        log.info(f"Starting audit on paths: {paths_to_check} (Recursive: {recursive})")

        # Analyze Source Files
        analyzer_func = run_all_checks
        files_to_audit = find_files_to_audit(paths_to_check, recursive, config)
        log.info(f"Found {len(files_to_audit)} source files to analyze.")

        if not files_to_audit:
            log.info("No source files found to audit.")
        else:
            violations_by_file, stats = analyze_files(files_to_audit, config, analyzer_func)
            all_violations.update(violations_by_file)
            combined_stats["files_analyzed"] = stats.get("files_analyzed", 0)
            combined_stats["files_with_violations"] = stats.get("files_with_violations", 0)
            combined_stats["compliant_files"] = stats.get("compliant_files", 0)

        # Analyze Pre-commit Config
        precommit_config_path = None
        if project_root:
            precommit_config_path = project_root / ".pre-commit-config.yaml"
            if precommit_config_path.is_file():
                log.info(f"Analyzing pre-commit config: {precommit_config_path}")
                precommit_violations = analyze_precommit_config(precommit_config_path)
                combined_stats["configs_analyzed"] = 1
                if precommit_violations:
                    all_violations[precommit_config_path] = precommit_violations
                    combined_stats["configs_with_violations"] = 1
                    log.debug(f"Found violations in {precommit_config_path}")
                else:
                    log.debug(f"No violations found in {precommit_config_path}")
            else:
                log.debug(f"No .pre-commit-config.yaml found at {project_root}")
        else:
            log.warning("Project root not found, skipping pre-commit config check.")

        # Report Combined Results
        total_entities_with_violations = (
            combined_stats["files_with_violations"] + combined_stats["configs_with_violations"]
        )

        if output_json_cli:
            violations_for_json = (
                {str(k): v for k, v in all_violations.items() if k != precommit_config_path}
                if precommit_config_path
                else {str(k): v for k, v in all_violations.items()}
            )
            json_output = format_violations_as_json(
                violations_for_json,  # Pass dict with string paths
                combined_stats["files_analyzed"],
                combined_stats["files_with_violations"],
                combined_stats["compliant_files"],
            )
            # TODO: Add pre-commit violations to JSON output structure
            print(json.dumps(json_output, indent=2))
        else:
            total_violations_count = sum(len(issues) for v in all_violations.values() for issues in v.values())
            log.info(
                f"Audit Complete. "
                f"Files Analyzed: {combined_stats['files_analyzed']}, "
                f"Configs Analyzed: {combined_stats['configs_analyzed']}, "
                f"Total Violations Found: {total_violations_count}, "
                f"Files w/ Violations: {combined_stats['files_with_violations']}, "
                f"Configs w/ Violations: {combined_stats['configs_with_violations']}."
            )
            if total_entities_with_violations > 0:
                log_violations_as_text(all_violations)
            else:
                log.info("✨ All analyzed files and configs comply with configured checks! ✨")

        if total_entities_with_violations > 0:
            exit_code = 1

    except Exception as e:
        log.exception("An unexpected error occurred during the audit process.")
        exit_code = 2

    return exit_code
