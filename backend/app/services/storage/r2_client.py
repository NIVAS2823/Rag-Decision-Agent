"""
Cloudflare R2 Storage Client
=============================
Handles file uploads to Cloudflare R2 with local filesystem fallback.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, BinaryIO
import aioboto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class R2StorageClient:
    """
    R2 Storage Client
    
    Handles file uploads to Cloudflare R2 with automatic fallback to local storage.
    """
    
    def __init__(self):
        self.use_r2 = settings.r2_configured
        self.bucket_name = settings.R2_BUCKET_NAME
        
        # Local storage fallback path
        self.local_storage_path = Path("/home/claude/uploads")
        
        if not self.use_r2:
            logger.warning("R2 not configured. Using local filesystem storage.")
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
        else:
            logger.info("R2 configured. Using Cloudflare R2 for storage.")
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        user_id: str
    ) -> str:
        """
        Upload file to R2 or local storage
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type
            user_id: User ID (for organization)
            
        Returns:
            str: Storage path
        """
        # Generate unique storage path
        file_hash = hashlib.sha256(file_content).hexdigest()[:16]
        storage_filename = f"{user_id}/{file_hash}_{filename}"
        
        if self.use_r2:
            return await self._upload_to_r2(
                file_content,
                storage_filename,
                content_type
            )
        else:
            return await self._upload_to_local(
                file_content,
                storage_filename
            )
    
    async def _upload_to_r2(
        self,
        file_content: bytes,
        storage_path: str,
        content_type: str
    ) -> str:
        """
        Upload file to Cloudflare R2
        
        Args:
            file_content: File content
            storage_path: Path in bucket
            content_type: MIME type
            
        Returns:
            str: Storage path
        """
        try:
            session = aioboto3.Session()
            
            async with session.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto"  # R2 uses "auto" region
            ) as s3_client:
                
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=storage_path,
                    Body=file_content,
                    ContentType=content_type
                )
                
                logger.info(
                    f"File uploaded to R2: {storage_path}",
                    extra={"bucket": self.bucket_name, "key": storage_path}
                )
                
                return f"r2://{self.bucket_name}/{storage_path}"
                
        except ClientError as e:
            logger.error(f"R2 upload failed: {e}")
            raise
    
    async def _upload_to_local(
        self,
        file_content: bytes,
        storage_path: str
    ) -> str:
        """
        Upload file to local filesystem
        
        Args:
            file_content: File content
            storage_path: Relative path
            
        Returns:
            str: Storage path
        """
        try:
            file_path = self.local_storage_path / storage_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(
                f"File uploaded to local storage: {storage_path}",
                extra={"path": str(file_path)}
            )
            
            return f"local://{storage_path}"
            
        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            raise
    
    async def download_file(self, storage_path: str) -> Optional[bytes]:
        """
        Download file from storage
        
        Args:
            storage_path: Storage path (r2://... or local://...)
            
        Returns:
            Optional[bytes]: File content if found
        """
        if storage_path.startswith("r2://"):
            return await self._download_from_r2(storage_path)
        elif storage_path.startswith("local://"):
            return await self._download_from_local(storage_path)
        else:
            logger.error(f"Invalid storage path: {storage_path}")
            return None
    
    async def _download_from_r2(self, storage_path: str) -> Optional[bytes]:
        """Download file from R2"""
        try:
            # Extract bucket and key from path
            path_parts = storage_path.replace("r2://", "").split("/", 1)
            bucket = path_parts[0]
            key = path_parts[1]
            
            session = aioboto3.Session()
            
            async with session.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto"
            ) as s3_client:
                
                response = await s3_client.get_object(Bucket=bucket, Key=key)
                
                async with response["Body"] as stream:
                    return await stream.read()
                    
        except ClientError as e:
            logger.error(f"R2 download failed: {e}")
            return None
    
    async def _download_from_local(self, storage_path: str) -> Optional[bytes]:
        """Download file from local filesystem"""
        try:
            relative_path = storage_path.replace("local://", "")
            file_path = self.local_storage_path / relative_path
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            with open(file_path, "rb") as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Local download failed: {e}")
            return None
    
    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage
        
        Args:
            storage_path: Storage path
            
        Returns:
            bool: True if deleted
        """
        if storage_path.startswith("r2://"):
            return await self._delete_from_r2(storage_path)
        elif storage_path.startswith("local://"):
            return await self._delete_from_local(storage_path)
        return False
    
    async def _delete_from_r2(self, storage_path: str) -> bool:
        """Delete file from R2"""
        try:
            path_parts = storage_path.replace("r2://", "").split("/", 1)
            bucket = path_parts[0]
            key = path_parts[1]
            
            session = aioboto3.Session()
            
            async with session.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto"
            ) as s3_client:
                
                await s3_client.delete_object(Bucket=bucket, Key=key)
                logger.info(f"File deleted from R2: {storage_path}")
                return True
                
        except ClientError as e:
            logger.error(f"R2 delete failed: {e}")
            return False
    
    async def _delete_from_local(self, storage_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            relative_path = storage_path.replace("local://", "")
            file_path = self.local_storage_path / relative_path
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted from local storage: {storage_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Local delete failed: {e}")
            return False


# Global storage client instance
r2_storage = R2StorageClient()