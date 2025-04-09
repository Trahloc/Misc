# Project TODO List

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

- [ ] 1. **Line Count Check:** (`analyzer/python/line_counts.py`) Implement `analyze_line_counts` (TDD). Integrate into `analyze_file_compliance`.
- [ ] 2. **Complexity Check:** (`analyzer/python/complexity.py`, `ast_utils.py`) Implement `analyze_complexity` using `ast` (TDD). Integrate.
- [ ] 3. **Docstring Check:** (`analyzer/python/docstrings.py`, `ast_utils.py`) Implement `analyze_docstrings` (module, function, class - TDD). Integrate.
- [ ] 4. **Parameter Count Check:** (`analyzer/python/parameters.py`, `ast_utils.py`) Implement `analyze_parameters` (TDD). Integrate.
- [ ] 5. **Statement Count Check:** (`analyzer/python/statements.py`, `ast_utils.py`) Implement `analyze_statements` (TDD). Integrate.
- [ ] 6. **Refactor Long/Complex Code:** Address violations flagged for line count, complexity, parameters (e.g., in `cli.py`, `config_loader.py`, `analyzer.py`).
- [ ] 7. **Fix Remaining Header/Footer Issues (ONGOING - Pivoted):** Debug why edits failed or manually fix remaining header/footer violations in files like `src/__init__.py`, test `__init__.py` files, etc.
    - [ ] 7.1. Create `tq()` helper for triple quotes in `tests/test_utils.py`.
    - [ ] 7.2. Refactor test strings in `test_file_analyzer.py` to use `tq()`.
    - [ ] 7.3. Resume debugging `check_header_compliance` logic.
- [ ] 8. **Configuration Enhancements:**
    - [ ] Support `ignore_codes` in `analyze_file_compliance` filtering.
    - [ ] Add validation for config values (e.g., using Pydantic).
    - [ ] Consider XDG Base Directory support for global config (`config_loader.py`).
- [ ] 9. **Reporting Enhancements:**
    - [ ] Improve detail/formatting of violation reports in `cli.py`.
    - [ ] Consider different output formats (JSON, etc.).
- [ ] 10. **CI Workflow:** Set up GitHub Actions workflow (`.github/workflows/ci.yml`) using `poetry`.

## Phase 3: Framework Integration & Polish

- [x] 1. **Framework Doc Update:** Update `frameworks/python/ZerothLawAIFramework.py313.md` to reflect `poetry` standardization.
- [ ] 2. **Custom Git Hook Management (TDD):**
    - [ ] 2.1. Define `install-git-hook` and `restore-git-hooks` commands in `cli.py`.
    - [ ] 2.2. Implement core logic for finding Git root and project roots.
    - [ ] 2.3. Implement logic to generate the custom multi-project pre-commit hook script content.
    - [ ] 2.4. Implement file writing and permission setting for installing the hook.
    - [ ] 2.5. Implement logic for `restore-git-hooks` (running `pre-commit install`).
    - [ ] 2.6. Write tests covering script generation, installation, restoration, and edge cases.
- [ ] 3. **Final README Review:** Ensure README is complete and accurate, including hook setup.
- [ ] 4. **License Review:** Confirm chosen license (CC0) is appropriate.
- [ ] 5. **Publishing Prep (Optional):** Prepare for potential PyPI release.

## Backlog / Ideas

- [ ] More sophisticated exclusion logic (`.gitignore` style?).
- [ ] Auto-fixing capabilities (e.g., add missing footers).
- [ ] Template generation/validation features.
- [ ] Specific checks for AI-generated code patterns?
- [ ] Integration with `pre-commit` beyond just running the tool.
