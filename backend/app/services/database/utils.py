"""
Database Utilities
==================
Helper functions for database operations.
"""

from typing import Dict, Any

from app.services.database import db_client
from app.core.logging_config import get_logger


logger = get_logger(__name__)


async def cleanup_test_data() -> Dict[str, int]:
    """
    Clean up test data from database
    
    Returns:
        Dict[str, int]: Number of documents deleted per collection
    """
    result = {}
    
    # Delete test users
    users_deleted = await db_client.get_users_collection().delete_many(
        {"email": {"$regex": "^(test|integration).*@example.com$"}}
    )
    result["users"] = users_deleted.deleted_count
    
    # Delete orphaned decisions (where user doesn't exist)
    # This would be more complex in production with proper cleanup
    result["decisions"] = 0
    
    logger.info(f"Cleanup completed: {result}")
    return result


async def reset_database() -> bool:
    """
    Reset database (drop all collections)
    
    WARNING: This deletes ALL data. Only for development/testing.
    
    Returns:
        bool: True if successful
    """
    from app.core.config import settings
    
    if settings.is_production:
        raise RuntimeError("Cannot reset database in production!")
    
    # Drop all collections
    collections = await db_client.list_collections()
    
    for collection_name in collections:
        await db_client.get_database().drop_collection(collection_name)
    
    logger.warning(f"Database reset: dropped {len(collections)} collections")
    
    # Reinitialize
    await db_client.initialize()
    
    return True