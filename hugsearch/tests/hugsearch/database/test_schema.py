"""
# PURPOSE: Test database schema management
## INTERFACES: None (test module)
"""

import pytest
import pytest_asyncio
import aiosqlite

from hugsearch.database.schema import init_db, migrate_schema, SCHEMA_VERSION


@pytest_asyncio.fixture(scope="function")
async def test_db(tmp_path):
    """Create empty test database"""
    db_path = tmp_path / "test_models.db"
    yield db_path


@pytest.mark.asyncio
async def test_schema_initialization(test_db):
    """Test database schema initialization"""
    await init_db(test_db)

    async with aiosqlite.connect(test_db) as db:
        # Check schema version
        cursor = await db.execute("SELECT version FROM schema_version")
        row = await cursor.fetchone()
        assert row[0] == SCHEMA_VERSION

        # Check tables exist
        cursor = await db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' OR type='view'
        """)
        tables = {row[0] for row in await cursor.fetchall()}

        required_tables = {
            "schema_version",
            "models",
            "model_tags",
            "model_descriptions",
            "followed_creators",
        }
        assert required_tables.issubset(tables)

        # Check indexes exist
        cursor = await db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
        """)
        indexes = {row[0] for row in await cursor.fetchall()}

        required_indexes = {
            "idx_models_name",
            "idx_models_name_lower",
            "idx_model_tags",
        }
        assert required_indexes.issubset(indexes)


@pytest.mark.asyncio
async def test_schema_migration(test_db):
    """Test schema migration handling"""
    # Create database with old version
    async with aiosqlite.connect(test_db) as db:
        await db.execute("""
            CREATE TABLE schema_version (version INTEGER PRIMARY KEY)
        """)
        await db.execute("INSERT INTO schema_version VALUES (?)", (0,))
        await db.commit()

    # Run migration
    await migrate_schema(test_db)

    # Check version was updated
    async with aiosqlite.connect(test_db) as db:
        cursor = await db.execute("SELECT version FROM schema_version")
        row = await cursor.fetchone()
        assert row[0] == SCHEMA_VERSION
