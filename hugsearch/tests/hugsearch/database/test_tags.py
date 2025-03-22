"""
# PURPOSE: Test tag operations
## INTERFACES: None (test module)
"""
import pytest
import pytest_asyncio
from pathlib import Path

from hugsearch.database.models import upsert_model
from hugsearch.database.schema import init_db
from hugsearch.database.tags import get_model_tags, get_all_tags, search_by_tag

@pytest_asyncio.fixture
async def test_db(tmp_path):
    """Create test database with sample data"""
    db_path = tmp_path / "test_models.db"
    await init_db(db_path)

    # Add test models with various tags
    models = [
        {
            "id": "model1",
            "name": "LLAMA 7B",
            "author": "meta",
            "description": "A foundational 7B parameter model",
            "tags": ["llm", "base-model"],
            "lastModified": "2024-01-01"
        },
        {
            "id": "model2",
            "name": "Mistral-7B",
            "author": "mistralai",
            "description": "Efficient 7B parameter model",
            "tags": ["llm", "efficient"],
            "lastModified": "2024-02-01"
        },
        {
            "id": "model3",
            "name": "CodeLlama-34b",
            "author": "meta",
            "description": "Code specialized 34B parameter model",
            "tags": ["llm", "code", "large"],
            "lastModified": "2024-03-01"
        }
    ]

    for model in models:
        await upsert_model(db_path, model)

    return db_path

@pytest.mark.asyncio
async def test_get_model_tags(test_db):
    """Test retrieving tags for a specific model"""
    tags = await get_model_tags(test_db, "model3")
    assert len(tags) == 3
    assert set(tags) == {"llm", "code", "large"}

@pytest.mark.asyncio
async def test_get_all_tags(test_db):
    """Test retrieving all unique tags"""
    # Get tags without counts
    tags = await get_all_tags(test_db)
    assert len(tags) == 5
    assert set(tags) == {"llm", "base-model", "efficient", "code", "large"}

    # Get tags with counts
    tags = await get_all_tags(test_db, include_counts=True)
    assert len(tags) == 5
    llm_tag = next(t for t in tags if t["tag"] == "llm")
    assert llm_tag["count"] == 3

@pytest.mark.asyncio
async def test_search_by_tag(test_db):
    """Test searching models by tag"""
    # Case insensitive search
    results = await search_by_tag(test_db, "code")
    assert len(results) == 1
    assert results[0]["name"] == "CodeLlama-34b"

    # Common tag search
    results = await search_by_tag(test_db, "llm")
    assert len(results) == 3

    # Case sensitive search
    results = await search_by_tag(test_db, "LLM", case_sensitive=True)
    assert len(results) == 0
