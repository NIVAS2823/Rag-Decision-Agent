"""
Storage Services
================
File storage abstractions (R2, local filesystem).
"""

from app.services.storage.r2_client import r2_storage

__all__ = ["r2_storage"]