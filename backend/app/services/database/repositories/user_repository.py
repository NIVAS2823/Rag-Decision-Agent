"""
User Repository
===============
Database operations for user management.
"""

from typing import Optional, List
from datetime import datetime

from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from app.models.user import UserInDB, UserCreate, UserUpdate, User
from app.services.database import db_client
from app.services.auth.password import hash_password
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class UserRepository:
    """
    User repository for database operations
    """
    @property
    def collection(self):
        return db_client.get_users_collection()
    
    def __init__(self):
        """Initialize repository"""
        pass
    
    async def create(self, user_data: UserCreate) -> UserInDB:
        """
        Create a new user
        
        Args:
            user_data: User creation data
            
        Returns:
            UserInDB: Created user
            
        Raises:
            ValueError: If email already exists
        """
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user document
        user_dict = {
            "email": user_data.email,
            "hashed_password": hashed_password,
            "full_name": user_data.full_name,
            "role": user_data.role,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "metadata": {}
        }
        
        try:
            result = await self.collection.insert_one(user_dict)
            user_dict["_id"] = result.inserted_id
            
            logger.info(
                f"Created user: {user_data.email}",
                extra={"user_id": str(result.inserted_id)}
            )
            
            return UserInDB(**user_dict)
            
        except DuplicateKeyError:
            logger.warning(f"Duplicate email attempted: {user_data.email}")
            raise ValueError(f"User with email {user_data.email} already exists")
    
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[UserInDB]: User if found, None otherwise
        """
        if not ObjectId.is_valid(user_id):
            return None
        
        user_dict = await self.collection.find_one({"_id": ObjectId(user_id)})
        
        if user_dict:
            return UserInDB(**user_dict)
        return None
    
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Get user by email
        
        Args:
            email: User email
            
        Returns:
            Optional[UserInDB]: User if found, None otherwise
        """
        user_dict = await self.collection.find_one({"email": email})
        
        if user_dict:
            return UserInDB(**user_dict)
        return None
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[UserInDB]:
        """
        Get all users with pagination and filters
        
        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return
            role: Filter by role
            is_active: Filter by active status
            
        Returns:
            List[UserInDB]: List of users
        """
        # Build query filter
        query = {}
        if role:
            query["role"] = role
        if is_active is not None:
            query["is_active"] = is_active
        
        # Query database
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        
        users = []
        async for user_dict in cursor:
            users.append(UserInDB(**user_dict))
        
        return users
    
    async def count(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """
        Count users with filters
        
        Args:
            role: Filter by role
            is_active: Filter by active status
            
        Returns:
            int: Number of users
        """
        query = {}
        if role:
            query["role"] = role
        if is_active is not None:
            query["is_active"] = is_active
        
        return await self.collection.count_documents(query)
    
    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[UserInDB]:
        """
        Update user
        
        Args:
            user_id: User ID
            user_data: User update data
            
        Returns:
            Optional[UserInDB]: Updated user if found, None otherwise
        """
        if not ObjectId.is_valid(user_id):
            return None
        
        # Build update document (only include provided fields)
        update_dict = {}
        
        if user_data.email is not None:
            update_dict["email"] = user_data.email
        if user_data.full_name is not None:
            update_dict["full_name"] = user_data.full_name
        if user_data.role is not None:
            update_dict["role"] = user_data.role
        if user_data.is_active is not None:
            update_dict["is_active"] = user_data.is_active
        if user_data.password is not None:
            update_dict["hashed_password"] = hash_password(user_data.password)
        
        if not update_dict:
            # Nothing to update
            return await self.get_by_id(user_id)
        
        # Always update the updated_at timestamp
        update_dict["updated_at"] = datetime.utcnow()
        
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict},
                return_document=True  # Return updated document
            )
            
            if result:
                logger.info(
                    f"Updated user: {user_id}",
                    extra={"updated_fields": list(update_dict.keys())}
                )
                return UserInDB(**result)
            
            return None
            
        except DuplicateKeyError:
            raise ValueError(f"Email {user_data.email} is already taken")
    
    async def delete(self, user_id: str) -> bool:
        """
        Delete user (hard delete)
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        if not ObjectId.is_valid(user_id):
            return False
        
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted user: {user_id}")
            return True
        
        return False
    
    async def soft_delete(self, user_id: str) -> bool:
        """
        Soft delete user (mark as inactive)
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if deactivated, False if not found
        """
        if not ObjectId.is_valid(user_id):
            return False
        
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Soft deleted user: {user_id}")
            return True
        
        return False
    
    async def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if updated, False if not found
        """
        if not ObjectId.is_valid(user_id):
            return False
        
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        return result.modified_count > 0
    
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists with given email
        
        Args:
            email: Email to check
            
        Returns:
            bool: True if exists, False otherwise
        """
        count = await self.collection.count_documents({"email": email}, limit=1)
        return count > 0


# Global repository instance
user_repository = UserRepository()