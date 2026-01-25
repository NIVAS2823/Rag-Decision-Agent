"""
Database Repositories
=====================
Repository pattern for database operations.
"""

from app.services.database.repositories.user_repository import user_repository


__all__ = ["user_repository"]