"""
Database Client
===============
Centralized database access with collection management.
"""

from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorCollection

from app.services.database.mongodb import mongodb_manager
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class DatabaseClient:
    """
    Database Client Singleton
    
    Provides centralized access to all database collections
    and manages database initialization.
    """
    
    USERS_COLLECTION = "users"
    DECISIONS_COLLECTION = "decisions"
    DOCUMENTS_COLLECTION = "documents"
    AUDIT_LOGS_COLLECTION = "audit_logs"
    SESSIONS_COLLECTION = "sessions"
    
    def __init__(self):
        """Initialize database client"""
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize database collections and indexes
        
        Creates collections if they don't exist and sets up indexes.
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        logger.info("Initializing database collections and indexes...")
        
        try:
            await self._create_users_indexes()
            await self._create_decisions_indexes()
            await self._create_documents_indexes()
            await self._create_audit_logs_indexes()
            await self._create_sessions_indexes()

            await self.create_collection_validators()

            indexes = await self.verify_indexes()
            total_indexes = sum(len(idx_list) for idx_list in indexes.values())
            logger.info(f"✅ Verified {total_indexes} indexes across {len(indexes)} collections")
            
            self._initialized = True
            logger.info("✅ Database initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    
    def get_users_collection(self) -> AsyncIOMotorCollection:
        """Get users collection"""
        return mongodb_manager.get_collection(self.USERS_COLLECTION)
    
    def get_decisions_collection(self) -> AsyncIOMotorCollection:
        """Get decisions collection"""
        return mongodb_manager.get_collection(self.DECISIONS_COLLECTION)
    
    def get_documents_collection(self) -> AsyncIOMotorCollection:
        """Get documents collection"""
        return mongodb_manager.get_collection(self.DOCUMENTS_COLLECTION)
    
    def get_audit_logs_collection(self) -> AsyncIOMotorCollection:
        """Get audit logs collection"""
        return mongodb_manager.get_collection(self.AUDIT_LOGS_COLLECTION)
    
    def get_sessions_collection(self) -> AsyncIOMotorCollection:
        """Get sessions collection"""
        return mongodb_manager.get_collection(self.SESSIONS_COLLECTION)
    
    
    async def _create_users_indexes(self) -> None:
        """Create indexes for users collection"""
        collection = self.get_users_collection()
        
        await collection.create_index("email", unique=True)
        
        await collection.create_index("created_at")
        
        await collection.create_index("role")
        
        await collection.create_index("is_active")
        
        logger.info(f"✅ Created indexes for {self.USERS_COLLECTION}")
    
    async def _create_decisions_indexes(self) -> None:
        """Create indexes for decisions collection"""
        collection = self.get_decisions_collection()
        
        await collection.create_index("user_id")
        
        await collection.create_index("created_at")
        
        await collection.create_index([("user_id", 1), ("created_at", -1)])
        
        await collection.create_index("status")
        
        await collection.create_index([
            ("query", "text"),
            ("decision.recommendation", "text"),
        ])
        
        logger.info(f"✅ Created indexes for {self.DECISIONS_COLLECTION}")
    
    async def _create_documents_indexes(self) -> None:
        """Create indexes for documents collection"""
        collection = self.get_documents_collection()
        
        await collection.create_index("user_id")
        
        await collection.create_index("uploaded_at")
        
        await collection.create_index("file_type")
        
        await collection.create_index("status")
        
        await collection.create_index("filename", name="filename_text")
        
        logger.info(f"✅ Created indexes for {self.DOCUMENTS_COLLECTION}")
    
    async def _create_audit_logs_indexes(self) -> None:
        collection = self.get_audit_logs_collection()

        indexes = await collection.index_information()

        if "timestamp_1" in indexes:
            logger.warning("Dropping old timestamp index to recreate TTL index")
            await collection.drop_index("timestamp_1")

        await collection.create_index("user_id")
        await collection.create_index([("user_id", 1), ("timestamp", -1)])
        await collection.create_index("action")
        await collection.create_index("resource_type")

        await collection.create_index(
            "timestamp",
            expireAfterSeconds=7776000,
            name="audit_log_ttl"
        )

        logger.info(f"✅ Created indexes for {self.AUDIT_LOGS_COLLECTION}")

    
    async def _create_sessions_indexes(self) -> None:
        """Create indexes for sessions collection"""
        collection = self.get_sessions_collection()
        
        await collection.create_index("session_id", unique=True)
        
        await collection.create_index("user_id")
        
        await collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            name="session_ttl"
        )
        
        logger.info(f"✅ Created indexes for {self.SESSIONS_COLLECTION}")
    
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dict[str, Any]: Database statistics
        """
        db = mongodb_manager.get_database()
        
        stats = await db.command("dbStats")
        
        return {
            "database": stats.get("db"),
            "collections": stats.get("collections"),
            "data_size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2),
            "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
            "indexes": stats.get("indexes"),
            "index_size_mb": round(stats.get("indexSize", 0) / (1024 * 1024), 2),
        }
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict[str, Any]: Collection statistics
        """
        db = mongodb_manager.get_database()
        
        stats = await db.command("collStats", collection_name)
        
        return {
            "collection": collection_name,
            "count": stats.get("count"),
            "size_mb": round(stats.get("size", 0) / (1024 * 1024), 2),
            "avg_obj_size": stats.get("avgObjSize"),
            "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
            "indexes": stats.get("nindexes"),
        }
    
    async def list_collections(self) -> list[str]:
        """
        List all collections in the database
        
        Returns:
            list[str]: List of collection names
        """
        db = mongodb_manager.get_database()
        collections = await db.list_collection_names()
        return collections

    
    async def create_collection_validators(self) -> None:
        """
        Create JSON schema validators for collections
        
        Enforces data integrity at the database level.
        """
        db = mongodb_manager.get_database()
        
        user_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["email", "hashed_password", "full_name", "role", "created_at"],
                "properties": {
                    "email": {
                        "bsonType": "string",
                        "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                        "description": "Must be a valid email"
                    },
                    "hashed_password": {
                        "bsonType": "string",
                        "minLength": 1,
                        "description": "Hashed password required"
                    },
                    "full_name": {
                        "bsonType": "string",
                        "minLength": 1,
                        "maxLength": 100,
                        "description": "Full name required"
                    },
                    "role": {
                        "enum": ["admin", "user", "viewer"],
                        "description": "Must be a valid role"
                    },
                    "is_active": {
                        "bsonType": "bool",
                        "description": "Active status"
                    },
                    "is_verified": {
                        "bsonType": "bool",
                        "description": "Verification status"
                    }
                }
            }
        }
        
        try:
            await db.command({
                "collMod": self.USERS_COLLECTION,
                "validator": user_validator,
                "validationLevel": "moderate"
            })
            logger.info(f"✅ Applied schema validator to {self.USERS_COLLECTION}")
        except Exception as e:
            logger.debug(f"Could not apply validator to {self.USERS_COLLECTION}: {e}")

        decision_validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id", "query", "status", "created_at"],
        "properties": {
            "user_id": {
                "bsonType": "string",
                "description": "User ID required"
            },
            "query": {
                "bsonType": "string",
                "minLength": 10,
                "description": "Decision query required"
            },
            "context": {
                "bsonType": ["string", "null"],
                "description": "Optional context"
            },
            "status": {
                "enum": ["pending", "processing", "completed", "failed"],
                "description": "Decision status"
            },
            "created_at": {
                "bsonType": "date",
                "description": "Creation timestamp"
            }
        }
    }
}

        try:
            await db.command({
        "collMod": self.DECISIONS_COLLECTION,
        "validator": decision_validator,
        "validationLevel": "moderate"
        })
            logger.info(f"✅ Applied schema validator to {self.DECISIONS_COLLECTION}")
        except Exception as e:
            logger.debug(f"Could not apply validator to {self.DECISIONS_COLLECTION}: {e}")

    
    async def verify_indexes(self) -> Dict[str, list]:
        """
        Verify all indexes are created
        
        Returns:
            Dict[str, list]: Dictionary of collection names to their indexes
        """
        result = {}
        
        collections = [
            self.USERS_COLLECTION,
            self.DECISIONS_COLLECTION,
            self.DOCUMENTS_COLLECTION,
            self.AUDIT_LOGS_COLLECTION,
            self.SESSIONS_COLLECTION,
        ]
        
        for collection_name in collections:
            collection = mongodb_manager.get_collection(collection_name)
            indexes = await collection.list_indexes().to_list(length=None)
            result[collection_name] = [idx["name"] for idx in indexes]
        
        return result

db_client = DatabaseClient()