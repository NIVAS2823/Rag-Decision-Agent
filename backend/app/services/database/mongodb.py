"""
MongoDB Connection Manager
==========================
Handles MongoDB connection lifecycle using Motor (async driver).
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class MongoDBManager:
    """
    MongoDB Connection Manager
    
    Manages the MongoDB connection lifecycle:
    - Connection initialization
    - Connection pooling
    - Health checks
    - Graceful shutdown
    """
    
    def __init__(self):
        """Initialize MongoDB manager"""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """
        Connect to MongoDB
        
        Raises:
            ConnectionFailure: If connection fails
        """
        try:
            logger.info(f"Connecting to MongoDB: {settings.MONGODB_URL}")
            
            # Create Motor client
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
            )
            
            # Get database
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # Verify connection
            await self.client.admin.command('ping')
            
            logger.info(
                f"✅ Connected to MongoDB database: {settings.MONGODB_DB_NAME}",
                extra={
                    "database": settings.MONGODB_DB_NAME,
                    "max_pool_size": settings.MONGODB_MAX_POOL_SIZE,
                }
            )
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """
        Disconnect from MongoDB
        """
        if self.client:
            logger.info("Closing MongoDB connection...")
            self.client.close()
            logger.info("✅ MongoDB connection closed")
    
    async def health_check(self) -> bool:
        """
        Check if MongoDB connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Ping the database
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get the database instance
        
        Returns:
            AsyncIOMotorDatabase: MongoDB database
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.db:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db
    
    def get_collection(self, name: str):
        """
        Get a collection from the database
        
        Args:
            name: Collection name
            
        Returns:
            AsyncIOMotorCollection: MongoDB collection
        """
        return self.get_database()[name]


# Global MongoDB manager instance
mongodb_manager = MongoDBManager()


async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency to get database instance
    
    Returns:
        AsyncIOMotorDatabase: MongoDB database
    """
    return mongodb_manager.get_database()