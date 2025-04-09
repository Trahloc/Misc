"""
# PURPOSE: Test model CRUD operations
## INTERFACES: None (test module)
"""

import json
import pytest
import pytest_asyncio

from hugsearch.database.models import upsert_model, get_model, delete_model
from hugsearch.database.schema import init_db


@pytest_asyncio.fixture
async def test_db(tmp_path):
    """Create test database with sample data"""
    db_path = tmp_path / "test_models.db"
    await init_db(db_path)
    return db_path


@pytest.mark.asyncio
async def test_model_crud(test_db):
    """Test basic CRUD operations for models"""
    # Test create
    model_data = {
        "id": "test-model",
        "name": "Test Model",
        "author": "test-author",
        "description": "A test model",
        "tags": ["test", "fixture"],
        "lastModified": "2024-01-01",
    }
    await upsert_model(test_db, model_data)

    # Test read
    saved_model = await get_model(test_db, "test-model")
    assert saved_model is not None
    assert saved_model["name"] == "Test Model"
    assert saved_model["author"] == "test-author"
    assert json.loads(saved_model["metadata"]) == model_data

    # Test update
    updated_data = dict(model_data)
    updated_data["name"] = "Updated Model"
    updated_data["tags"] = ["test", "updated"]
    await upsert_model(test_db, updated_data)

    updated_model = await get_model(test_db, "test-model")
    assert updated_model["name"] == "Updated Model"
    assert json.loads(updated_model["metadata"])["tags"] == ["test", "updated"]

    # Test delete
    assert await delete_model(test_db, "test-model")
    deleted_model = await get_model(test_db, "test-model")
    assert deleted_model is None


@pytest.mark.asyncio
async def test_model_metadata(test_db):
    """Test handling of model metadata"""
    model_data = {
        "id": "metadata-test",
        "name": "Metadata Test",
        "author": "test-author",
        "description": "Testing metadata handling",
        "tags": ["test"],
        "downloads": 1000,
        "likes": 500,
        "extra_field": "custom value",
        "lastModified": "2024-01-01",
    }
    await upsert_model(test_db, model_data)

    saved_model = await get_model(test_db, "metadata-test")
    metadata = json.loads(saved_model["metadata"])

    # Check all fields are preserved
    assert metadata["downloads"] == 1000
    assert metadata["likes"] == 500
    assert metadata["extra_field"] == "custom value"

    # Check core fields are properly stored
    assert saved_model["name"] == model_data["name"]
    assert saved_model["author"] == model_data["author"]
