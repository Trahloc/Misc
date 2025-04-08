# Project TODO List

## Phase 1: Project Initialization & Configuration

- [x] 1. Create Directory Structure
- [x] 2. Populate `pyproject.toml` (incl. `poetry2conda` -> `poetry-plugin-export` fixes, build-system fix)
- [x] 3. Populate `.gitignore` (incl. `requirements*.txt`)
- [x] 4. Populate `README.md` (incl. framework filename fix & updated setup instructions)
- [x] 5. Populate `.pre-commit-config.yaml`
- [x] 6. Create `scripts/generate_requirements.sh` & make executable (renamed from `generate_environment.sh`)
- [x] 7. Environment Setup (Revised Workflow):
  - [x] Install `poetry` & `poetry-plugin-export` in bootstrap env (`localbin`)
  - [x] Run `poetry lock`
  - [x] Generate `requirements.txt` & `requirements-dev.txt` (using `poetry export`)
  - [x] Create minimal `environment.yml` (using `requirements.txt`)
  - [x] Run `micromamba env create -f environment.yml` (using `conda` alias)
  - [x] Install dev dependencies (`conda run -n zeroth_law pip install -r requirements-dev.txt`)
  - [x] Install `pre-commit` manually (workaround for export issue)
  - [x] Run `conda run -n zeroth_law pre-commit install`
  - [x] Run `conda run -n zeroth_law pip install -e .` (Install project editable)

## Phase 1.5: Legacy System Analysis

- [x] Analyze `.legacy` variant code and identify core functionalities.
- [x] Document the purpose of each major component/function in the legacy system. (See [docs/legacy/analysis_summary.md](docs/legacy/analysis_summary.md))
- [x] List specific features/checks performed by the legacy system to guide refactoring. (See [docs/legacy/analysis_summary.md](docs/legacy/analysis_summary.md))

## Phase 2: Core Logic & TDD

- [x] 8. Identify First Feature (based on `ZerothLawAIFramework.py313.md`) - Load `pyproject.toml` and extract Python version.
- [x] 9. Write Failing Test (Red)
- [x] 10. Implement Minimal Code (Green)
- [x] 11. Refactor
- [x] 12. Commit (using Conventional Commits)

## Phase 3: Iterative Development & Refinement

- [ ] 13. Repeat TDD Cycle for subsequent features
  - [x] 8a. Identify Next Feature (Informed by Legacy) - Find Python files to analyze.
  - [x] 9a. Write Failing Test (Red)
  - [x] 10a. Implement Minimal Code (Green)
  - [x] 11a. Refactor
  - [x] 12a. Commit (using Conventional Commits)
  - [x] 8b. Identify Next Feature - Analyze AST for missing public function docstrings (D103).
  - [x] 9b. Write Failing Test (Red)
  - [x] 10b. Implement Minimal Code (Green)
  - [x] 11b. Refactor
  - [x] 12b. Commit
  - [ ] 8c. Identify Next Feature - Check for Header Comment Presence (Principle #11)
  - [ ] 9c. Write Failing Test (Red)
  - [ ] 10c. Implement Minimal Code (Green)
  - [x] 11c. Refactor
  - [x] 12c. Commit
  - [ ] 8d. Identify Next Feature - Check for Footer Comment Presence (Principle #11)
  - [ ] 9d. Write Failing Test (Red)
  - [ ] 10d. Implement Minimal Code (Green)
  - [x] 11d. Refactor
  - [x] 12d. Commit
  - [ ] 8e. Identify Next Feature - Check Cyclomatic Complexity
  - [ ] 9e. Write Failing Test (Red)
  - [ ] 10e. Implement Minimal Code (Green)
  - [x] 11e. Refactor
  - [x] 12e. Commit
  - [ ] 8f. Identify Next Feature - Check Max Parameters per Function
  - [ ] 9f. Write Failing Test (Red)
  - [ ] 10f. Implement Minimal Code (Green)
  - [x] 11f. Refactor
  - [x] 12f. Commit
  - [ ] 8g. Identify Next Feature - Check Max Statements per Function
  - [ ] 9g. Write Failing Test (Red)
  - [ ] 10g. Implement Minimal Code (Green)
  - [x] 11g. Refactor
  - [x] 12g. Commit
  - [ ] 8h. Identify Next Feature - Check Max Executable Lines per File
  - [ ] 9h. Write Failing Test (Red)
  - [ ] 10h. Implement Minimal Code (Green)
  - [ ] 11h. Refactor
  - [ ] 12h. Commit
- [ ] 14. Continuously Integrate Tooling (`ruff`, `mypy`, `pylint`, `pytest --cov`)
- [ ] 15. Set up CI (`.github/workflows/ci.yml`)
- [ ] 16. Final Documentation & Review:
  - [ ] Ensure in-file documentation pattern in all source files
  - [ ] Update `README.md` (Usage, Contributing sections)
  - [ ] Final review against all requirements
