# Rust Project Layout: rust-2025-Trahloc Microcrate Convention (r2025t)

## 0. Scope

The rust-2025-Trahloc Microcrate Convention (r2025t) defines a strict directory and naming standard for Rust workspaces. It is designed specifically to:

1. **Eliminate File Ambiguity**: Prevent AI context hallucinations caused by multiple files named `lib.rs`, `main.rs`, or `mod.rs`.
2. **Optimize Compilation**: Enforce boundaries that keep incremental builds under 2 seconds.
3. **Structure for AI Agents**: Provide a deterministic map where file location equals logical responsibility.
4. **Minimize Path Noise**: Flatten microcrate structure by eliminating unnecessary `src/` directories.

This is a **layout and naming spec only**. It does not change Rust semantics, editions, or compiler behavior. It layers on top of Rust 2018 and 2021 editions.

---

## 1. Core Principles

1. **Uniqueness by Top-Level Directory (TLD)**
   For every logical component X, there is exactly one directory X/ containing exactly one crate whose root source file is X.rs.

2. **Banned Filenames**
   - `mod.rs` is **strictly forbidden**. Use the Rust 2018 `foo.rs` + `foo/` pattern instead.
   - `lib.rs` and `main.rs` are **forbidden as logic containers**. They exist only as optional tooling redirects containing zero logic.

3. **Flattened Microcrates**
   Microcrates omit the `src/` directory. The `Cargo.toml` lives alongside the root X.rs file. The `src/` directory is reserved for the workspace binary crate only.

4. **One Binary Front Door**
   There is exactly one primary binary crate responsible for the main executable name. All other crates are libraries.

5. **Explicit Root Directory**
   The project root directory is prefixed with an underscore (e.g., `_dotsetup/`). This distinguishes the workspace container from the logical crates inside it.

6. **Backwards Compatibility over Ideological Purity**
   When tooling requires `lib.rs` or `main.rs`, those files exist as redirects. The convention adapts to the ecosystem, not the reverse.

---

## 2. Workspace Structure

At the highest level, a r2025t workspace looks like:

    _dotsetup/
    ├── Cargo.toml               # workspace root
    ├── bin/                     # binary front door (uses src/)
    ├── command/                 # command microcrates (flattened)
    ├── lib/                     # shared library microcrates (flattened)
    ├── tests/                   # integration test crate (flattened)
    └── docs/                    # documentation, specs

### 2.1 Workspace Cargo.toml

    [workspace]
    members = [
        "bin",
        "command/*",
        "lib/*",
        "tests",
    ]
    resolver = "2"

    [profile.dev]
    opt-level = 0
    debug = true
    incremental = true

    [profile.dev.package."*"]
    opt-level = 2  # optimize dependencies, keep your code fast to compile

---

## 3. Crate Naming and Directory Rules

### 3.1 Crate Directory Name and Package Name

For each crate:

- The directory name is the TLD.
- The package name in Cargo.toml follows: `<project>-<kind>-<tld>`

Where:

- `<project>` is the base project name (e.g., `dotsetup`)
- `<kind>` is one of: `bin`, `command`, `lib`, `tests`
- `<tld>` is the crate directory name (e.g., `install`, `common`)

Examples:

- `bin/` → `dotsetup-bin`
- `command/install/` → `dotsetup-command-install`
- `lib/common/` → `dotsetup-lib-common`
- `tests/` → `dotsetup-tests`

### 3.2 Root Source File Rule

For any crate with directory name X/:

- The crate root source file **must** be named X.rs
- The crate Cargo.toml **must** explicitly declare the path

### 3.3 Flattened Layout (Microcrates)

Microcrates do not use a `src/` directory. All source files live directly in the crate directory.

    command/install/
    ├── Cargo.toml
    ├── install.rs           # crate root
    ├── config.rs            # module
    └── steps.rs             # module

Cargo.toml for flattened layout:

    [package]
    name = "dotsetup-command-install"
    version = "0.1.0"
    edition = "2021"

    [lib]
    name = "dotsetup_command_install"
    path = "install.rs"

    [dependencies]
    dotsetup-lib-common = { path = "../../lib/common" }

### 3.4 Standard Layout (Binary Crate Only)

The binary front door uses `src/` because it is the public entry point and may have additional structure:

    bin/
    ├── Cargo.toml
    └── src/
        ├── dotsetup.rs      # orchestrator
        └── main.rs          # redirect

### 3.5 Naming Restrictions

- Never name a microcrate `core`. It shadows `std::core` and causes confusion. Use `common` or `shared`.
- Never use `mod.rs`. Use the Rust 2018 pattern: `foo.rs` as module root, `foo/` as submodule directory.

---

## 4. Tooling Compatibility Redirects

When external tools require `lib.rs` or `main.rs`, create thin redirects containing no logic.

### 4.1 Library Redirect

    // lib.rs - tooling compatibility redirect
    // All logic lives in install.rs
    mod install;
    pub use install::*;

Note: This declares `install` as a module and re-exports its contents. The Cargo.toml still points to `install.rs` as the true root; this file exists only for tools that ignore Cargo.toml paths.

### 4.2 Binary Redirect

    // main.rs - tooling compatibility redirect
    // All logic lives in dotsetup.rs
    mod dotsetup;

    fn main() {
        dotsetup::run();
    }

### 4.3 Redirect Rules

- Redirects contain at most 5 lines of code.
- Redirects contain no business logic, no error handling, no imports beyond the orchestrator.
- Redirects are marked with a comment explaining their purpose.
- If your tooling works without these, delete them. Less noise is better.

---

## 5. Command Microcrate Layout

Commands represent CLI verbs (install, fix, status). All command crates live under `command/`.

### 5.1 Directory Layout

    _dotsetup/command/install/
        Cargo.toml
        install.rs               # crate root, orchestrator
        install_config.rs        # module: configuration handling
        install_steps.rs         # module: step execution
        lib.rs                   # optional redirect

### 5.2 Cargo.toml Example

    [package]
    name = "dotsetup-command-install"
    version = "0.1.0"
    edition = "2021"

    [lib]
    name = "dotsetup_command_install"
    path = "install.rs"

    [dependencies]
    dotsetup-lib-common = { path = "../../lib/common" }

### 5.3 Module Declaration

In install.rs:

    // install.rs - orchestrator for the install command

    mod install_config;
    mod install_steps;

    pub use install_config::Config;
    pub use install_steps::execute;

    pub fn run(config: Config) -> Result<(), Error> {
        // orchestration logic
    }

---

## 6. Library Microcrate Layout

Shared logic lives under `lib/`. Code moves here the moment it is needed by more than one command.

### 6.1 Directory Layout

    _dotsetup/lib/common/
        Cargo.toml
        common.rs                # crate root
        fs_utils.rs              # module
        xdg.rs                   # module
        symlink.rs               # module

### 6.2 Cargo.toml Example

    [package]
    name = "dotsetup-lib-common"
    version = "0.1.0"
    edition = "2021"

    [lib]
    name = "dotsetup_lib_common"
    path = "common.rs"

---

## 7. Binary Crate Layout

The workspace has exactly one primary binary crate under `bin/`.

### 7.1 Directory Layout

    _dotsetup/bin/
        Cargo.toml
        src/
            dotsetup.rs          # orchestrator, CLI dispatch
            main.rs              # redirect

### 7.2 Cargo.toml Example

    [package]
    name = "dotsetup-bin"
    version = "0.1.0"
    edition = "2021"

    [[bin]]
    name = "dotsetup"
    path = "src/dotsetup.rs"

    [features]
    default = ["install", "fix", "status"]
    install = ["dotsetup-command-install"]
    fix = ["dotsetup-command-fix"]
    status = ["dotsetup-command-status"]
    full = ["install", "fix", "status"]

    [dependencies]
    dotsetup-command-install = { path = "../command/install", optional = true }
    dotsetup-command-fix = { path = "../command/fix", optional = true }
    dotsetup-command-status = { path = "../command/status", optional = true }
    dotsetup-lib-common = { path = "../lib/common" }

### 7.3 Orchestrator Structure

In src/dotsetup.rs:

    // dotsetup.rs - CLI orchestrator

    use clap::Parser;

    #[derive(Parser)]
    enum Command {
        Install(dotsetup_command_install::Args),
        Fix(dotsetup_command_fix::Args),
        Status(dotsetup_command_status::Args),
    }

    pub fn run() {
        let cmd = Command::parse();
        match cmd {
            Command::Install(args) => dotsetup_command_install::run(args),
            Command::Fix(args) => dotsetup_command_fix::run(args),
            Command::Status(args) => dotsetup_command_status::run(args),
        }
    }

---

## 8. Testing Strategy

Testing is stratified to optimize compilation speed and AI comprehension.

### 8.1 Unit Tests (In-File)

Tests that verify internal logic live inside the source file they test.

    // install.rs

    pub fn validate_path(path: &Path) -> bool {
        path.exists() && path.is_dir()
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn test_validate_path_exists() {
            // test implementation
        }
    }

Benefits:

- AI sees code and tests together in one context window.
- Tests compile only when that specific crate is tested.
- Private functions are testable without `pub(crate)` gymnastics.

### 8.2 Integration Tests (Test Crate)

Integration tests live in a dedicated workspace member `tests/`. This is a **crate**, not a standard Cargo test folder.

Why: Cargo's default `tests/` folder compiles each `*.rs` file as a separate binary. This destroys compile times. A single test crate compiles once.

### 8.3 Test Crate Layout

    _dotsetup/tests/
        Cargo.toml
        integration.rs           # crate root
        install_flow.rs          # test module
        fix_flow.rs              # test module

### 8.4 Test Crate Cargo.toml

    [package]
    name = "dotsetup-tests"
    version = "0.1.0"
    edition = "2021"
    publish = false

    [lib]
    name = "dotsetup_tests"
    path = "integration.rs"

    [[test]]
    name = "integration"
    path = "integration.rs"

    [dependencies]
    dotsetup-bin = { path = "../bin" }
    dotsetup-command-install = { path = "../command/install" }
    dotsetup-command-fix = { path = "../command/fix" }
    dotsetup-lib-common = { path = "../lib/common" }

### 8.5 Test Crate Root

    // integration.rs

    mod install_flow;
    mod fix_flow;

### 8.6 Running Tests

    cargo test -p dotsetup-command-install    # unit tests for one crate
    cargo test -p dotsetup-tests              # all integration tests
    cargo test --workspace                    # everything

---

## 9. When to Split: The Microcrate Threshold

Split a module into its own microcrate when **any** of the following are true:

1. **Type Proliferation**: The module has 3+ non-trivial public types or traits with their own impl blocks.

2. **Dependency Isolation**: The module pulls in a dependency that nothing else in the parent crate needs.

3. **Test Divergence**: The module's tests require materially different fixtures or setup than its siblings.

4. **Independent Versioning**: You want to version or feature-gate the module independently.

5. **Collaboration Boundary**: Two developers (or AI agents) would reasonably work on it simultaneously without touching the same files.

**Do not split** merely because a file exceeds a line count. Split when the boundary becomes load-bearing for compilation, testing, or comprehension.

The goal: change one file in one microcrate → rebuild only that crate → run tests in under 2 seconds.

---

## 10. Nested Microcrates

r2025t allows microcrates inside microcrates when they are implementation details of the parent.

### 10.1 Nested Layout

    _dotsetup/command/install/
        Cargo.toml                   # dotsetup-command-install
        install.rs
        migration/                   # nested microcrate
            Cargo.toml               # dotsetup-command-install-migration
            migration.rs

### 10.2 Nested Cargo.toml

    [package]
    name = "dotsetup-command-install-migration"
    version = "0.1.0"
    edition = "2021"

    [lib]
    name = "dotsetup_command_install_migration"
    path = "migration.rs"

### 10.3 Constraints

- Each nested crate has its own Cargo.toml.
- Each nested crate follows the TLD X/X.rs rule (flattened).
- Dependencies are explicit and acyclic at the crate level.

### 10.4 Promotion Rule

Promote a nested microcrate when any of these occur:

- **Cross-reference**: It is needed by sibling crates, not just its parent.
- **Independent identity**: It grows versioning or feature needs distinct from its parent.
- **Conceptual graduation**: It is no longer an implementation detail.

Promotion means:

1. Move the crate to `lib/` (e.g., `lib/migration/`).
2. Rename the package (e.g., `dotsetup-lib-migration`).
3. Extract shared code to `lib/common/` if needed.
4. Update all dependents.

---

## 11. Feature Flag Strategy

### 11.1 Crate-Local Features

Each microcrate owns features for its optional dependencies or conditional compilation.

    # lib/common/Cargo.toml

    [features]
    default = []
    logging = ["tracing"]

    [dependencies]
    tracing = { version = "0.1", optional = true }

### 11.2 Workspace-Level Aggregation

The binary crate aggregates features from dependencies and exposes them to end users.

    # bin/Cargo.toml

    [features]
    default = ["install", "fix"]
    install = ["dotsetup-command-install"]
    fix = ["dotsetup-command-fix"]
    status = ["dotsetup-command-status"]
    full = ["install", "fix", "status"]
    verbose-logging = ["dotsetup-lib-common/logging"]

    [dependencies]
    dotsetup-command-install = { path = "../command/install", optional = true }
    dotsetup-command-fix = { path = "../command/fix", optional = true }
    dotsetup-command-status = { path = "../command/status", optional = true }
    dotsetup-lib-common = { path = "../lib/common" }

### 11.3 Feature Naming Convention

- Command features: Use the command name (`install`, `fix`).
- Capability features: Use descriptive names (`verbose-logging`, `network-retry`).
- Propagated features: Use `crate-name/feature-name` syntax for clarity.

### 11.4 Feature Coordination

The `common` crate does not coordinate features. It is a leaf. The binary is the root that decides what is included. Features flow downward from binary to libraries, never upward.

---

## 12. Iterative Development Tooling

The goal is **fastest in human time**, not fastest in CPU time.

### 12.1 Required Tools

**cargo-watch**: Auto-rebuild on file changes.

    cargo install cargo-watch
    cargo watch -x check                              # continuous type checking
    cargo watch -x "test -p dotsetup-command-install" # test one crate
    cargo watch -x "clippy -- -W warnings"            # continuous linting

**sccache**: Shared compilation cache for faster cold builds.

    cargo install sccache
    export RUSTC_WRAPPER=sccache

Add to shell profile for persistence.

**mold** (Linux): Faster linker.

    # Install mold via package manager, then add to .cargo/config.toml:

    [target.x86_64-unknown-linux-gnu]
    linker = "clang"
    rustflags = ["-C", "link-arg=-fuse-ld=mold"]

### 12.2 IDE Configuration

For rust-analyzer (VS Code, Cursor, etc.):

    {
        "rust-analyzer.checkOnSave.command": "clippy",
        "rust-analyzer.cargo.buildScripts.enable": true,
        "rust-analyzer.procMacro.enable": true
    }

### 12.3 Development Workflow

Typical iteration loop:

1. Run `cargo watch -x check` in a terminal.
2. Edit code. Errors appear within seconds.
3. Run `cargo test -p dotsetup-command-install` to test one crate.
4. Run `cargo run -- install` to test the full binary.

Microcrate boundaries are compilation unit boundaries. The flattened layout plus small crates means incremental rebuilds are near-instant.

---

## 13. The Uniqueness Invariant

The defining invariant of r2025t:

> For every crate directory X/ under the workspace, there exists exactly one crate whose root module is X.rs (flattened) or src/X.rs (binary only). Files named lib.rs, main.rs, or mod.rs exist only as tooling-compatibility redirects containing no logic. mod.rs is strictly forbidden in all contexts.

---

## 14. Directory Tree Reference (Complete)

    _dotsetup/
    ├── Cargo.toml                          # workspace root
    ├── docs/
    │   └── r2025t-spec.md
    ├── bin/
    │   ├── Cargo.toml                      # dotsetup-bin
    │   └── src/
    │       ├── dotsetup.rs                 # orchestrator
    │       └── main.rs                     # redirect
    ├── command/
    │   ├── install/
    │   │   ├── Cargo.toml                  # dotsetup-command-install
    │   │   ├── install.rs                  # root
    │   │   ├── install_config.rs           # module
    │   │   ├── install_steps.rs            # module
    │   │   ├── lib.rs                      # optional redirect
    │   │   └── migration/                  # nested microcrate
    │   │       ├── Cargo.toml              # dotsetup-command-install-migration
    │   │       └── migration.rs            # root
    │   ├── fix/
    │   │   ├── Cargo.toml                  # dotsetup-command-fix
    │   │   ├── fix.rs                      # root
    │   │   └── lib.rs                      # optional redirect
    │   └── status/
    │       ├── Cargo.toml                  # dotsetup-command-status
    │       ├── status.rs                   # root
    │       └── lib.rs                      # optional redirect
    ├── lib/
    │   └── common/
    │       ├── Cargo.toml                  # dotsetup-lib-common
    │       ├── common.rs                   # root
    │       ├── fs_utils.rs                 # module
    │       ├── xdg.rs                      # module
    │       ├── symlink.rs                  # module
    │       └── lib.rs                      # optional redirect
    └── tests/
        ├── Cargo.toml                      # dotsetup-tests
        ├── integration.rs                  # root
        ├── install_flow.rs                 # test module
        └── fix_flow.rs                     # test module

---

## 15. Summary

**rust-2025-Trahloc (r2025t)**:

1. **Unique Names**: Every crate root is X.rs. No ambiguous lib.rs or mod.rs.
2. **Flattened Microcrates**: No `src/` folders except in the binary crate.
3. **Dedicated Test Crate**: `tests/` is a package, not a folder of separate binaries.
4. **AI Optimization**: Zero file path ambiguity. One name, one responsibility, one location.
5. **Compilation Speed**: Microcrate boundaries enable sub-2-second incremental rebuilds.
6. **Backwards Compatible**: Redirect files satisfy legacy tooling without polluting architecture.

This layout trades adherence to Cargo defaults for precision, compilation speed, and AI-assistant compatibility.