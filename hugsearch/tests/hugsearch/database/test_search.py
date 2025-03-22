"""
# PURPOSE: Test search functionality
## INTERFACES: None (test module)
"""
import pytest
import pytest_asyncio
from pathlib import Path

from hugsearch.database import search_models
from hugsearch.database.models import upsert_model
from hugsearch.database.schema import init_db

@pytest_asyncio.fixture
async def test_db(tmp_path):
    """Create test database with sample data"""
    db_path = tmp_path / "test_models.db"
    await init_db(db_path)

    # Add test models
    models = [
        {
            "id": "model1",
            "name": "LLAMA 7B",
            "author": "meta",
            "description": "A foundational 7B parameter model",
            "tags": ["llm", "base-model"],
            "downloads": 1000,
            "likes": 500,
            "lastModified": "2024-01-01"
        },
        {
            "id": "model2",
            "name": "Mistral-7B",
            "author": "mistralai",
            "description": "Efficient 7B parameter model",
            "tags": ["llm", "efficient"],
            "downloads": 800,
            "likes": 400,
            "lastModified": "2024-02-01"
        },
        {
            "id": "model3",
            "name": "CodeLlama-34b",
            "author": "meta",
            "description": "Code specialized 34B parameter model",
            "tags": ["llm", "code", "large"],
            "downloads": 1500,
            "likes": 600,
            "lastModified": "2024-03-01"
        }
    ]

    for model in models:
        await upsert_model(db_path, model)

    return db_path

@pytest.mark.asyncio
async def test_basic_search(test_db):
    """Test basic search functionality"""
    # Simple keyword search
    results = await search_models(test_db, "llama")
    assert len(results) == 2
    assert any(r["name"] == "LLAMA 7B" for r in results)
    assert any(r["name"] == "CodeLlama-34b" for r in results)

@pytest.mark.asyncio
async def test_case_sensitive_search(test_db):
    """Test case sensitive search"""
    # Case insensitive (default)
    results = await search_models(test_db, "llama")
    assert len(results) == 2

    # Case sensitive
    results = await search_models(test_db, "LLAMA", case_sensitive=True)
    assert len(results) == 1
    assert results[0]["name"] == "LLAMA 7B"

@pytest.mark.asyncio
async def test_exact_match_search(test_db):
    """Test exact match search"""
    # Fuzzy match (default)
    results = await search_models(test_db, "llam")
    assert len(results) == 2

    # Exact match
    results = await search_models(test_db, "llam", exact_match=True)
    assert len(results) == 0

    results = await search_models(test_db, "LLAMA", exact_match=True)
    assert len(results) == 1
    assert results[0]["name"] == "LLAMA 7B"

@pytest.mark.asyncio
async def test_tag_filter(test_db):
    """Test tag filtering"""
    # Search with tag filter
    results = await search_models(test_db, "llama", filters={"tags": "code"})
    assert len(results) == 1
    assert results[0]["name"] == "CodeLlama-34b"

@pytest.mark.asyncio
async def test_boolean_operators(test_db):
    """Test AND/OR operators"""
    # Test OR
    results = await search_models(test_db, "llama OR mistral")
    assert len(results) == 3

    # Test AND
    results = await search_models(test_db, "llama AND 7B")
    assert len(results) == 1
    assert results[0]["name"] == "LLAMA 7B"
