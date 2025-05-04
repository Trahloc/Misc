# Project TODO List

**== INTERRUPTED (YYYY-MM-DDTHH:MM:SS+ZZ:ZZ - AI: Run `date --iso-8601=seconds`) ==**
**Reason:** User is renaming the project root directory according to the new ZLF convention (`project_pkg/src/project/`).
**Last Action:** Successfully fixed `ImportError` for `find_project_root` in `src/zeroth_law/cli.py`.
**Next Action:** Re-run `pytest tests/test_cli.py` to verify the fix and CLI dispatch mechanism after the project rename.
**====**

## **Phase B: Extending Static Analysis & Refinement**

- [x] 1. **Line Count Check:** (`analyzer/python/line_counts.py`) Implement `analyze_line_counts` (TDD). Integrate into `analyze_file_compliance`.
- [x] 2. **Complexity Check:** (`analyzer/python/complexity.py`, `ast_utils.py`) Implement `analyze_complexity` using `ast` (TDD). Integrate.
- [x] 3. **Docstring Check:** (`analyzer/python/docstrings.py`, `ast_utils.py`) Implement `analyze_docstrings` (module, function, class - TDD). Integrate.
- [x] 4. **Parameter Count Check:** (`analyzer/python/parameters.py`, `ast_utils.py`) Implement `analyze_parameters` (TDD). Integrate.
- [x] 5. **Statement Count Check:** (`analyzer/python/statements.py`, `ast_utils.py`) Implement `analyze_statements` (TDD). Integrate.
- [ ] 6. **Refactor Long/Complex Code:** Address violations flagged for line count, complexity, parameters (e.g., in `cli.py`, `config_loader.py`, `analyzer.py`).
    - [x] 6.1. Refactor `run_audit` function in `cli.py` to reduce complexity.
    - [x] 6.2. Refactor `config_loader.py` functions.
      - Created a more modular design with better separation of concerns
      - Implemented proper error handling for TOML parsing and validation
      - Added comprehensive test coverage (83% for refactored module)
      - Followed TDD principles with tests created before implementation
      - Need to finalize by renaming from `config_loader_refactor.py` to `config_loader.py`
    - [ ] 6.3. Refactor `analyzer.py` functions. *(Note: Consider how this logic will be reused/integrated by the future ZLT orchestration engine)*.
- [ ] 7. **Fix Remaining Header/Footer Issues:** Debug why edits failed or manually fix remaining header/footer violations in files like `src/__init__.py`, test `__init__.py` files, etc.
    - [ ] 7.1. Resume debugging `check_header_compliance` logic.
- [ ] 8. **Configuration Enhancements:**
    - [x] Support `ignore_codes` in `analyze_file_compliance` filtering.
    - [x] Add validation for config values (e.g., using Pydantic).
    - [ ] Consider XDG Base Directory support for global config (`config_loader.py`).
    - [ ] Finalize `pyproject.toml` schema (`[tool.zerothlaw.fuzzing]`) for configuring fuzz targets for ZLT execution.
- [x] 9. **Reporting Enhancements:**
    - [x] Improve detail/formatting of violation reports in `cli.py`.
    - [x] Implement JSON output using proper TDD/DDT.
- [ ] 10. **CI Workflow:** Set up GitHub Actions workflow (`.github/workflows/ci.yml`) using `poetry`.

## **Phase C: Framework Tooling & Polish**

- [x] 1. **Framework Doc Update:** Update `frameworks/python/ZerothLawAIFramework.py313.md` to reflect `poetry` standardization & ZLF/ZLT vision.
- [x] 2. **Custom Git Hook Management (TDD):**
    - [x] 2.1. Define `install-git-hook` and `restore-git-hooks` commands in `cli.py`.
    - [x] 2.2. Implement core logic for finding Git root and project roots.
    - [x] 2.3. Implement logic to generate the custom multi-project pre-commit hook script content.
    - [x] 2.4. Implement file writing and permission setting for installing the hook.
    - [x] 2.5. Implement logic for `restore-git-hooks` (running `pre-commit install`).
    - [x] 2.6. Write tests covering script generation, installation, restoration, and edge cases.
- [ ] 3. **Final README Review:** Ensure README is complete and accurate, including hook setup.
- [ ] 4. **Document Development Workflow Patterns:**
    - [ ] 4.1. **IDE Integration:** Document recommended IDE setup with format-on-save + pre-commit safety net pattern.
    - [ ] 4.2. **Repository Structure:** Explain Git root vs. Python project root considerations and how tools handle this distinction.
    - [ ] 4.3. **Config Location Requirements:** Document mandatory location of `.pre-commit-config.yaml` and other configuration files.
    - [ ] 4.4. Create diagrams or examples illustrating these patterns for clarity.
- [ ] 5. **License Review:** Confirm chosen license (CC0) is appropriate.
- [ ] 6. **Publishing Prep (Optional):** Prepare for potential PyPI release.

## Known Issues / Tech Debt
- [CRITICAL] **Fix `uv run pytest` Failures:** Investigate and resolve errors preventing the test suite from running via `uv run pytest`. Follow the plan outlined in NOTES.md.
- [CRITICAL] **Investigate and Fix `src/src` Directory Structure:** The project contains a `src/src/` directory structure which is incorrect. Audit the project structure, identify the cause, and refactor to the correct `src/zeroth_law/` structure, adjusting all relevant imports and configurations.
- [ ] **Investigate Podman Stop Warning:** The `zlt-baseline-runner-...` container often requires SIGKILL instead of stopping gracefully with SIGTERM during `zlt tools sync`. Investigate the cause (e.g., process handling in `container_runner.py`, resource limits, Podman cleanup) and resolve.
- [ ] Investigate and fix root cause of `mypy` "Source file found twice" error when executed via `action_runner.py`. Re-enable `mypy` in `tool_mapping.json` for the `lint` action once resolved. (Currently handled by pre-commit hook).
- [ ] Review and refactor suppressed `E402` (module import not at top of file) errors identified in `CODE_TODOS.md`. Remove `sys.path` modifications if redundant due to Poetry's editable install.
- [ ] **Investigate Disappearing Baseline Output:** The `generated_command_outputs/` directory (or its subdirs) disappears after `zlt tools sync --generate` completes, despite successful writes during the run. Investigate potential causes (Podman cleanup timing, filesystem caching, unexpected side effects in sync logic or dependencies).
    - [ ] **Troubleshooting Notes (2025-05-02):**
        - Debug logs confirm `baseline_generator.py` successfully opens files for writing (`open(..., 'wb')`).
        - Debug logs confirm `f.write()` completes without error.
        - Debug logs confirm internal verification (`output_capture_path.is_file()`) passes immediately after closing the file.
        - Added explicit `f.flush()`, `os.fsync(f.fileno())`, and `time.sleep(0.1)` before the verification check; issue persists.
        - Running sequentially (`--tool uv`) *seemed* to work once, but subsequent `list_dir` checks confirmed the output directory was still empty.
        - Podman volume mounts (`--volume=...:/app:ro`, `--volume=...:/root/.cache/python:rw`) appear correct.
        - Parallelism (`_run_parallel_baseline_processing`) vs. sequential execution might be a factor, but the sequential test also ultimately failed to produce files.
        - Root cause remains unknown; filesystem interaction or Podman behavior is highly suspect.

## **Phase D: ZLT Core Orchestration Engine**
# Goal: Develop ZLT to directly execute and interpret consultant tools as the primary ZLF enforcement mechanism.
- [ ] ZLT: Implement initial "pass-through" execution for core consultants (`ruff check`, `ruff format`, `mypy`, `pytest`). ZLT acts as an alias, running the tool and reporting raw results. *(Priority: Get data flowing through ZLT)*.
- [ ] ZLT: Design core execution loop for iterating through configured checks.
- [ ] ZLT: Design `pyproject.toml` schema (`[tool.zerothlaw.*]`) for configuring consultant tools (paths, flags, targets, timeouts, initial configs).
- [ ] ZLT: Implement execution & interpretation wrapper for `ruff check`.
- [ ] ZLT: Implement execution & interpretation wrapper for `ruff format` (check mode).
- [ ] ZLT: Implement execution & interpretation wrapper for `mypy --strict`.
- [ ] ZLT: Implement execution & interpretation wrapper for `pytest` (incl. coverage parsing).
- [ ] ZLT: Implement execution & interpretation wrapper for `pylint` (using a broad default config initially, blacklisting only conflicts/style).
- [ ] ZLT: Implement execution & interpretation wrapper for Fuzzers (e.g., `Atheris`) based on `pyproject.toml` config.
- [ ] ZLT: Implement result aggregation and de-duplication logic (normalize similar errors from different tools).
- [ ] ZLT: Develop unified reporting module for aggregated/de-duplicated results.
- [ ] ZLT: Define and implement violation severity levels (INFO, WARN, FAIL) in reporting:
    - INFO: Meta suggestions (e.g., better docstring phrasing).
    - WARN: Violates a principle, but doesn't impact functionality or clarity.
    - FAIL: Breaks TDD, type coverage, correctness, or structural integrity.
- [ ] ZLT: Refactor `cli.py::run_audit` to utilize the new orchestration engine.
- [ ] Investigate using `uv run <tool> -- <args>` for local ZLT tool execution instead of direct `.venv/bin/<tool>` calls, evaluating benefits for environment consistency vs. implementation complexity/overhead.
- [ ] **(Optional Investigation) Podman for Stricter Local Checks:** Explore the feasibility and value of optionally running certain local ZLT checks (e.g., linters, formatters in check mode) inside a Podman container (potentially read-only) to strictly prevent unintended file modifications. Assess performance trade-offs.
- [ ] **(Optional Investigation) Podman for Sandboxing:** Explore using Podman as a sandboxed execution environment for potentially less trusted or experimental tools integrated into the ZLT workflow in the future.

## **Phase E: ZLT-Dev Capability Mapping & Optimization**
# Goal: Continuously improve ZLT's understanding of consultant tools and optimize its default configuration based on evidence from real tests.
- [ ] **1. Create Rule-to-Principle Registry:**
    - [ ] Define YAML/JSON schema mapping tool rule IDs (e.g., `ruff:SIM108`) to ZLF Principles (e.g., `[#12]`).
    - [ ] Implement initial population for known high-value rules.
    - [ ] (Optional) Implement auto-PR suggestion for unmapped rules encountered during analysis.
- [ ] **2. Define Test Intent Capture Method:**
    - [ ] Define the dual mechanism for capturing test intent:
        - **Primary:** `@zlf_principle([...])` decorator (robust, AST-parsable). Define placeholder decorator.
        - **Supported:** Structured comments (`# ZLF: [...]`) for flexibility/legacy.
        - Specify decorator takes precedence if both exist.
    - [ ] Define the Module -> Class -> Function tagging granularity and inheritance model:
        - Module: `# ZLF_MODULE: [...]`
        - Class/Function: `@zlf_principle([...])`
        - Lower levels override/extend higher levels.
    - [ ] Define convention for multiple principles: Allow list, first entry denotes primary intent.
    - [ ] Define convention for parameterized tests: Tag applies to base function for all variants.
    - [ ] Implement AST parsing logic within ZLT-dev to extract this metadata during test analysis.
- [ ] **3. Implement Test Harvesting & Execution:**
    - [ ] Design mechanism to identify and collect relevant test cases (initially ZLT's own tests).
    - [ ] Implement logic within ZLT-dev to execute consultant tools broadly against harvested tests.
- [ ] **4. Implement Violation Logging & Correlation:**
    - [ ] Design structured logging format (e.g., JSON/DB schema) to store: `test_case`, `line_triggered`, `code_snippet`, `tool`, `rule`, `mapped_zlf_principles`, `test_intent_principles`.
    - [ ] Implement ZLT-dev logic to parse tool output, look up principles from the registry, extract test intent, and populate the log/DB.
- [ ] **5. Implement Capability Map Analysis:**
    - [ ] Develop queries/logic to analyze the collected data for:
        - Rule frequency per ZLF principle.
        - Rule overlap/redundancy (e.g., which rules consistently fire together for the same principle on the same code).
        - Coverage gaps (ZLF principles with low rule coverage).
        - Confidence scores for rule-principle mappings.
- [ ] **6. Design Configuration Feedback Loop:**
    - [ ] Define process/tooling for using analysis results to propose evidence-based updates to ZLT's default consultant configurations (e.g., suggesting rules to disable/enable).
- [ ] **7. (Optional) `.zgraph.yaml` Integration:**
    - [ ] Explore modeling principles and rule mappings within `.zgraph.yaml` for high-level coverage visualization.

## **Phase F: Codebase Map & Structural Verification**
# Goal: Implement an automated map of the codebase structure (in SQLite) to enhance refactoring safety and ZLT's understanding.
- [ ] **1. Define SQLite Schema:**
    - [x] Design core tables (`modules`, `classes`, `functions`) and columns.
    - [x] Define relationships (FOREIGN KEYs) and constraints (UNIQUE).
    - [x] Document schema in **`tests/codebase_map/schema.sql`**.
    - [ ] Note: Conceptual tables (`principles`, `rules`, mappings) deferred to Phase Y.
- [ ] **2. Implement Map Generator (`tests/codebase_map/map_generator.py`):
    - [x] Use `ast` (via `ast.NodeVisitor`) to traverse Python files in `src/zeroth_law/`.
    - [x] Use `sqlite-utils` module to connect to `tests/codebase_map/code_map.db`.
    - [x] Implement logic to create tables based on schema if DB doesn't exist.
    - [x] Implement `sqlite_utils.upsert` logic based on AST scan results.
    - [x] Implement logic to detect potential stale entries (`audit_database_against_scan`).
    - [x] Track processed items during scan.
    - [x] Add `argparse` for script execution.
- [ ] **5. Implement Map Verification Tests (`tests/test_codebase_map/test_map_generator.py`):
    - [ ] Test basic generation (modules, classes, functions) with temp files.
    - [ ] Test signature hash calculation and updates.
    - [ ] Test handling of methods vs. module-level functions.
    - [ ] Test stale entry detection (`audit_database_against_scan`) reporting.
    - [ ] Use `pytest` fixtures for setup/teardown (temp DB, temp src files).
- [ ] **6. Implement Pruning/Cleanup Mechanism:**
    - [x] Design the confirmation mechanism for stale entry removal (require `--prune-stale-entries "<confirmation_string>"`).
    - [x] Implement the logic to execute SQL `DELETE` statements based on the verified confirmation.
    - [x] Add tests to verify conditional pruning based on confirmation string.
- [ ] **7. Integrate into Test Workflow:**
    - [x] Ensure map generation/update runs automatically during `pytest` (via session-scoped fixture `code_map_db` in `tests/conftest.py`).
    - [ ] Ensure verification tests run as part of the standard test suite (will be covered by creating tests in Task 3/6).
- [ ] **8. Implement Reporting (Optional but Recommended):**
    - [ ] Add fixtures or scripts to query the DB upon specific test failures and generate consumable reports for the AI (e.g., list of orphaned functions, signature mismatches).
- [ ] **9. (Future) ZLT Integration:** Explore having ZLT directly query the `code_map.db`.

## **Phase G: Tool Definition Workflow & AI Interpretation**
# Goal: Refine the process for capturing and verifying tool CLI definitions using AI interpretation.
#
# --- MANDATE REMINDER --- #
# `tool_index.json` is 100% programmatically generated (by baseline tests).
# NEVER edit `tool_index.json` directly. The AI's role is ONLY to populate/update
# the separate `.json` DEFINITION files based on `.txt` baselines and sync their
# internal `metadata.ground_truth_crc` to match the index.
# * Clarification: This interpretation (`.txt` -> `.json` structure & internal CRC sync) is the *sole* permitted non-deterministic step.
# --- END MANDATE REMINDER --- #
#
# --- SUPERCEDING NOTE (2025-05-01T12:15:37+08:00) ---
# The detailed implementation steps outlined in the 10-Step Plan (Phase L)
# supersede the specific implementation tasks listed below in Phase G and Phase H (Item 10).
# While the high-level goals may remain, refer to Phase L for the current, authoritative workflow.
# --- END SUPERCEDING NOTE ---
#
- [ ] **Simplify Paths:** Update paths in tests (`test_ensure_*.py`, `test_txt_json_consistency.py`).
- [x] **Update Schema Guidelines:** Add guidance to `docs/zlt_schema_guidelines.md` emphasizing the AI's responsibility to maintain consistency for unchanged options/args when updating `.json` files.
- [x] **Separate Capabilities:** Create `src/zeroth_law/tools/tool_capabilities.yaml` to store functional categories (Formatter, Linter, etc.), separate from CLI structure.
- [ ] **AI Task: Populate `.json` Definitions:** Systematically process `.txt` files and populate the corresponding `.json` skeleton files according to the guidelines. (Partially superseded by Phase L, Step 8 - focus is now iterative and triggered by sync failures).
    - [ ] **Review `poetry.json`:** The current `poetry.txt` seems to contain help for `poetry list` rather than the main command.
        - [ ] Regenerate the baseline using `poetry --help` (or similar) to capture the correct help text. (Covered by Phase L, Step 6)
        - [ ] Repopulate `src/zeroth_law/tools/poetry/poetry.json` based on the new baseline, ensuring it includes core subcommands like `add`, `install`, `build`. (Covered by Phase L, Step 8)
- [ ] **Implement Schema Validation Test:** Create `tests/test_tool_defs/test_json_schema_validation.py` to validate `value_name` structure, `nargs` consistency, and whitespace rules in names/flags. (Consistent with Phase L, Step 7.5 validation goals).

## **Phase H: Tool Management Subcommand (`zlt tools`)**
# Goal: Centralize tool management logic into a dedicated subcommand group.
- [x] 1. Rename `src/zeroth_law/commands/` to `src/zeroth_law/subcommands/`.
- [x] 2. Remove duplicate `audit.py` file.
- [x] 3. Create `src/zeroth_law/subcommands/tools/` directory.
- [x] 4. Create `src/zeroth_law/subcommands/tools/__init__.py`.
- [x] 5. Create `src/zeroth_law/subcommands/tools/tools.py` with main `click.group`.
- [x] 6. Register `tools_group` in `src/zeroth_law/cli.py`.
- [x] 7. Implement `zlt tools reconcile` subcommand.
  - [x] Migrate core logic from `reconciliation_logic.py`.
  - [x] Migrate logic from `tool_discovery.py`. *(Logic already covered by current reconcile implementation)*.
  - [x] Migrate logic from `tools_dir_scanner.py`. *(Logic moved to lib/tooling/tools_dir_scanner.py)*.
  - [x] Implement reporting of discrepancies (new tools, orphans, missing files).
- [ ] 8. Implement `zlt tools add/remove-whitelist` subcommands.
  - [ ] Implement `pyproject.toml` parsing/writing (using `tomlkit`).
  - [ ] Implement hierarchical logic (tool vs. tool:subcommand).
  - [ ] Implement `--all` flag logic.
  - [ ] Implement INFO message for conflicting entries.
- [ ] 9. Implement `zlt tools add/remove-blacklist` subcommands (similar to whitelist).
  - [x] Implement `pyproject.toml` parsing/writing (using `tomlkit`).
  - [x] Implement hierarchical logic (tool vs. tool:subcommand).
  - [x] Implement `--all` flag logic.
  - [x] Implement INFO message for conflicting entries.
- [ ] 10. Implement `zlt tools sync` subcommand. (Superseded by Phase L for implementation details)
  - [ ] ~~Migrate baseline generation logic (`generate_baseline_cli.py`).~~ (Superseded by Phase L, Step 6 Podman logic)
  - [ ] ~~Migrate skeleton JSON creation logic.~~ (Superseded by Phase L logic)
  - [ ] ~~Migrate index update logic (`ToolIndexHandler`).~~ (Integrated into Phase L, Steps 6 & 9)
  - [x] Implement `--tool`, `--force`, `--since` options. (Note: `--tool` needs review against Phase L sequence focus. `--since` split into `--check-since`, `--update-since` in Phase L).
  - [✓] **10.6 Add --dry-run option:** Implement flag to simulate sync actions without execution. (Needs review/integration with Phase L)
  - [ ] **~~Verify Handling of Whitelisted but Missing Tools:~~** ~~Ensure `sync` correctly attempts to generate baselines for tools like `zlt` that are whitelisted but whose directories are initially missing.~~ (Covered by Phase L, Step 4 & 6 interaction)
  - [ ] **Enhance User Feedback:** Add progress indicators or more verbose logging during reconciliation and parallel baseline generation phases to improve user experience for long operations. (Still relevant for Phase L implementation)
- [x] 11. Refactor/Remove redundant dev scripts (`reconciliation_logic.py`, `generate_baseline_cli.py`, `tools_dir_scanner.py`, `tool_discovery.py`).
- [ ] 12. Refactor/Remove redundant test fixtures (`ensure_baselines_updated`, `managed_sequences` - replace with direct calls or new fixtures if needed).
- [ ] 13. Update tests to use or test the new `zlt tools` commands.
  - [x] Refactor `test_check_for_new_tools` to use `zlt tools reconcile`.
  - [x] Update `get_tool_dirs` import in `test_no_orphan_tool_directories`.
  - [ ] Verify tests pass or fail for expected reasons (e.g., `ToolIndexHandler` import).
  - [ ] Add new tests for `zlt tools reconcile`, `sync`, `add/remove-whitelist/blacklist`.
- [ ] **14. Implement Subcommand-Level Blacklist/Whitelist Management:**
  - [x] **14.1.** Implement parsing logic in `config_loader.py` to handle hierarchical syntax (`tool:sub1,sub2`) and produce structured dicts.
  - [ ] **14.2.** Refactor `tool_reconciler.py::reconcile_tools` to accept and utilize the structured dict/tree format for whitelist/blacklist and apply **specific-over-general precedence rule**.
  - [ ] **14.3.** Update `reconcile.py::_perform_reconciliation_logic` to pass the structured dicts/trees to `reconcile_tools` and interpret the results correctly.
  - [ ] **14.4.** Update `sync.py` to filter command sequences based on the resolved hierarchical status from `reconcile` (applying precedence rules).
  - [x] **14.5.** Update `list_utils.py` (`modify_tool_list`, `_format...`) and `whitelist_cmd.py`/`blacklist_cmd.py`:
    - [x] Handle parsing/writing arbitrary nesting syntax (`tool:sub:subsub`).
    - [x] Implement `--all` flag logic for descendant modification.
    - [x] Implement conflict detection: `add` fails if item exists in other list, unless `--force` is used (add `--force` option to CLI commands).
  - [ ] **14.6.** Add/update tests for:
    - [x] **14.6.1** Nested parsing (`config_loader`).
    - [x] **14.6.2** Hierarchical modification in `list_utils.py` (add/remove, with/without `--all`, with/without `--force`, conflict scenarios).
    - [ ] **14.6.3** Precedence rule checking in `reconcile`.
    - [ ] **14.6.4** Task filtering in `sync` based on precedence.
    - [✓] **14.6.4.1** Sync Sequence Filtering: Verify `sync.py` correctly filters command sequences using `_get_effective_status` based on various `pyproject.toml` whitelist/blacklist configurations (specific tools, subcommands, wildcards). (Debugged: 2025-04-30 - Fixed issues related to type hints, parsing, and logic in `tool_reconciler.py`, `hierarchical_utils.py`, `cli.py`.)
    - [ ] **14.6.5** CLI command tests (`whitelist_cmd.py`/`blacklist_cmd.py`) including `--force`.
    - [x] **14.6.6** New pytest check to fail if the *exact same item* exists in both parsed whitelist and blacklist structures.
- [ ] **15. Podman Integration Follow-up (Post-Refactor):**
  - [ ] Document `podman` as a development dependency for the `zlt tools sync` workflow.
  - [ ] Test the Podman-based baseline capture workflow thoroughly, covering various tools, subcommands, potential errors (container start failure, exec failure, timeouts), and cleanup.
  - [ ] **15.3 Verify Read-Only Check:** Explicitly test and document the use of a read-only filesystem within the Podman container during baseline generation to differentiate commands requiring writes (which should fail) from pure help/subcommand invocations.
  - [ ] Investigate and improve shell escaping robustness for command arguments passed to `podman exec sh -c \"...\"` in `baseline_generator.py`.
  - [x] (Post JSON Validation) Re-evaluate implementing a "blind execution" fallback (running command without `--help`) using the Podman sandbox for cases where help flags consistently fail for *valid* commands.
  - [x] **Refactor Podman Helper Function (`_prepare_command_for_container`):**
    - [x] 1. Create new file: `src/zeroth_law/lib/tooling/podman_utils.py`.
    - [x] 2. ~~Read the definition of `_prepare_command_for_container` from `src/zeroth_law/subcommands/tools/sync.py`.~~ *Function was missing, needed reimplementation.*
    - [x] 3. Edit `podman_utils.py` to add the function definition (with imports: `Path`, `sys`, `List`, `Sequence`).
    - [x] 4. Edit `src/zeroth_law/subcommands/tools/sync.py` to add import from `podman_utils`.
    - [x] 5. Edit `src/zeroth_law/lib/tooling/baseline_generator.py` to add import from `podman_utils`.
- [ ] **16. Refactor `zlt tools sync` into Stages:**
  - [ ] **16.1 Design:** Define logical stages (e.g., Reconciliation, Podman Setup, Sequence Generation, Baseline Capture Loop, Index Update, Podman Cleanup).
  - [ ] **16.2 Implement:** Refactor `sync.py` into separate functions/methods for each stage.
  - [ ] **16.3 Orchestrate:** Modify the main `sync` command function to call these stages in sequence.
  - [ ] **16.4 Add Stage Control (Optional):** Consider adding flags (e.g., `--skip-setup`, `--only-capture`) or internal commands to allow running specific stages for debugging.
  - [ ] **16.5 Test:** Ensure end-to-end functionality is preserved and add tests for individual stages if feasible.

## **Phase I: Capability-Driven Refactor & Central Definitions**
# Goal: Refactor core logic for better testability, define central schemas, and improve CLI experience.

[ ] **1. Integrate TODO Management into ZLT (`src/zeroth_law/subcommands/todo/`):**
    - [x] Create `todo_group.py` and register with `cli.py`.
    - [x] Move `archive_todo_phase.py` logic into `zlt todo complete` command.
    - [ ] **1.3. Implement `zlt todo codetodos`:**
        - [ ] Create `codetodos.py` subcommand.
        - [ ] Adapt logic from `scripts/generate_code_todos.py` (or similar).
        - [ ] Define output format for `CODE_TODOS.md`.
        - [ ] Add tests for `codetodos` generation.
    - [ ] **1.4. Refine `zlt todo complete` Workflow:**
        - [ ] Determine verification mechanism (e.g., require `--reviewed` flag? Rely on manual AI trigger?).
        - [ ] Update command logic and documentation.
        - [ ] **1.4.1 Add `--report` option:** Implement a `--report <string>` option used with `--confirmed` to capture the AI's **Executive Summary**.
        - [ ] **1.4.2 Prepend summary to archive:** Modify `complete` logic to prepend the `--report` Executive Summary to the archived phase content.
        - [ ] **1.4.3 Add tests for `--report`:** Verify report content appears in the archived file.
    - [ ] **1.5. Refine Phase Completion Test (`test_detect_completed_phases.py`):**
        - [ ] Adjust test logic/assertion to act as a *warning* or *prompt* for review, not a hard failure.
        - [ ] Update test message to reflect its advisory role.

## **Phase J: Tool Execution Definition & Mapping**
# Goal: Define and populate the structured knowledge ZLT uses to select and execute the correct underlying tools based on requested capabilities, file types, and options.

[ ] **1. Define Tool Definition Schema (`src/zeroth_law/schemas/tool_definition.schema.json`?):**
    - [ ] Specify JSON schema for tool/subcommand `.json` definition files.
    - [ ] Include fields for core CLI structure (commands, options, args, types) derived from `.txt` baselines.
    - [ ] Add required semantic fields:
        - `capability`: ZLT capability provided (string or list, linking to `tool_capabilities.yaml`?).
        - `filetype_affinity`: List of applicable file extensions.
        - `option_map`: Mapping from canonical ZLT option names (`zlt_options_definitions.json`) to this tool's specific options/flags/argument patterns.
            - Consider how to represent complex mappings (e.g., ZLT `--level=high` maps to tool `--severity critical --filter XYZ`).

[ ] **2. AI Task: Populate Initial Definitions (`src/zeroth_law/tools/.../*.json`):**
    - [ ] Systematically interpret the `.txt` baseline help output for core tools (`ruff`, `mypy`, `pytest`, `black`, etc.).
    - [ ] Create/update the corresponding `.json` definition files according to the defined schema.
    - [ ] Ensure accurate mapping of CLI structure.
    - [ ] Add the semantic mappings (`capability`, `filetype_affinity`, `option_map`) based on tool documentation and ZLT goals.
    - [ ] Update `metadata.ground_truth_crc` in the `.json` to match the corresponding `.txt` baseline CRC in `tool_index.json` after interpretation.

[ ] **3. Implement Tool Definition Loading & Validation:**
    - [ ] Create loader function to read and validate `.json` definition files against the schema.
    - [ ] Implement tests (`test_tool_definition_validation.py`?) to:
        - Validate schema compliance.
        - Verify consistency (e.g., referenced ZLT options in `option_map` exist in `zlt_options_definitions.json`).
        - Check for structural integrity.

[ ] **4. Define Central ZLT Capabilities (`src/zeroth_law/zlt_capabilities.yaml`):**
    - [ ] Create a YAML file listing canonical ZLT capabilities (e.g., `Linter`, `Formatter`, `TypeChecker`, `Tester`, `SecurityAuditor`) with descriptions.
    - [ ] Ensure capability names used in tool definitions refer to entries in this file.

[ ] **5. Define Central ZLT Options (`src/zeroth_law/zlt_options_definitions.json`):**
    - [ ] Create JSON file defining canonical ZLT global/command options (e.g., `--config`, `--fix`, `--verbose`, `--level`, `paths`).
    - [ ] Include type, CLI flags, help text, canonical name for mapping.
    - [ ] Ensure ZLT CLI generation (Phase I.3) uses this file.
    - [ ] Ensure tool definition validation (J.3) uses this file to check `option_map` references.

## **Phase L: Implement Tool Sync Workflow (10-Step Plan)**
# Goal: Implement the robust, deterministic `zlt tools sync` workflow based on the 10-step plan defined on 2025-05-01.
# NOTE: Add completion timestamp `(YYYY-MM-DDTHH:MM:SS+ZZ:ZZ - Run 'date --iso-8601=seconds')` to each item upon completion.

### **Phase 1: Setup & Reconciliation (Steps 1-5)**

- [x] **Step 1: Environment Setup** (`2025-05-01T12:15:37+08:00`)
  - [x] 1.1 Action: Ensure correct venv activation (implicit via `uv run`). (`2025-05-01T13:47:53+08:00`)
  - [x] 1.2 Action: Determine absolute path to active venv `bin` directory (e.g., `sys.prefix`/`bin`) -> `venv_bin_path`. (`2025-05-01T13:47:53+08:00`)
  - [x] 1.3 Verification: Log the detected `venv_bin_path`. (`2025-05-01T13:47:53+08:00`)

- [x] **Step 2: Discover Executables** (`2025-05-01T12:15:37+08:00`)
  - [x] 2.1 Action: Scan `venv_bin_path` directory. (`2025-05-01T13:47:53+08:00`)
  - [x] 2.2 Action: Create raw list `raw_executables` of all executable file names. (`2025-05-01T13:47:53+08:00`)
  - [x] 2.3 Verification: Log the count of `raw_executables`. (`2025-05-01T13:47:53+08:00`)

- [x] **Step 3: Filter & Validate Whitelist/Blacklist** (`2025-05-01T12:15:37+08:00`)
  - [x] 3.1 Action: Load hierarchical whitelist/blacklist from `pyproject.toml` -> `whitelist_tree`, `blacklist_tree` (using `src/zeroth_law/lib/config_loader.py`). (`2025-05-01T13:47:53+08:00`)
  - [x] 3.2 Action: Implement/Verify `check_list_conflicts(whitelist_tree, blacklist_tree)` (in `src/zeroth_law/lib/hierarchical_utils.py`?). (`2025-05-01T13:47:53+08:00`)
  - [x] 3.3 Action: Call `check_list_conflicts`, fail immediately if conflicts found. (`2025-05-01T13:47:53+08:00`)
  - [x] 3.4 Action: Implement/Verify `get_effective_status(sequence, whitelist_tree, blacklist_tree)` in `src/zeroth_law/lib/hierarchical_utils.py` (handles precedence, wildcards). (`2025-05-01T13:47:53+08:00`)
  - [x] 3.5 Action: Initialize `managed_executables = []`, `unclassified_executables = []`. (`2025-05-01T13:47:53+08:00`)
  - [x] 3.6 Action: Iterate `raw_executables`, use `get_effective_status` to populate `managed_executables` and `unclassified_executables`. (`2025-05-01T13:47:53+08:00`)
  - [x] 3.7 Action: If `unclassified_executables` not empty, fail immediately with clear instructions to use `zlt tools add-whitelist/add-blacklist`. (`2025-05-01T13:47:53+08:00`)
  - [x] 3.8 Verification: Log count of `managed_executables`. (`2025-05-01T13:47:53+08:00`)

- [x] **Step 4: Reconcile `tools/` Directory Structure** (`2025-05-01T12:15:37+08:00`)
  - [x] 4.1 Action: Define `tools_base_dir = Path("src/zeroth_law/tools/")`. (`2025-05-01T13:47:53+08:00`)
  - [x] 4.2 Action: Get list `existing_tool_dirs` of immediate subdirectories. (`2025-05-01T13:47:53+08:00`)
  - [x] 4.3 Action: Initialize `orphan_dirs = []`. (`2025-05-01T13:47:53+08:00`)
  - [x] 4.4 Action: Iterate `existing_tool_dirs`, use `get_effective_status` to populate `orphan_dirs` if status is BLACKLISTED or UNSPECIFIED. (`2025-05-01T13:47:53+08:00`)
  - [x] 4.5 Action: If `orphan_dirs` not empty, fail immediately with instructions to whitelist tool or remove directory. (`2025-05-01T13:47:53+08:00`)
  - [x] 4.6 Action: Iterate `managed_executables`, ensure `tools_base_dir / tool_name` exists, create if missing (`os.makedirs`). (`2025-05-01T13:47:53+08:00`)
  - [x] 4.7 Verification: `tools/` structure aligns with `managed_executables`. (`2025-05-01T13:47:53+08:00`)

- [x] **Step 5: Identify Effectively Whitelisted Command Sequences** (`2025-05-01T12:15:37+08:00`)
  - [x] 5.1 Action: Initialize `whitelisted_sequences = []`. (`2025-05-01T13:47:53+08:00`)
  - [x] 5.2 Action: Add base sequences from `managed_executables` to `whitelisted_sequences`. (`2025-05-01T13:47:53+08:00`)
  - [x] 5.3 Action: Implement/Verify recursive `scan_tool_dirs(current_dir, current_sequence, ...)` in `src/zeroth_law/lib/tooling/tools_dir_scanner.py` (uses `get_effective_status`, handles recursion). (`2025-05-01T13:47:53+08:00`)
  - [x] 5.4 Action: Call `scan_tool_dirs` for each managed tool's base directory. (`2025-05-01T13:47:53+08:00`)
  - [x] 5.5 Action: Combine base and scanned sequences into final `whitelisted_sequences`. (`2025-05-01T13:47:53+08:00`)
  - [x] 5.6 Verification: Log total count of `whitelisted_sequences`. (`2025-05-01T13:47:53+08:00`)

### **Phase 2: Baseline Generation & Indexing (Step 6)**

- [ ] **Step 6: `.txt` Baseline Generation & Verification** (`2025-05-01T12:15:37+08:00`)
  - [x] 6.1 Action: Initialize `recent_update_warning_count = 0`. (`2025-05-01T13:47:53+08:00`)
  - [x] 6.2 Action: Implement/Verify `ToolIndexHandler` class (in `src/zeroth_law/lib/tooling/tool_index_handler.py`?) with load/save/update/add methods for `tool_index.json`. Load index. (Using functions from `tool_index_utils.py`) (`2025-05-01T13:47:53+08:00`)
  - [x] 6.3 Action: Define deterministic Podman container name. (`2025-05-01T13:47:53+08:00`)
  - [x] 6.4 Action: Implement Podman container setup/teardown context management within `sync` command (stop/rm existing, start new, stop/rm finally, read-only mounts). (`2025-05-01T13:47:53+08:00`)
  - [ ] 6.5 Action: Loop through each `sequence` in `whitelisted_sequences`: (`2025-05-01T13:47:53+08:00`)
    - [x] 6.5.1 Lookup: Get entry from loaded index via `ToolIndexHandler`. Continue if not found. (`2025-05-01T13:47:53+08:00`)
    - [x] 6.5.2 Timestamp Check: Use `--check-since` (default 24h) and `--force`. Continue if check passes. (`2025-05-01T13:47:53+08:00`)
    - [ ] 6.5.3 Podman Execution:
      - [x] 6.5.3.1 Construct help command args (e.g., `['ruff', 'check', '--help']`). (`2025-05-01T13:47:53+08:00`)
      - [x] 6.5.3.2 Implement/Verify `_execute_capture_in_podman(sequence_args, container_name, ...)` in `src/zeroth_law/lib/tooling/baseline_generator.py` (builds `podman exec sh -c "export PATH...; timeout ... | cat"`, runs `subprocess`, handles errors, returns stdout). (`2025-05-01T13:47:53+08:00`)
      - [x] 6.5.3.3 Call `_execute_capture_in_podman`, handle exceptions. (`2025-05-01T13:47:53+08:00`)
      - [ ] **6.5.3.4 (INCOMPLETE)** Modify `_execute_capture_in_podman` (or calling logic) to determine the *actual* command arguments (e.g., `--help`, `--version`, specific subcommand help) based on the interpreted `.json` definition (from Step 8/9), not just hardcoding `--help`.
    - [x] 6.5.4 CRC Calculation: Calculate `new_crc = zlib.crc32(output)` -> hex string. (`2025-05-01T13:47:53+08:00`)
    - [x] 6.5.5 Comparison & Update:
      - [x] 6.5.5.1 If `new_crc == index_crc`: Call `ToolIndexHandler.update_checked_timestamp(sequence, now)`. (`2025-05-01T13:47:53+08:00`)
      - [x] 6.5.5.2 If `new_crc != index_crc`: Use `--update-since` (default 48h), warn/increment `recent_update_warning_count` if needed. Write output to `.txt` file. Call `ToolIndexHandler.update_entry(sequence, crc=new_crc, updated_timestamp=now, ...)` (`2025-05-01T13:47:53+08:00`)
  - [x] 6.6 Action: After loop, call `ToolIndexHandler.save_index()`. (`2025-05-01T13:47:53+08:00`)
  - [x] 6.7 Action: If `recent_update_warning_count >= 3`, fail immediately reporting rapid update issue. (`2025-05-01T13:47:53+08:00`)

### **Phase 3: AI Interpretation & Validation (Steps 7-8)**

- [x] **Step 7: Identify First Missing/Outdated `.json`** (`2025-05-01T12:15:37+08:00`)
  - [x] 7.1 Action: Reload index via `ToolIndexHandler`. (`2025-05-01T13:47:53+08:00`)
  - [x] 7.2 Action: Loop through `tool_index.json` entries (`sequence_key`, `entry_data`). (`2025-05-01T13:47:53+08:00`)
  - [x] 7.3 Action: For each entry: (`2025-05-01T13:47:53+08:00`)
    - [x] 7.3.1 Check `get_effective_status`. Continue if not WHITELISTED. (`2025-05-01T13:47:53+08:00`)
    - [x] 7.3.2 Determine `txt_path`, `json_path`. (`2025-05-01T13:47:53+08:00`)
    - [x] 7.3.3 Check if `txt_path` exists. Continue if not. (`2025-05-01T13:47:53+08:00`)
    - [x] 7.3.4 Check if `json_path` exists. If not, `needs_interpretation = True`. (`2025-05-01T13:47:53+08:00`)
    - [x] 7.3.5 If `json_path` exists, load JSON, get `json_crc`, compare with `index_crc`. If mismatch or placeholder, `needs_interpretation = True`. (`2025-05-01T13:47:53+08:00`)
    - [x] 7.3.6 If `needs_interpretation`, fail immediately, report sequence/path, instruct AI to start Step 8. (`2025-05-01T13:47:53+08:00`)
  - [x] 7.4 Outcome: If loop completes, proceed to Step 9. (`2025-05-01T13:47:53+08:00`)

- [ ] **Step 8: AI Interpretation & Validation (Triggered by Step 7 Failure)** (`2025-05-01T12:15:37+08:00`)
  - [ ] 8.1 AI Task: Interpret `.txt` to `.json`
    - [ ] 8.1.1 AI: Receive sequence key, JSON path from Step 7 failure.
    - [ ] 8.1.2 AI: Read `.txt`, existing `.json`, `zlt_schema_guidelines.md`.
    - [ ] 8.1.3 AI: Propose `edit_file` for `.json` path, adhering to guidelines (NO backslashes, DO NOT set `ground_truth_crc`).
  - [ ] 8.2 Verify & Correct Schema (Automated Post-AI Edit)
    - [ ] 8.2.1 Implement trigger mechanism (AI calls script? Wrapper script?).
    - [ ] 8.2.2 Run `fix_json_whitespace.py` on edited file. Check exit.
    - [ ] 8.2.3 Run `fix_json_schema.py` on edited file (ensure backslash check is added). Check exit.
    - [ ] 8.2.4 Run `schema_corrector.py` on edited file. Check exit.
    - [ ] 8.2.5 If any script fails, report error, instruct AI to retry 8.1.
  - [ ] 8.3 Update `.json` CRC via Script (Automated Post-Validation)
    - [ ] 8.3.1 Ensure `scripts/update_json_crc_tool.py` exists and functions correctly (reads index, updates `.json` metadata field).
    - [ ] 8.3.2 Execute `uv run python scripts/update_json_crc_tool.py --file <validated_json_path>`.
    - [ ] 8.3.3 If script fails, report error and halt.
    - [ ] 8.3.4 If script succeeds, instruct user/AI to re-run `zlt tools sync`.

### **Phase 4: Subcommand Discovery & Iteration (Steps 9-10)**

- [x] **Step 9: Discover & Index Subcommands** (`2025-05-01T12:15:37+08:00`)
  - [x] 9.1 Action: Reload index. Initialize `new_sequences_added = False`. (`2025-05-01T13:47:53+08:00`)
  - [x] 9.2 Action: Loop through `tool_index.json` entries (`parent_sequence_key`, `parent_entry_data`). (`2025-05-01T13:47:53+08:00`)
    - [x] 9.2.1 Consistency Check: Verify parent `.json` exists and its CRC matches index. Continue if not. (`2025-05-01T13:47:53+08:00`)
    - [x] 9.2.2 Parse JSON: Load parent JSON. (`2025-05-01T13:47:53+08:00`)
    - [x] 9.2.3 Find Subcommands: Extract subcommand names (e.g., from `subcommands_detail`). (`2025-05-01T13:47:53+08:00`)
    - [x] 9.2.4 Process Subcommands: For each `subcommand_name`: (`2025-05-01T13:47:53+08:00`)
      - [x] 9.2.4.1 Construct `new_sequence_list`, `new_sequence_key`. (`2025-05-01T13:47:53+08:00`)
      - [x] 9.2.4.2 Recursion Check: Fail if `subcommand_name == parent_sequence[-1]`. (`2025-05-01T13:47:53+08:00`)
      - [x] 9.2.4.3 Check `get_effective_status`. (`2025-05-01T13:47:53+08:00`)
      - [x] 9.2.4.4 If WHITELISTED and `new_sequence_key` not in index: Calculate paths, create subdir, call `ToolIndexHandler.add_entry(new_sequence_key, crc=None, ...)`, set `new_sequences_added = True`. (`2025-05-01T13:47:53+08:00`)
  - [x] 9.3 Action: If `new_sequences_added`, call `ToolIndexHandler.save_index()`. (`2025-05-01T13:47:53+08:00`)

- [ ] **Step 10: Iteration & Completion** (`2025-05-01T12:15:37+08:00`)
  - [x] 10.1 Check: If `new_sequences_added` was `True`, report need to re-run `sync` and exit. (`2025-05-01T13:47:53+08:00`)
  - [x] 10.2 Check: If Step 7 completed AND `new_sequences_added` was `False`, report successful completion and exit 0. (`2025-05-01T13:47:53+08:00`)
  - [x] Test Step 10 Completion: Run `sync` where Steps 7 & 9 find nothing to do. Assert exit code 0 and success message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 10 Iteration: Run `sync` after Step 9 added a sequence. Assert exit code 0 and re-run message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test `--dry-run`: Run various scenarios with `--dry-run`, assert no file changes occur and appropriate log messages appear. (`2025-05-01T17:23:43+08:00`)
  - [x] Test `--prune` (requires careful mocking of `shutil.rmtree`). (`2025-05-01T17:23:43+08:00`)
  - [ ] **6.11 Test Data-Driven Command Generation:** Once L.6.5.3.4 is implemented, add/modify tests to verify that `sync --generate` executes the *correct* commands (e.g., `--help`, `--version`) based on mock `.json` file content, not just a hardcoded command.
  - [ ] **6.12 Test Disappearing Directory Fix:** Once the root cause of the disappearing `generated_command_outputs` is identified and fixed, add a test to specifically prevent regressions (e.g., ensure the target output file exists after a successful `sync --generate` run with file modification).

## **Phase M: Test Coverage for Tool Sync Workflow (Phase L)**
# Goal: Implement comprehensive unit and integration tests for the Phase L functionality.
# NOTE: Add completion timestamp `(YYYY-MM-DDTHH:MM:SS+ZZ:ZZ - Run 'date --iso-8601=seconds')` to each item upon completion.

- [x] **1. Unit Tests: `hierarchical_utils.py`** (`2025-05-01T17:10:35+08:00`)
  - [x] Test `parse_to_nested_dict`: Basic parsing, nested parsing, comma handling (last part only), wildcard (`:*`) handling, invalid inputs (empty strings, `::`, etc.). (`2025-05-01T17:10:35+08:00`)
  - [x] Test `check_list_conflicts`: No conflicts, conflicts at root, conflicts nested, no common keys. (`2025-05-01T17:10:35+08:00`)
  - [x] Test `get_effective_status`: (`2025-05-01T17:10:35+08:00`)
    - [x] No match (UNSPECIFIED). (`2025-05-01T17:10:35+08:00`)
    - [x] Whitelist only (explicit, wildcard). (`2025-05-01T17:10:35+08:00`)
    - [x] Blacklist only (explicit, wildcard). (`2025-05-01T17:10:35+08:00`)
    - [x] Both match: Deeper path wins (W>B, B>W). (`2025-05-01T17:10:35+08:00`)
    - [x] Both match (same level): Explicit beats wildcard (W>B, B>W). (`2025-05-01T17:10:35+08:00`)
    - [x] Both match (same level, same type): Blacklist wins tie (explicit W vs explicit B, wildcard W vs wildcard B). (`2025-05-01T17:10:35+08:00`)

- [ ] **2. Unit Tests: `tools_dir_scanner.py`**
  - [ ] Test `scan_whitelisted_sequences`: (`2025-05-01T17:10:35+08:00`)
    - [x] Mock `get_effective_status`. Test scanning various directory structures. (`2025-05-01T17:10:35+08:00`)
    - [x] Scenario: Only base tools whitelisted. (`2025-05-01T17:10:35+08:00`)
    - [x] Scenario: Base tool and some subcommands whitelisted. (`2025-05-01T17:10:35+08:00`)
    - [x] Scenario: Only specific subcommands whitelisted (base implicitly needed). (`2025-05-01T17:10:35+08:00`)
    - [x] Scenario: Blacklisted tool/subcommand encountered during scan (should not be returned or descended into). (`2025-05-01T17:10:35+08:00`)
    - [x] Scenario: Empty tools directory. (`2025-05-01T17:10:35+08:00`)
    - [ ] Scenario: Directory scan error handling (mock `os.iterdir` exception?).

- [ ] **3. Unit Tests: `tool_index_utils.py`**
  - [x] Test `load_tool_index`: File not found, invalid JSON, empty file, valid file (nested structure). (`2025-05-01T17:10:35+08:00`)
  - [x] Test `save_tool_index`: Successful save, check sorting, check trailing newline. (`2025-05-01T17:10:35+08:00`)
  - [x] Test `get_index_entry`: Base command found/not found, subcommand found/not found (nested), invalid base entry type. (`2025-05-01T17:10:35+08:00`)
  - [x] Test `update_index_entry`: Update existing base, update existing sub, create new base, create new sub (incl. creating intermediate dicts), update with different data types. (`2025-05-01T17:10:35+08:00`)
  - [ ] Test `load_update_and_save_entry` (requires mocking `FileLock` and other utils). *(Note: Function may be obsolete; direct load/update/save utils are tested).*
  - [x] Test `update_json_crc_tool.py` script: (`2025-05-01T13:52:13+08:00`)
    - [x] Handles file not found (target JSON). (`2025-05-01T13:52:13+08:00`)
    - [x] Handles file not found (index). (`2025-05-01T13:52:13+08:00`)
    - [x] Handles missing entry in index. (`2025-05-01T13:52:13+08:00`)
    - [x] Handles missing CRC in index entry. (`2025-05-01T13:52:13+08:00`)
    - [x] Handles JSON load errors (target/index). (`2025-05-01T13:52:13+08:00`)
    - [x] Handles file write errors. (`2025-05-01T13:52:13+08:00`)
    - [x] Test argument parsing (--file required). (`2025-05-01T13:52:13+08:00`)
    - [x] No update needed (CRC matches). (`2025-05-01T13:52:13+08:00`)
    - [x] Edge case path parsing. (`2025-05-01T13:52:13+08:00`)

- [x] **4. Unit Tests: `tool_path_utils.py`** (`2025-05-01T17:10:35+08:00`)
  - [x] Test `command_sequence_to_filepath`: Base, sub, subsub, non-existent. (`2025-05-01T17:10:35+08:00`)
  - [x] Test `command_sequence_to_id`. (`2025-05-01T17:10:35+08:00`)
  - [x] Test `calculate_crc32_hex` with known inputs. (`2025-05-01T17:10:35+08:00`)

- [x] **5. Unit Tests: `podman_utils.py` & `baseline_generator.py` (Mocking `subprocess`)** (`2025-05-01T17:10:35+08:00`)
  - [x] Test `podman_utils._run_podman_command`: Mock `subprocess.run`, test success, non-zero exit, exception scenarios, capture stdout/stderr. (`2025-05-01T17:10:35+08:00`)
  - [x] Test `baseline_generator._capture_command_output`: Verify correct construction of `podman exec` command (incl. `sh -c`, PATH, `| cat`). Test handling of Python script override vs standard tool. Mock `_execute_capture_in_podman` return values (success, failure, empty output). (`2025-05-01T17:10:35+08:00`)
  - [x] Test `baseline_generator._execute_capture_in_podman`: Mock `_run_podman_command` return values (CompletedProcess with different stdout/stderr/returncode, including 127). Verify correct return tuple (stdout bytes, stderr bytes, exit code) or exception handling. (`2025-05-01T17:10:35+08:00`)

- [x] **6. Integration Tests: `sync.py` (`zlt tools sync` using `CliRunner`)** (`2025-05-01T17:23:43+08:00`)
  - [x] Setup: Use fixtures to create temporary `pyproject.toml`, mock `venv/bin` contents, mock `tools/` structure, mock Podman interactions (e.g., mock `_start/stop_podman_runner`, `_capture_command_output`).
  - [x] Test Step 3 Failures: Run `sync` with mock venv containing unclassified tool. Assert exit code > 0 and expected error message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 4 Failures: Run `sync` with mock `tools/` containing orphan dir. Assert exit code > 0 and expected error message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 6 Success (No Change): Run `sync --generate` with consistent index/txt/json. Assert exit code 0, no file changes, index check timestamps updated. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 6 Success (Baseline Update): Run `sync --generate` with inconsistent index/txt (CRC mismatch). Assert exit code 0, `.txt` file updated, index entry updated (CRC, timestamps). (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 6 Timestamp Logic: Test `--force`, `--check-since-hours` skipping/processing scenarios. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 6 Warning/Failure: Simulate >3 rapid updates (mock `time.time`?), assert exit code > 0 and warning message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 7 Failure (Missing JSON): Run `sync` with `.txt` present but `.json` missing. Assert exit code > 0 and specific failure message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 7 Failure (Outdated JSON): Run `sync` with `.json` CRC mismatch. Assert exit code > 0 and specific failure message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 9 Discovery: Run `sync` with consistent parent JSON containing a new, whitelisted subcommand. Assert exit code 0, new entry added to index (with `crc=None`), correct reporting message. (`2025-05-01T17:23:43+08:00`)
  - [x] Test Step 10 Completion: Run `sync` where Steps 7 & 9 find nothing to do. Assert exit code 0 and success message. (`2025-05-01T17:23:43+08:00`)

## **Phase N: Automated TODO Management & Dependency Tracking**
# Goal: Replace manual editing of `TODO.md` with a `zlt todo` command suite that parses the file according to a chosen standard, generates/manages immutable Unique IDs (UIDs) alongside potentially changing Structured IDs (SIDs), allows structured modifications, understands task dependencies, provides AI-centric TDD workflow statuses, enforces parent/child dependencies, suggests the next actionable task, and provides explicit next-step instructions. (**Note:** `pytest` linking via UIDs is deferred).

- [ ] **N.1: Define & Implement `zlt todo` Multi-File Storage & Logic:** Implement the automated TODO management suite using a multi-file storage approach to mitigate AI editing issues experienced with the monolithic `TODO.md`.
    - [ ] **N.1.1: Core Logic Design:** Ensure core task processing engine (status, dependencies, `next`) operates on an abstract in-memory task tree (keyed by immutable UUIDs), making it largely agnostic to the storage I/O model.
    - [ ] **N.1.2: Multi-File Model Implementation:**
        - [ ] **N.1.2.1 Structure:** Use `docs/todos/` directory. Main `TODO.md` lists Phase titles with associated Phase UUIDs. Detailed tasks reside in `docs/todos/Phase_Title-{PhaseUUID}.md` files. Completed phases/files are moved to `docs/todos/completed/`.
        - [ ] **N.1.2.2 UUID System:** Tasks have standard immutable, globally unique **UUID** strings (e.g., generated by `uuid.uuid4()`) assigned at creation. This UUID string conceptually represents the task throughout its lifecycle.
        - [ ] **N.1.2.3 SID System:** SIDs (`M.1.2`) are phase/file-local, representing positional order within their specific `.md` file.
        - [ ] **N.1.2.4 Placeholders for Moved Tasks:** Use a distinct status marker (e.g., `[M]`) for tasks that have been moved... [rest of N.1.2.4 as before] ...
        - [ ] **N.1.2.5 Filtering Placeholders:** Tooling logic needing active tasks (e.g., `next`, `list --actionable`) filters out `[M]` placeholder lines during processing.
        - [ ] **N.1.2.6 Dependency Check:** Always based on the active task's **UUID**... [rest of N.1.2.6 as before] ...
        - [ ] **N.1.2.7 Move Operation:** Use Copy-On-Write (COW)... [rest of N.1.2.7 as before] ...
        - [ ] **N.1.2.8 Concatenation for Global Views:** Commands needing a combined view (e.g., `next`, `list --actionable`)... [rest of N.1.2.8 as before] ...
        - [ ] **N.1.2.9 Save/Write Logic:** Tool identifies modified nodes in the in-memory tree... [rest of N.1.2.9 as before] ...
    - [ ] **N.1.3: Define Status Markers & State Machine:** Formalize the AI-centric TDD task status markers (`[ ]` Pending, `[T]` Tests Defined, `[I]` Implementation, `[V]` Verify Impl, `[R]` Refactoring, `[X]` Verify Refactor, `[M]` Moved Placeholder, `[B]` Blocked, `[C]` Complete), their meanings, valid transitions (driven by `zlt todo` commands), and the 'Next Action' associated with each state/transition. Ensure this is documented clearly in `docs/todo_format_guidelines.md`. (Captures essence of old `1.bis`).
        - [ ] **N.1.3.1: Implement Indentation Linting:** Add checks to `zlt todo audit` to verify consistent Markdown list indentation, ensuring child tasks are indented relative to parents and siblings share the same indentation level, according to the chosen Markdown standard.
    - [ ] **N.1.4: UUID Uniqueness Audit:** Implement validation as part of `zlt todo audit` (or a dedicated sub-task like `_audit/_validate-uuids.py`) to verify that **each UUID string appears exactly once** across all active task lines (i.e., non-`[M]` lines) in all `docs/todos/*.md` files. This check detects errors like failed COW moves resulting in duplicate active UUIDs.
- [ ] **2. Implement `TODO.md` Parser:**
    - [ ] 2.1. Choose parsing strategy (robust Markdown library + regex/post-processing for UIDs/comments).
    - [ ] 2.2. Implement parser -> internal tree (extracts SID, UID, status, dependencies, text; stores UID as primary key).
    - [ ] 2.3. Implement optimized reading (use Active Phase markers).
    - [ ] 2.4. Handle parsing errors gracefully.
- [ ] **3. Implement Internal Task Tree Representation:**
    - [ ] 3.1. Define classes/structures for Phases and Tasks (store immutable UID, parsed SID, status, dependencies list using UIDs, text, etc.).
    - [ ] 3.2. Include methods for traversal, search (by UID, SID, status), and modification (operating on UID).
    - [ ] 3.3 Add method `get_task_status(task_uid)` for dependency checking.
- [ ] **4. Implement `TODO.md` Writer:**
    - [ ] 4.1. Implement writer tree -> `TODO.md` (recalculates SIDs based on hierarchy, writes immutable UID, status, text, dependency comments, preserves standard compliance).
    - [ ] 4.2. Define strategy for non-task comments.
    - [ ] 4.3 Ensure output is compliant with the chosen Linting standard.
- [ ] **5. Implement Core Dependency Logic:**
    - [ ] 5.1. Implement upward propagation for non-`[C]` status based on UID relationships.
    - [ ] 5.2. Define parent/sibling completion check logic based on UIDs.
    - [ ] 5.3. Implement `is_actionable(task_uid, tree)` checking dependency UIDs.
    - [ ] 5.4. Integrate logic into status modification and `next` command.
- [ ] **6. Implement `zlt todo` Subcommands (using `click`):**
    - [ ] 6.1. **`zlt todo add <parent_sid_or_uid> "<task_text>" [--id <new_sid_suffix>] [--status <S>] [--depends UID1,UID2]`**: Adds task, generates+stores UID, calculates initial SID. Adds `# DEPENDS_ON:`.
    - [ ] 6.2. **`zlt todo set-status <sid_or_uid> <STATUS> [--recursive]`**: Finds task by SID/UID, updates status via UID. Outputs "Next Action".
    - [ ] 6.3. **`zlt todo complete-verification <sid_or_uid> --passed` / `--failed`**: Finds task by SID/UID, triggers status change via UID, outputs next action.
    - [ ] 6.4. **`zlt todo depends <sid_or_uid> <dependency_uid> [--remove]`**: Finds task by SID/UID, modifies `# DEPENDS_ON:` comment using UIDs.
    - [ ] 6.5. **`zlt todo remove <sid_or_uid>`**: Finds task by SID/UID, removes node (identified by UID) and children.
    - [ ] 6.6. **`zlt todo list [--phase <X>] [--status <S>] [--all-phases] [--actionable]`**: Lists tasks (showing SID, UID, Status, Text). `--actionable` uses UID logic.
    - [ ] 6.7. **`zlt todo show <sid_or_uid>`**: Finds task by SID/UID, shows details (incl. UID, dependency UIDs).
    - [ ] 6.8. **`zlt todo next`**: Finds first actionable task based on UID dependencies, prints SID/UID/Text, outputs next action.
    - [ ] 6.9. **`zlt todo add-phase "<Phase Title>" [--activate]`**: Adds phase header.
    - [ ] 6.10. **`zlt todo activate-phase <phase_id>` / `deactivate-phase <phase_id>`**: Adds/removes Active Phase marker.
    - [ ] 6.11 Ensure commands load, modify tree (via UIDs), and save tree back to `TODO.md` (recalculating SIDs).
- [ ] **7. Implement Timestamp Management:**
    - [ ] 7.1. Decide when to update timestamps (e.g., on transition *to* `[C]`).
    - [ ] 7.2. Implement parsing/updating logic, storing alongside task status/UID.
- [ ] **8. Write Comprehensive Tests (TDD):**
    - [ ] 8.1. Test parser (statuses, SID/UID extraction, active marker, dependencies via UID, malformed inputs).
    - [ ] 8.2. Test writer (SID recalculation, UID output, status output, standard compliance, dependency comments).
    - [ ] 8.3. Test each command (SID/UID lookup, tree modification via UID, status handling, next action output, verification outcomes).
    - [ ] 8.4. **Crucially:** Test dependency logic thoroughly (upward propagation via UID, `is_actionable` via UID, `zlt todo next` finding correct task via UID).
    - [ ] 8.5 Test edge cases (root tasks, empty file, circular dependencies via UID).
    - [ ] 8.6. Add test step: Validate `TODO.md` output using the chosen external Markdown linter tool.
- [ ] **9. Documentation:**
    - [ ] 9.1. Update user docs (commands, statuses, SID/UID concept, dependencies via UID, active phase, `next` usage, verification commands).
    - [ ] 9.2. Ensure `docs/todo_format_guidelines.md` is comprehensive (incl. UID format/placement).
    - [ ] 9.3 **Add note that `pytest` linking via UIDs (`@zlf_task_id(<UID>)`) is deferred to a future phase.**

## **Phase O: Tool Execution & Integration**
# Goal: Develop a seamless integration between ZLT and the selected tool ecosystem, ensuring that tools are executed efficiently and results are accurately interpreted.

- [ ] **1. Develop Tool Execution Framework:**
    - [ ] Implement a generic framework for tool execution that abstracts away tool-specific details.
    - [ ] Define a common interface for tool execution and result interpretation.
- [ ] **2. Integrate with Existing Tools:**
    - [ ] Identify and integrate with existing tools that are part of the tool ecosystem.
    - [ ] Develop tool-specific modules to handle tool-specific configurations and execution logic.
- [ ] **3. Implement Tool-Specific Configuration:**
    - [ ] Develop configuration templates for each tool that can be customized via `pyproject.toml`.
    - [ ] Implement tool-specific configuration management to ensure consistency across tools.
- [ ] **4. Implement Tool-Specific Result Interpretation:**
    - [ ] Develop specific parsers for tool-specific output formats.
    - [ ] Implement tool-specific result interpretation logic to extract meaningful information.
- [ ] **5. Implement Tool-Specific Reporting:**
    - [ ] Develop tool-specific reporting modules to generate standardized reports.
    - [ ] Implement tool-specific reporting integration into the ZLT workflow.
- [ ] **6. Implement Tool-Specific Error Handling:**
    - [ ] Develop tool-specific error handling mechanisms to manage and report tool-specific errors.
- [ ] **7. Implement Tool-Specific Logging:**
    - [ ] Develop tool-specific logging modules to capture tool-specific logs.
    - [ ] Implement tool-specific logging integration into the ZLT workflow.
- [ ] **8. Implement Tool-Specific Configuration Management:**
    - [ ] Develop tool-specific configuration management modules to handle tool-specific configurations.
    - [ ] Implement tool-specific configuration management integration into the ZLT workflow.
- [ ] **9. Implement Tool-Specific Dependency Tracking:**
    - [ ] Develop tool-specific dependency tracking modules to track tool-specific dependencies.
    - [ ] Implement tool-specific dependency tracking integration into the ZLT workflow.
- [ ] **10. Implement Tool-Specific Test Integration:**
    - [ ] Develop tool-specific test integration modules to integrate tool-specific tests into the ZLT workflow.
    - [ ] Implement tool-specific test integration integration into the ZLT workflow.

## **Phase P: ZLT-Dev Documentation & Best Practices**
# Goal: Document the ZLT development process, best practices, and common pitfalls to aid future development and maintenance.

- [ ] **1. Develop ZLT-Dev Documentation:**
    - [ ] Create a comprehensive developer guide that covers all aspects of ZLT development.
    - [ ] Include detailed API documentation for all modules and components.
    - [ ] Provide examples and best practices for common use cases.
- [ ] **2. Develop Best Practices Document:**
    - [ ] Create a document that outlines best practices for ZLT development.
    - [ ] Include guidelines for code quality, testing, and deployment.
- [ ] **3. Develop Common Pitfalls Document:**
    - [ ] Create a document that highlights common pitfalls and how to avoid them.
    - [ ] Include troubleshooting tips and debugging strategies.
- [ ] **4. Implement Code Review Process:**
    - [ ] Develop a code review process that ensures code quality and consistency.
    - [ ] Include automated code review tools and integration into the development workflow.
- [ ] **5. Implement Continuous Integration/Continuous Deployment (CI/CD) Pipeline:**
    - [ ] Develop a CI/CD pipeline that integrates with GitHub Actions.
    - [ ] Implement automated testing and deployment workflows.
- [ ] **6. Implement Version Control Best Practices:**
    - [ ] Develop version control best practices document.
    - [ ] Include guidelines for branching, merging, and tagging.
- [ ] **7. Implement Documentation Best Practices:**
    - [ ] Develop documentation best practices document.
    - [ ] Include guidelines for writing clear and concise documentation.
- [ ] **8. Implement Code Quality Tools:**
    - [ ] Develop code quality tools and integration into the development workflow.
    - [ ] Include static analysis tools, linting, and formatting tools.
- [ ] **9. Implement Testing Best Practices:**
    - [ ] Develop testing best practices document.
    - [ ] Include guidelines for unit testing, integration testing, and end-to-end testing.
- [ ] **10. Implement Deployment Best Practices:**
    - [ ] Develop deployment best practices document.
    - [ ] Include guidelines for packaging, deployment, and monitoring.

## **Phase M: Test Coverage for Phase L (`zlt tools sync`)**
# Goal: Ensure robust test coverage for the complex logic implemented in Phase L before proceeding.
- [x] **M.1:** Unit tests for `hierarchical_utils.py` (specifically `parse_to_nested_dict`, `check_list_conflicts`, `get_effective_status`).
- [x] **M.2:** Unit tests for `tools_dir_scanner.py::scan_directory_for_definitions`.
- [x] **M.3:** Unit tests for `tool_index_utils.py` (all functions, including CRC script logic/helpers if not covered separately).
  - [x] Tests for `scripts/update_json_crc_tool.py` (covering success, errors: file not found, missing entries/CRCs, JSON errors, write errors, arg parsing, edge cases).
- [x] **M.4:** Unit tests for `tool_path_utils.py::command_sequence_to_path_parts`.
- [x] **M.5:** Unit tests for Podman/baseline generation helper functions in `sync.py` (e.g., `_prepare_command_for_container`, `_run_podman_command`) mocking `subprocess.run`.
- [x] **M.6:** Integration tests for `zlt tools sync` using `CliRunner`.
  - [x] Mock `_start_podman_runner` and `_run_parallel_baseline_processing` initially.
  - [x] Test Step 3/4/7 failures (invalid JSON, conflicts, unclassified tools).
  - [x] Test Step 6 success/update logic (mocking baseline generator return values).
  - [x] Test Step 6 timestamp logic (`--check-since`, `--update-since`).
  - [x] Test Step 6 warning for missing definition files.
  - [x] Test Step 9 subcommand discovery/indexing.
  - [x] Test Step 10 completion message and index update (mocking).
  - [x] Test `--dry-run` flag.
  - [x] Test `--prune` flag.
- [ ] **M.7:** Integration tests for Podman execution (unmocked `_start_podman_runner`, `_run_parallel_baseline_processing`).
    - [ ] Requires Podman installed.
    - [ ] Test actual container setup, dependency installation, command execution (`--help`), baseline file creation, and cleanup.
    - [ ] Test handling of Podman errors (start failure, exec failure).
- [ ] **M.8:** Add `TODO` for Podman Optimization:
    - [ ] Add a TODO item to optimize the Podman setup in `sync.py` to persist the container or reuse installed dependencies, avoiding redundant environment creation and downloads on each run.


## **Phase N: ZLT Dev Capabilities and Initial Usage**