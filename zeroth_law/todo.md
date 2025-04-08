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

## Phase 2: Core Logic & TDD

- [x] 8. Identify First Feature (based on `ZerothLawAIFramework.py313.md`) - Load `pyproject.toml` and extract Python version.
- [x] 9. Write Failing Test (Red)
- [x] 10. Implement Minimal Code (Green)
- [x] 11. Refactor
- [ ] 12. Commit (using Conventional Commits)

## Phase 3: Iterative Development & Refinement

- [ ] 13. Repeat TDD Cycle for subsequent features
- [ ] 14. Continuously Integrate Tooling (`ruff`, `mypy`, `pylint`, `pytest --cov`)
- [ ] 15. Set up CI (`.github/workflows/ci.yml`)
- [ ] 16. Final Documentation & Review:
  - [ ] Ensure in-file documentation pattern in all source files
  - [ ] Update `README.md` (Usage, Contributing sections)
  - [ ] Final review against all requirements
