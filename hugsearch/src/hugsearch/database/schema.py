"""
# PURPOSE: Database schema management and initialization
## INTERFACES:
- init_db(): Initialize database schema
- migrate_schema(): Handle schema migrations
## DEPENDENCIES:
- aiosqlite: Async SQLite operations
"""
import aiosqlite
from pathlib import Path
from typing import Union

SCHEMA_VERSION = 2

async def init_db(db_path: Union[str, Path]) -> None:
    """Initialize database schema"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # Version tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        # Core models table with normalized columns
        await db.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_lower TEXT NOT NULL,
                author TEXT NOT NULL,
                author_lower TEXT NOT NULL,
                last_modified TEXT NOT NULL,
                metadata TEXT NOT NULL,
                last_checked TEXT NOT NULL
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_models_name ON models(name)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_models_name_lower ON models(name_lower)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_models_author ON models(author)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_models_author_lower ON models(author_lower)")

        # Tags table for clean tag management
        await db.execute("""
            CREATE TABLE IF NOT EXISTS model_tags (
                model_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                tag_lower TEXT NOT NULL,
                PRIMARY KEY (model_id, tag),
                FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_model_tags ON model_tags(tag_lower)")

        # Description search using FTS5
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS model_descriptions USING fts5(
                model_id UNINDEXED,
                description
            )
        """)

        # Creator following
        await db.execute("""
            CREATE TABLE IF NOT EXISTS followed_creators (
                author TEXT PRIMARY KEY,
                last_checked TEXT NOT NULL
            )
        """)

        # Set initial schema version
        await db.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                        (SCHEMA_VERSION,))
        await db.commit()

async def migrate_schema(db_path: Union[str, Path]) -> None:
    """Handle any necessary schema migrations"""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT version FROM schema_version")
        row = await cursor.fetchone()
        current_version = row[0] if row else 0

        if current_version < 1:
            # Create initial tables if they don't exist
            await db.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_lower TEXT NOT NULL,
                    author TEXT NOT NULL,
                    last_modified TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    last_checked TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_models_name ON models(name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_models_name_lower ON models(name_lower)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_models_author ON models(author)")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS model_tags (
                    model_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    tag_lower TEXT NOT NULL,
                    PRIMARY KEY (model_id, tag),
                    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_model_tags ON model_tags(tag_lower)")

            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS model_descriptions USING fts5(
                    model_id UNINDEXED,
                    description
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS followed_creators (
                    author TEXT PRIMARY KEY,
                    last_checked TEXT NOT NULL
                )
            """)

        if current_version < 2:
            await db.execute("ALTER TABLE models ADD COLUMN author_lower TEXT")
            await db.execute("UPDATE models SET author_lower = lower(author)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_models_author_lower ON models(author_lower)")

        if current_version < SCHEMA_VERSION:
            await db.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
            await db.commit()