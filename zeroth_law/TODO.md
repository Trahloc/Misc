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
- [ ] ZLT: Refactor `cli.py::run_audit` to utilize the new orchestration engine.

## Phase Y: ZLT-dev - Capability Mapping & Optimization
# Goal: Continuously improve ZLT's understanding of consultant tools and optimize its default configuration based on evidence from real tests.
- [ ] ZLT-dev: Design test harvesting mechanism (initially target ZLT's own test suite).
- [ ] ZLT-dev: Implement unrestricted consultant tool execution against harvested tests.
- [ ] ZLT-dev: Design SQLite schema for storing capability map (Rule -> Tool -> Principle -> Test File -> etc.).
- [ ] ZLT-dev: Implement output parsing and correlation logic to populate the SQLite capability map.
- [ ] ZLT-dev: Develop logic to query the map and identify unique contributions vs. overlaps.
- [ ] ZLT-dev: Design feedback mechanism/process to update ZLT's default consultant configurations based on map insights (e.g., disable empirically redundant rules).

## Backlog / Ideas

- [ ] More sophisticated exclusion logic (`.gitignore` style?).
- [ ] Auto-fixing capabilities (e.g., add missing footers).
- [ ] Template generation/validation features.
- [ ] Specific checks for AI-generated code patterns?
- [ ] Integration with `pre-commit` beyond just running the tool.
- [ ] Create a VS Code/Cursor extension for direct IDE integration of Zeroth Law checks.
- [ ] Support for automatically migrating existing projects to Zeroth Law compliance.
- [ ] Documentation on multi-project monorepo best practices with Zeroth Law.
