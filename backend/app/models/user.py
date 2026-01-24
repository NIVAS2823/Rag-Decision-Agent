"""
User Models
===========
Pydantic models for user data and validation.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, field_validator
from bson import ObjectId


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# ============================================================================
# HELPER CLASSES
# ============================================================================

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, info):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        schema.update(type="string")
        return schema


# ============================================================================
# DATABASE MODEL
# ============================================================================

class UserInDB(BaseModel):
    """
    User model as stored in database
    
    This represents the complete user document in MongoDB.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    email: EmailStr = Field(..., description="User email address (unique)")
    hashed_password: str = Field(..., description="Bcrypt hashed password")
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(default=True, description="Whether user account is active")
    is_verified: bool = Field(default=False, description="Whether email is verified")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    
    # Metadata
    metadata: dict = Field(default_factory=dict, description="Additional user metadata")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "hashed_password": "$2b$12$...",
                "full_name": "John Doe",
                "role": "user",
                "is_active": True,
                "is_verified": False,
            }
        }
    }


# ============================================================================
# REQUEST MODELS
# ============================================================================

class UserCreate(BaseModel):
    """
    User creation request
    
    Used when creating a new user account.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    
    @field_validator("password")
    def validate_password(cls, v):
        """
        Validate password strength
        
        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "Jane Smith",
                "role": "user"
            }
        }
    }


class UserUpdate(BaseModel):
    """
    User update request
    
    All fields are optional - only provided fields will be updated.
    """
    email: Optional[EmailStr] = Field(default=None, description="User email address")
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="User's full name")
    role: Optional[UserRole] = Field(default=None, description="User role")
    is_active: Optional[bool] = Field(default=None, description="Whether user account is active")
    password: Optional[str] = Field(default=None, min_length=8, description="New password")
    
    @field_validator("password")
    def validate_password(cls, v):
        """Validate password if provided"""
        if v is None:
            return v
        
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Jane Doe",
                "role": "admin"
            }
        }
    }


class PasswordChange(BaseModel):
    """
    Password change request
    
    Used when a user wants to change their password.
    """
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    
    @field_validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class User(BaseModel):
    """
    User response model
    
    Used when returning user data to clients.
    NEVER includes the hashed password.
    """
    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., description="User's full name")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether email is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "user",
                "is_active": True,
                "is_verified": True,
                "created_at": "2025-01-22T12:00:00Z",
                "updated_at": "2025-01-22T12:00:00Z",
                "last_login": "2025-01-22T14:30:00Z"
            }
        }
    }
    
    @classmethod
    def from_db(cls, user_db: UserInDB) -> "User":
        """
        Convert database model to response model
        
        Args:
            user_db: User from database
            
        Returns:
            User: User response model (without password)
        """
        return cls(
            id=str(user_db.id),
            email=user_db.email,
            full_name=user_db.full_name,
            role=user_db.role,
            is_active=user_db.is_active,
            is_verified=user_db.is_verified,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            last_login=user_db.last_login,
        )


class UserList(BaseModel):
    """
    List of users response
    
    Used when returning multiple users (e.g., admin user list).
    """
    users: list[User] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=10, description="Number of users per page")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "users": [],
                "total": 42,
                "page": 1,
                "page_size": 10
            }
        }
    }