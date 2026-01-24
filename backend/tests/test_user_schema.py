"""
Quick test of user model serialization
"""
from datetime import datetime
from app.models.user import UserCreate, UserInDB, User, UserRole

# Test UserCreate
print("=" * 70)
print("Testing UserCreate")
print("=" * 70)

user_create = UserCreate(
    email="john@example.com",
    password="SecurePass123",
    full_name="John Doe",
    role=UserRole.USER
)

print(f"Email: {user_create.email}")
print(f"Full Name: {user_create.full_name}")
print(f"Role: {user_create.role}")
print(f"\nJSON:\n{user_create.model_dump_json(indent=2)}")

# Test UserInDB
print("\n" + "=" * 70)
print("Testing UserInDB")
print("=" * 70)

user_db = UserInDB(
    email="john@example.com",
    hashed_password="$2b$12$hashed_password_here",
    full_name="John Doe",
    role=UserRole.USER,
)

print(f"\nJSON:\n{user_db.model_dump_json(indent=2, exclude={'hashed_password'})}")

# Test User response
print("\n" + "=" * 70)
print("Testing User Response Model")
print("=" * 70)

user_response = User(
    id="507f1f77bcf86cd799439011",
    email="john@example.com",
    full_name="John Doe",
    role=UserRole.USER,
    is_active=True,
    is_verified=True,
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow(),
)

print(f"\nJSON:\n{user_response.model_dump_json(indent=2)}")

print("\n" + "=" * 70)
print("✅ All models working correctly!")
print("=" * 70)