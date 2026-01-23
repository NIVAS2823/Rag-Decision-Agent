"""
Database Services
=================
Database connection and client initialization.
"""

from app.services.database.mongodb import mongodb_manager
from app.services.database.client import db_client


async def initialize_database() -> None:
    """
    Initialize database connection and collections
    
    This function should be called during application startup.
    """
    # Connect to MongoDB
    await mongodb_manager.connect()
    
    # Initialize collections and indexes
    await db_client.initialize()


async def close_database() -> None:
    """
    Close database connection
    
    This function should be called during application shutdown.
    """
    await mongodb_manager.disconnect()


__all__ = [
    "mongodb_manager",
    "db_client",
    "initialize_database",
    "close_database",
]