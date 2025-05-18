# Code-Level Issues & TODOs (Auto-Generated)

Generated: 2025-04-29T16:24:13+08:00

Source                                                                      | Line  | Issue / TODO
----------------------------------------------------------------------------|-------|------------------------------------------------------------------------------------------
src/zeroth_law/action_runner.py                                             | 115   | Consider if default paths should be used with the specific option.
src/zeroth_law/actions/lint/python.py                                       | 12    | Replace basic logging with structlog configured instance
src/zeroth_law/actions/lint/python.py                                       | 34    | Use config to customize ruff args (e.g., specific files, config path)
src/zeroth_law/actions/lint/python.py                                       | 77    | Add execution for other configured linters (e.g., targeted pylint)
src/zeroth_law/analyzer/python/analyzer.py                                  | 237   | Add more sophisticated filtering for tuple-based violations later
src/zeroth_law/analyzer/python/statements.py                                | 61    | Revisit robust docstring detection.
src/zeroth_law/analyzers/precommit_analyzer.py                              | 13    | Make this configurable?
src/zeroth_law/cli.py                                                       | 163   | Add more sophisticated configuration based on flags
src/zeroth_law/cli.py                                                       | 170   | Implement color handling
src/zeroth_law/cli.py                                                       | 316   | Add dynamic commands based on capabilities/mapping later
src/zeroth_law/dev_scripts/debug_fix_headers.py                             | 15    | [Suppressed] Module import not at top of file (E402)
src/zeroth_law/dev_scripts/debug_fix_headers.py                             | 15    | [Suppressed] Module import not at top of file (E402)
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 2     | comments and # noqa: E402 suppressions
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 2     | comments and # noqa: E402 suppressions
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 44    | ' or '# noqa: E402'
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 44    | ' or '# noqa: E402'
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 77    | ")) {
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 77    | ")) {
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 78    | ") + length("# TODO:"));
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 78    | ") + length("# TODO:"));
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 80    | [Suppressed] Module import not at top of file (E402)
src/zeroth_law/dev_scripts/generate_code_todos.sh                           | 80    | [Suppressed] Module import not at top of file (E402)
src/zeroth_law/dev_scripts/regenerate_index.py                              | 265   | Implement override mechanism (e.g., read from dedicated config?).
src/zeroth_law/dev_scripts/regenerate_index.py                              | 265   | Implement override mechanism (e.g., read from dedicated config?).
src/zeroth_law/dev_scripts/regenerate_index.py                              | 34    | Replace with robust loading, potentially using config_loader logic
src/zeroth_law/dev_scripts/regenerate_index.py                              | 34    | Replace with robust loading, potentially using config_loader logic
src/zeroth_law/dev_scripts/regenerate_index.py                              | 59    | Reuse/refactor logic from tool_discovery.py if possible
src/zeroth_law/dev_scripts/regenerate_index.py                              | 59    | Reuse/refactor logic from tool_discovery.py if possible
src/zeroth_law/runner.py                                                    | 73    | Add logic for handling default behaviors from metadata if needed
src/zeroth_law/subcommands/audit/audit.py                                   | 140   | Add pre-commit violations to JSON output structure
src/zeroth_law/subcommands/tools/reconcile.py                               | 11    | Move these utilities to a more central location (e.g., common or tools_lib)
src/zeroth_law/subcommands/tools/sync.py                                    | 22    | Move baseline_generator to a shared location
src/zeroth_law/subcommands/tools/sync.py                                    | 34    | Move ToolIndexHandler and helpers to shared location if not already
tests/test_interaction/test_dev_scripts/test_ensure_txt_baselines_exist.py  | 9     | This might be better handled by packaging or pytest config
tests/test_zeroth_law/test_cli/test_dynamic_options.py                      | 54    | Handle cases where description might be on the next line
tests/test_zeroth_law/test_common/test_config_validation.py                 | 13    | [Suppressed] Module import not at top of file (E402)
tests/test_zeroth_law/test_common/test_config_validation.py                 | 14    | [Suppressed] Module import not at top of file (E402)
tests/test_zeroth_law/test_common/test_config_validation.py                 | 15    | [Suppressed] Module import not at top of file (E402)
tests/test_zeroth_law/test_common/test_config_validation.py                 | 20    | [Suppressed] Module import not at top of file (E402)
tests/test_zeroth_law/test_common/test_file_finder.py                       | 164   | Add more tests for exclude_files patterns and edge cases
tests/test_zeroth_law/test_common/test_git_utils.py                         | 258   | Add tests for hook installation/restoration (file writing, permissions)
tests/test_zeroth_law/test_common/test_path_utils.py                        | 22    | [Suppressed] Module import not at top of file (E402)
tests/test_zeroth_law/test_common/test_path_utils.py                        | 23    | [Suppressed] Module import not at top of file (E402)
tests/test_zeroth_law/test_dev_scripts/test_capture_txt_tty_output.py       | 163   | Add tests for other branches in capture_tty_output:
tests/test_zeroth_law/test_dev_scripts/test_code_map/test_map_reporter.py   | 287   | Add tests for error handling during DB queries (might need mocking) - Partially addressed
tests/test_zeroth_law/test_lib/test_tooling/test_baseline_generator.py      | 23    | Add actual tests covering:
tests/test_zeroth_law/test_runner.py                                        | 202   | Add tests for:
tests/test_zeroth_law/test_subcommands/test_tools/test_definition.py        | 286   | Add failure case tests for remove, set, map, unmap
tests/test_zeroth_law/test_subcommands/test_tools/test_definition.py        | 90    | Add more tests for add-capability:

NOTE: This file is auto-generated by src/zeroth_law/dev_scripts/generate_code_todos.sh. Do not edit directly.
