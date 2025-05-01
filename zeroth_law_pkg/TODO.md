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

## **Phase K: ... (Next Phase)**
# ...

## **Phase L: Implement Tool Sync Workflow (10-Step Plan)**
# Goal: Implement the robust, deterministic `zlt tools sync` workflow based on the 10-step plan defined on 2025-05-01.
# NOTE: Add completion timestamp `(YYYY-MM-DDTHH:MM:SS+ZZ:ZZ - Run 'date --iso-8601=seconds')` to each item upon completion.

### **Phase 1: Setup & Reconciliation (Steps 1-5)**

- [ ] **Step 1: Environment Setup** (`2025-05-01T12:15:37+08:00`)
  - [ ] 1.1 Action: Ensure correct venv activation (implicit via `uv run`).
  - [ ] 1.2 Action: Determine absolute path to active venv `bin` directory (e.g., `sys.prefix`/`bin`) -> `venv_bin_path`.
  - [ ] 1.3 Verification: Log the detected `venv_bin_path`.

- [ ] **Step 2: Discover Executables** (`2025-05-01T12:15:37+08:00`)
  - [ ] 2.1 Action: Scan `venv_bin_path` directory.
  - [ ] 2.2 Action: Create raw list `raw_executables` of all executable file names.
  - [ ] 2.3 Verification: Log the count of `raw_executables`.

- [ ] **Step 3: Filter & Validate Whitelist/Blacklist** (`2025-05-01T12:15:37+08:00`)
  - [ ] 3.1 Action: Load hierarchical whitelist/blacklist from `pyproject.toml` -> `whitelist_tree`, `blacklist_tree` (using `src/zeroth_law/lib/config_loader.py`).
  - [ ] 3.2 Action: Implement/Verify `check_list_conflicts(whitelist_tree, blacklist_tree)` (in `src/zeroth_law/lib/hierarchical_utils.py`?).
  - [ ] 3.3 Action: Call `check_list_conflicts`, fail immediately if conflicts found.
  - [ ] 3.4 Action: Implement/Verify `get_effective_status(sequence, whitelist_tree, blacklist_tree)` in `src/zeroth_law/lib/hierarchical_utils.py` (handles precedence, wildcards).
  - [ ] 3.5 Action: Initialize `managed_executables = []`, `unclassified_executables = []`.
  - [ ] 3.6 Action: Iterate `raw_executables`, use `get_effective_status` to populate `managed_executables` and `unclassified_executables`.
  - [ ] 3.7 Action: If `unclassified_executables` not empty, fail immediately with clear instructions to use `zlt tools add-whitelist/add-blacklist`.
  - [ ] 3.8 Verification: Log count of `managed_executables`.

- [ ] **Step 4: Reconcile `tools/` Directory Structure** (`2025-05-01T12:15:37+08:00`)
  - [ ] 4.1 Action: Define `tools_base_dir = Path("src/zeroth_law/tools/")`.
  - [ ] 4.2 Action: Get list `existing_tool_dirs` of immediate subdirectories.
  - [ ] 4.3 Action: Initialize `orphan_dirs = []`.
  - [ ] 4.4 Action: Iterate `existing_tool_dirs`, use `get_effective_status` to populate `orphan_dirs` if status is BLACKLISTED or UNSPECIFIED.
  - [ ] 4.5 Action: If `orphan_dirs` not empty, fail immediately with instructions to whitelist tool or remove directory.
  - [ ] 4.6 Action: Iterate `managed_executables`, ensure `tools_base_dir / tool_name` exists, create if missing (`os.makedirs`).
  - [ ] 4.7 Verification: `tools/` structure aligns with `managed_executables`.

- [ ] **Step 5: Identify Effectively Whitelisted Command Sequences** (`2025-05-01T12:15:37+08:00`)
  - [ ] 5.1 Action: Initialize `whitelisted_sequences = []`.
  - [ ] 5.2 Action: Add base sequences from `managed_executables` to `whitelisted_sequences`.
  - [ ] 5.3 Action: Implement/Verify recursive `scan_tool_dirs(current_dir, current_sequence, ...)` in `src/zeroth_law/lib/tooling/tools_dir_scanner.py` (uses `get_effective_status`, handles recursion).
  - [ ] 5.4 Action: Call `scan_tool_dirs` for each managed tool's base directory.
  - [ ] 5.5 Action: Combine base and scanned sequences into final `whitelisted_sequences`.
  - [ ] 5.6 Verification: Log total count of `whitelisted_sequences`.

### **Phase 2: Baseline Generation & Indexing (Step 6)**

- [ ] **Step 6: `.txt` Baseline Generation & Verification** (`2025-05-01T12:15:37+08:00`)
  - [ ] 6.1 Action: Initialize `recent_update_warning_count = 0`.
  - [ ] 6.2 Action: Implement/Verify `ToolIndexHandler` class (in `src/zeroth_law/lib/tooling/tool_index_handler.py`?) with load/save/update/add methods for `tool_index.json`. Load index.
  - [ ] 6.3 Action: Define deterministic Podman container name.
  - [ ] 6.4 Action: Implement Podman container setup/teardown context management within `sync` command (stop/rm existing, start new, stop/rm finally, read-only mounts).
  - [ ] 6.5 Action: Loop through each `sequence` in `whitelisted_sequences`:
    - [ ] 6.5.1 Lookup: Get entry from loaded index via `ToolIndexHandler`. Continue if not found.
    - [ ] 6.5.2 Timestamp Check: Use `--check-since` (default 24h) and `--force`. Continue if check passes.
    - [ ] 6.5.3 Podman Execution:
      - [ ] 6.5.3.1 Construct help command args (e.g., `['ruff', 'check', '--help']`).
      - [ ] 6.5.3.2 Implement/Verify `_execute_capture_in_podman(sequence_args, container_name, ...)` in `src/zeroth_law/lib/tooling/baseline_generator.py` (builds `podman exec sh -c "export PATH...; timeout ... | cat"`, runs `subprocess`, handles errors, returns stdout).
      - [ ] 6.5.3.3 Call `_execute_capture_in_podman`, handle exceptions.
    - [ ] 6.5.4 CRC Calculation: Calculate `new_crc = zlib.crc32(output)` -> hex string.
    - [ ] 6.5.5 Comparison & Update:
      - [ ] 6.5.5.1 If `new_crc == index_crc`: Call `ToolIndexHandler.update_checked_timestamp(sequence, now)`.
      - [ ] 6.5.5.2 If `new_crc != index_crc`: Use `--update-since` (default 48h), warn/increment `recent_update_warning_count` if needed. Write output to `.txt` file. Call `ToolIndexHandler.update_entry(sequence, crc=new_crc, updated_timestamp=now, ...)`.
  - [ ] 6.6 Action: After loop, call `ToolIndexHandler.save_index()`.
  - [ ] 6.7 Action: If `recent_update_warning_count >= 3`, fail immediately reporting rapid update issue.

### **Phase 3: AI Interpretation & Validation (Steps 7-8)**

- [ ] **Step 7: Identify First Missing/Outdated `.json`** (`2025-05-01T12:15:37+08:00`)
  - [ ] 7.1 Action: Reload index via `ToolIndexHandler`.
  - [ ] 7.2 Action: Loop through `tool_index.json` entries (`sequence_key`, `entry_data`).
  - [ ] 7.3 Action: For each entry:
    - [ ] 7.3.1 Check `get_effective_status`. Continue if not WHITELISTED.
    - [ ] 7.3.2 Determine `txt_path`, `json_path`.
    - [ ] 7.3.3 Check if `txt_path` exists. Continue if not.
    - [ ] 7.3.4 Check if `json_path` exists. If not, `needs_interpretation = True`.
    - [ ] 7.3.5 If `json_path` exists, load JSON, get `json_crc`, compare with `index_crc`. If mismatch or placeholder, `needs_interpretation = True`.
    - [ ] 7.3.6 If `needs_interpretation`, fail immediately, report sequence/path, instruct AI to start Step 8.
  - [ ] 7.4 Outcome: If loop completes, proceed to Step 9.

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

- [ ] **Step 9: Discover & Index Subcommands** (`2025-05-01T12:15:37+08:00`)
  - [ ] 9.1 Action: Reload index. Initialize `new_sequences_added = False`.
  - [ ] 9.2 Action: Loop through `tool_index.json` entries (`parent_sequence_key`, `parent_entry_data`).
    - [ ] 9.2.1 Consistency Check: Verify parent `.json` exists and its CRC matches index. Continue if not.
    - [ ] 9.2.2 Parse JSON: Load parent JSON.
    - [ ] 9.2.3 Find Subcommands: Extract subcommand names (e.g., from `subcommands_detail`).
    - [ ] 9.2.4 Process Subcommands: For each `subcommand_name`:
      - [ ] 9.2.4.1 Construct `new_sequence_list`, `new_sequence_key`.
      - [ ] 9.2.4.2 Recursion Check: Fail if `subcommand_name == parent_sequence[-1]`.
      - [ ] 9.2.4.3 Check `get_effective_status`.
      - [ ] 9.2.4.4 If WHITELISTED and `new_sequence_key` not in index: Calculate paths, create subdir, call `ToolIndexHandler.add_entry(new_sequence_key, crc=None, ...)`, set `new_sequences_added = True`.
  - [ ] 9.3 Action: If `new_sequences_added`, call `ToolIndexHandler.save_index()`.

- [ ] **Step 10: Iteration & Completion** (`2025-05-01T12:15:37+08:00`)
  - [ ] 10.1 Check: If `new_sequences_added` was `True`, report need to re-run `sync` and exit.
  - [ ] 10.2 Check: If Step 7 completed AND `new_sequences_added` was `False`, report successful completion and exit 0.

