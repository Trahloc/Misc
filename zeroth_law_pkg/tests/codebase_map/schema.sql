-- SQLite schema for the ZLF Codebase Map
-- Version: 1 (YYYY-MM-DDTHH:MM:SS+ZZ:ZZ - AI: Run `date --iso-8601=seconds`)

PRAGMA foreign_keys = ON;

-- Table to track scanned Python modules (.py files)
CREATE TABLE modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Relative path from src/ root, e.g., 'zeroth_law/cli.py'
    path TEXT UNIQUE NOT NULL,
    -- UNIX timestamp of the last successful scan that included this module
    last_scanned_timestamp REAL NOT NULL
);

-- Table to track classes found within modules
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    -- Placeholder for a hash representing the method signatures, TBD
    signature_hash TEXT,
    start_line INTEGER,
    end_line INTEGER,
    FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
    -- Class names must be unique within a module
    UNIQUE(module_id, name)
);

-- Table to track functions/methods found within modules or classes
CREATE TABLE functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    -- NULL if function is module-level, otherwise points to the containing class
    class_id INTEGER,
    name TEXT NOT NULL,
    -- Placeholder for a hash representing the function signature, TBD
    signature_hash TEXT,
    start_line INTEGER,
    end_line INTEGER,
    FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
    FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
    -- Function/method names must be unique within their scope (module or class)
    UNIQUE(module_id, class_id, name)
);

-- Table to track import statements within modules
CREATE TABLE imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- The module performing the import
    importing_module_id INTEGER NOT NULL,
    -- The full name of what is being imported (e.g., 'os', 'pathlib.Path', '.utils')
    imported_name TEXT NOT NULL,
    -- The alias used, if any (e.g., 'pd' for 'pandas')
    alias TEXT,
    -- The line number where the import occurs
    line_number INTEGER NOT NULL,
    FOREIGN KEY(importing_module_id) REFERENCES modules(id) ON DELETE CASCADE
    -- Note: No uniqueness constraint here, as the same import might occur multiple times
);

-- Indexes for faster lookups
CREATE INDEX idx_modules_path ON modules(path);
CREATE INDEX idx_classes_module_id ON classes(module_id);
CREATE INDEX idx_functions_module_id ON functions(module_id);
CREATE INDEX idx_functions_class_id ON functions(class_id);
CREATE INDEX idx_imports_module_id ON imports(importing_module_id);