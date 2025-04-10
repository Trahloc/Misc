# Zeroth Law: AI-Driven Lua 5.1 Code Quality Framework

**Co-Author**: Trahloc colDhart
**Version**: 2025-03-23

---

## 1. PURPOSE
Define a minimal, AI-centric code quality standard for Lua 5.1. By enforcing clarity, modularity, and simplicity, you ensure immediate comprehension of each module without external references.

## 2. APPLICATION
All code changes must meet these guidelines before merging. Automated checks and AI agents apply these rules, blocking completion until the required quality is met or surpassed.

## 3. GUIDING PRINCIPLES

1. **Single Responsibility & Clear Module Boundaries**
   Limit each Lua file to one distinct purpose. Only expose the public interface via a returned table; keep internals private. By segregating responsibilities, you avoid hidden side effects and make it straightforward to modify or replace parts in isolation.

2. **First Principles Simplicity**
   Favor minimal, direct solutions over elaborate structures or clever tricks. Lua’s lean syntax makes it easy to keep code small and focused. More complexity means more risk—only accept it when you have a clear, validated benefit.

3. **Follow Exemplary Project Standards**
   Reference well-known Lua 5.1 projects (e.g., Neovim, Penlight) as architectural and stylistic benchmarks. Emulating proven patterns anchors your decisions, ensuring consistent, reliable code when uncertain.

4. **Leverage Existing Libraries (No Reinvention)**
   Turn to LuaRocks or the built-in library before writing new functionality. Established libraries are complexity-neutral—incorporate them freely if they meet your needs. This approach prevents wheel reinvention, saving time and reducing bugs.

5. **Don’t Repeat Yourself (DRY)**
   Keep shared logic in a single place. Duplicated code causes inconsistent updates and inflates technical debt. By centralizing features, you ensure changes propagate cleanly and predictably.

6. **Self-Documenting Code Structure**
   Use clear, descriptive naming for functions, variables, and modules. Each file returns a table specifying its public API. Rely on concise `--` comments to capture what a function does, its parameters, and its return value. This in-file clarity helps you (or other AI agents) grasp each module quickly.

7. **Consistent Style & Idiomatic Usage**
   Follow a unified coding style: indentation, snake_case or lowerCamelCase naming, and standard Lua 5.1 idioms. Consistency eases collaboration, automated formatting, and refactoring, letting you confidently predict how each part is structured.

8. **Comprehensive Testing & Automation**
   Every module and function should have corresponding tests. Tools like `busted` can validate correctness and catch regressions. Integrate tests into a minimal CI process, ensuring no change is merged without passing checks. With thorough tests, you can safely refactor at any time.

9. **Explicit Error Handling & Robustness**
   Surface problems early with explicit `error` calls or structured returns. Avoid silent failures. Guard against resource leaks (e.g., file handles, coroutines) using well-defined cleanup paths. When an error arises, fail fast, so you can pinpoint and address it immediately.

10. **Continuous Refactoring & Improvement**
   Iterate on the codebase regularly. Simplify design, rename functions for clarity, or break modules apart if they grow too large. Robust tests let you refine code safely without fear of breaking existing functionality.

---

## 4. IN-FILE DOCUMENTATION PATTERN

### 4.1 Header
Begin each file with a header describing its purpose and dependencies:

```lua
--[[
# PURPOSE: [Clear, single focus for this module]

## DEPENDENCIES: [List required modules or libraries]

## TODO: [Pending tasks; remove completed, add new ones]
]]
```

### 4.2 Implementation
Document functions using short, luadoc-like comments:

```lua
--- [Single-sentence summary of what the function does]
-- @param param1 [Description of param1]
-- @param param2 [Description of param2]
-- @return [What this function returns]
local function example_function(param1, param2)
  -- Implementation details
end
```

Store local functions in a table at the end for public exposure.

### 4.3 Footer
Finish each file with any known issues, recent improvements, and future tasks:

```lua
--[[
## KNOWN ERRORS: [List and categorize issues]

## IMPROVEMENTS: [Enhancements made during this session]

## FUTURE TODOs: [Ideas for further refinement or decomposition]
]]
```

---

## 5. KEY METRICS

### 5.1 AI Quality
- **Context Independence**: Each file stands alone with descriptive naming and a single purpose.
- **AI Insight Documentation**: Clear, concise comments referencing these guidelines where relevant.
- **Implementation Consistency**: Maintain >90% adherence to the header-implementation-footer pattern. Use `luacheck` or similar for automated checks.
- **Architecture Visibility**: Organize modules in distinct directories and list dependencies in each header.
- **Test Coverage**: Aim for 90%+ coverage using `busted`.
- **Style Conformance**: Follow well-known Lua patterns and style rules.

### 5.2 File Organization
- **File Purpose**: Header clarifies the single responsibility and needed modules.
- **File Size**: ~200–300 lines (excluding comments).
- **Module Interface**: Return a table documenting public functions via comments.

### 5.3 Code
- **Semantic Naming**: Use descriptive identifiers (long is fine if clearer).
- **Function Size**: Keep it under ~30 lines for readability.
- **Function Signature**: Max of 4 parameters; pass a table if more are needed.
- **Cyclomatic Complexity**: Keep it <8.
- **Code Duplication**: Stay below 2%. Factor out repeated logic.

### 5.4 Error Handling
- **Traceability**: Errors should describe the function, parameters, and mismatch between expected and actual behavior.
- **Logging**: Adopt a consistent format (timestamp, severity, message, context).
- **Exception Management**: If using `pcall` or custom errors, be explicit.
- **No Fallbacks**: Fail clearly for internal code. Only externally-sourced errors (e.g., network calls) may warrant fallback logic.

### 5.5 Dependencies
- **Vetting**: Favor stable LuaRocks packages and well-reviewed libraries.
- **Discernment**: When selecting dependencies, justify them briefly.

---

## 6. AUTOMATION

- **`stylua`**: Automate formatting to keep indentation and style uniform.
- **`luacheck`**: Lint for syntactic errors and style issues.
- **`busted`**: Provide unit/integration tests for modules.
- **Luadoc Generation**: Optional but recommended; extract function docs from your `---` comments.
- **Pre-Commit Hooks**: Use Git hooks to run `stylua`, `luacheck`, and `busted` before pushing code.

### 6.1 Example Project Layout
```md
project_head/
├── Makefile
├── src/
│   └── utils.lua
└── tests/
    └── test_utils.lua
```

### 6.2 Makefile Example
```makefile
test:
	busted

lint:
	luacheck src

doc:
	luadoc -d doc src

all: lint test doc
```

Run `make all` before committing to confirm the code meets Zeroth Law requirements.
