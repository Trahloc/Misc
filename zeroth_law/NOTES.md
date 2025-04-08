# Development Notes & Decisions

## Pre-commit, Ruff Format, and IDE Integration (Recovered Discussion)

**Initial Problem:** The `ruff-format` pre-commit hook was causing commit failures even when it successfully formatted files, because pre-commit halts on *any* file modification by a hook. This created friction, conflicting with Zeroth Law's goal of smooth flow.

**Constraint:** Removing `ruff-format` from pre-commit entirely is not allowed, as it serves as a critical final quality gate for consistent style (Zeroth Law Principle #4).

**Exploration & Reasoning:**

1.  **Comparing `ruff format` and `black`:** The initial thought was whether `black` might handle pre-commit differently. Conclusion: No, the standard `black` hook also causes pre-commit to halt on modification. The issue stems from pre-commit's core design (fail on change), not a specific tool's behavior.
2.  **`ruff check --fix` Behavior:** We previously configured `ruff check --fix` *without* the `--exit-non-zero-on-fix` flag. This allows the *linter* hook to fix many stylistic issues (like trailing whitespace) silently (exit 0) during commit. It only fails the commit if it finds errors it *cannot* fix.
3.  **Why the `ruff check --fix` solution doesn't apply to `ruff-format`:** The `--exit-non-zero-on-fix` flag is specific to linters-with-fixing. Formatters like `ruff-format` don't have an equivalent flag because their primary job *is* modification. Their successful operation inherently triggers pre-commit's halt-on-modification behavior.
4.  **Idea: Benign vs. Significant Formatting:** Could we configure `ruff-format` to only apply "benign" fixes silently? Conclusion: No, `ruff-format` applies all rules comprehensively, and pre-commit doesn't have a mechanism to ignore specific "benign" modifications from a hook.
5.  **Idea: Leverage IDE:** The user suggested shifting the focus from Git hooks to the IDE (Cursor/VS Code).

**Solution: IDE Format-on-Save + Pre-commit Safety Net:**

1.  **Configure Format-on-Save:** Set up the IDE (Cursor/VS Code) with the Ruff extension to automatically run `ruff format` every time a Python file is saved.
    *   Key settings: `editor.formatOnSave: true`, `editor.defaultFormatter: charliermarsh.ruff`.
2.  **Keep `ruff-format` in `pre-commit`:** The `ruff-format` hook remains in `.pre-commit-config.yaml`.
3.  **Workflow Result:**
    *   Developer saves file -> IDE runs `ruff format` -> File is instantly corrected.
    *   Developer runs `git add` -> Already formatted file is staged.
    *   Developer runs `git commit` -> `pre-commit` runs hooks.
    *   `ruff-format` hook runs, sees the file is already correct, makes no changes, exits 0.
    *   Commit proceeds smoothly unless other hooks (like `ruff check --fix` finding unfixable errors, or `mypy`) fail.
    *   The pre-commit hook acts as a crucial *safety net* for cases where Format-on-Save might have been missed, but it's no longer the primary source of formatting *friction*.

**Conclusion:** This approach respects the Zeroth Law constraint of guaranteed formatting (via the pre-commit hook) while significantly improving the developer workflow smoothness by leveraging IDE automation. 