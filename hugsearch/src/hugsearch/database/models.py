"""
# PURPOSE: Handle model data operations (CRUD)
## INTERFACES:
- upsert_model(): Insert or update a model
- get_model(): Retrieve a single model
- delete_model(): Remove a model
## DEPENDENCIES:
- aiosqlite: Async SQLite operations
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

import aiosqlite


async def upsert_model(db_path: Union[str, Path], model_data: Dict) -> None:
    """Insert or update a model record"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("BEGIN TRANSACTION") as cursor:
            # Extract core fields
            model_id = model_data["id"]
            name = model_data["name"]
            name_lower = name.lower()
            author = model_data["author"]
            author_lower = author.lower()  # Add author_lower
            last_modified = model_data.get("lastModified", datetime.now().isoformat())
            description = model_data.get("description", "")

            # Store core model data
            await cursor.execute(
                """
                INSERT OR REPLACE INTO models
                (id, name, name_lower, author, author_lower, last_modified, metadata, last_checked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    model_id,
                    name,
                    name_lower,
                    author,
                    author_lower,
                    last_modified,
                    json.dumps(model_data),
                    datetime.now().isoformat(),
                ),
            )

            # Store description for text search
            await cursor.execute(
                """
                INSERT OR REPLACE INTO model_descriptions (model_id, description)
                VALUES (?, ?)
            """,
                (model_id, description),
            )

            # Update tags
            await cursor.execute(
                "DELETE FROM model_tags WHERE model_id = ?", (model_id,)
            )
            if "tags" in model_data and model_data["tags"]:
                await cursor.executemany(
                    "INSERT INTO model_tags (model_id, tag, tag_lower) VALUES (?, ?, ?)",
                    [(model_id, tag, tag.lower()) for tag in model_data["tags"]],
                )

        await db.commit()


async def get_model(db_path: Union[str, Path], model_id: str) -> Optional[Dict]:
    """Retrieve a single model by ID"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Get model core data
        cursor = await db.execute("SELECT * FROM models WHERE id = ?", (model_id,))
        model = await cursor.fetchone()
        if not model:
            return None

        # Convert to dict and return
        return dict(model)


async def delete_model(db_path: Union[str, Path], model_id: str) -> bool:
    """Delete a model by ID"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("BEGIN TRANSACTION") as cursor:
            # Check if model exists first
            cursor = await db.execute("SELECT 1 FROM models WHERE id = ?", (model_id,))
            if not await cursor.fetchone():
                return False

            # Delete model - cascading will handle related records
            await cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))

        await db.commit()
        return True
