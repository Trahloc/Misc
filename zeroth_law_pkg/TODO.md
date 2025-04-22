# Project TODO List

**== INTERRUPTED (YYYY-MM-DDTHH:MM:SS+ZZ:ZZ - AI: Run `date --iso-8601=seconds`) ==**
**Reason:** User is renaming the project root directory according to the new ZLF convention (`project_pkg/src/project/`).
**Last Action:** Successfully fixed `ImportError` for `find_project_root` in `src/zeroth_law/cli.py`.
**Next Action:** Re-run `pytest tests/test_cli.py` to verify the fix and CLI dispatch mechanism after the project rename.
**====**

## Phase 1: Core Setup & Basic Compliance Checks (Initial TDD)

- [x] 1. Initialize project structure (`poetry new`, basic dirs like `src/zeroth_law`, `tests`).
- [x] 2. Populate `pyproject.toml` (incl. build-system fix)
- [x] 3. Set up `ruff` configuration (`pyproject.toml`).
- [x] 4. Set up `mypy` configuration (`pyproject.toml`).
- [x] 5. Set up `pytest` configuration (`pyproject.toml`, basic `conftest.py` if needed).
- [x] 6. Set up `pre-commit` (`.pre-commit-config.yaml` with `ruff`, `mypy`).
- [x] 7. Create initial `README.md` with setup instructions (using `poetry`).
- [x] 8. Implement basic `file_finder.py` (TDD): Find `.py` files, exclude defaults.
- [x] 9. Implement basic `config_loader.py` (TDD): Load basic settings (e.g., `exclude_dirs`, `exclude_files`) from `[tool.zeroth-law]` in `pyproject.toml`, merging with defaults.
- [x] 10. Implement basic `cli.py` using `click` (TDD): Argument parsing (paths, recursive, verbosity, color), setup logging (`structlog`), call config loader, call file finder, orchestrate basic audit flow.
- [x] 11. Implement basic Header Check (`analyzer/python/analyzer.py::check_header_compliance`).
- [x] 12. Implement basic Footer Check (`analyzer/python/analyzer.py::check_footer_compliance`).
- [x] 13. Implement main `analyze_file_compliance` orchestrator (`analyzer/python/analyzer.py`) calling header/footer checks.
- [x] 14. Integrate checks into `cli.py::run_audit`.
- [x] 15. Ensure pre-commit hooks pass (resolve initial issues, potentially adjust limits temporarily).

## Phase 2: Advanced Compliance Checks & Refinements

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

## Phase 3: Framework Integration & Polish

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
- [ ] Investigate and fix root cause of `mypy` "Source file found twice" error when executed via `action_runner.py`. Re-enable `mypy` in `tool_mapping.json` for the `lint` action once resolved. (Currently handled by pre-commit hook).
- [ ] Review and refactor suppressed `E402` (module import not at top of file) errors identified in `CODE_TODOS.md`. Remove `sys.path` modifications if redundant due to Poetry's editable install.

## Phase X: ZLT Core Orchestration Engine
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

## Phase Y: ZLT-dev - Capability Mapping & Optimization
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

## Tool Interface Definition Workflow (v3 - AI Interpretation)
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
- [ ] **Create `baseline_generator.py` and Implement `generate_or_verify_baseline`:**
    - Implement help capture (`--help | cat`).
    - Implement CRC calculation and comparison with `tool_index.json`.
    - Implement conditional `.txt` file writing.
    - Implement `tool_index.json` updates (for `crc`, `updated_timestamp`, `checked_timestamp`).
    - Implement minimal skeleton `.json` creation (only if missing, with placeholder CRC `0x00000000`).
- [ ] **Perform One-Time Structural Correction of `tool_index.json`:**
      *(Note: This is a one-off task to fix past inconsistencies and enable the automated workflow. It does NOT represent standard practice.)*
    - Ensure all entries have `updated_timestamp` and `checked_timestamp` keys (add placeholders if missing).
    - Correct any known placeholder CRCs (e.g., `zeroth-law`) to match their corresponding `.txt` baseline CRC.
- [x] **Simplify Paths:** Update paths in tests (`test_ensure_*.py`, `test_txt_json_consistency.py`).
- [x] **Update Schema Guidelines:** Add guidance to `tools/zlt_schema_guidelines.md` emphasizing the AI\'s responsibility to maintain consistency for unchanged options/args when updating `.json` files.
- [x] **Separate Capabilities:** Create `src/zeroth_law/tools/tool_capabilities.yaml` to store functional categories (Formatter, Linter, etc.), separate from CLI structure.
- [ ] **AI Task: Populate `.json` Definitions:** Systematically process `.txt` files and populate the corresponding `.json` skeleton files according to the guidelines.
-   [ ] **Review `poetry.json`:** The current `poetry.txt` seems to contain help for `poetry list` rather than the main command.
    -   Regenerate the baseline using `poetry --help` (or similar) to capture the correct help text.
    -   Repopulate `src/zeroth_law/tools/poetry/poetry.json` based on the new baseline, ensuring it includes core subcommands like `add`, `install`, `build`.
-   [ ] **Implement Schema Validation Test:** Create `tests/test_tool_defs/test_json_schema_validation.py` to validate `value_name` structure, `nargs` consistency, and whitespace rules in names/flags.
