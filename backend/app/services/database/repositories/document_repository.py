"""
Document Repository
===================
Database operations for document management.
"""

from typing import Optional, List
from datetime import datetime

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.models.document import DocumentInDB, DocumentStatus, DocumentType
from app.services.database import db_client
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class DocumentRepository:
    """
    Document repository for database operations
    """
    
    @property
    def collection(self):
        return db_client.get_documents_collection()
    
    async def create(
        self,
        user_id: str,
        filename: str,
        file_type: DocumentType,
        file_size_bytes: int,
        file_hash: str,
        storage_path: str,
        metadata: dict = None
    ) -> DocumentInDB:
        """
        Create a new document record
        
        Args:
            user_id: User who uploaded the document
            filename: Original filename
            file_type: Document type
            file_size_bytes: File size in bytes
            file_hash: SHA256 hash of file
            storage_path: Path in storage (R2 or local)
            metadata: Additional metadata
            
        Returns:
            DocumentInDB: Created document
        """
        document_dict = {
            "user_id": user_id,
            "filename": filename,
            "file_type": file_type.value,
            "file_size_bytes": file_size_bytes,
            "file_hash": file_hash,
            "storage_path": storage_path,
            "status": DocumentStatus.PENDING.value,
            "chunk_count": None,
            "processing_error": None,
            "uploaded_at": datetime.utcnow(),
            "processed_at": None,
            "metadata": metadata or {}
        }
        
        try:
            result = await self.collection.insert_one(document_dict)
            document_dict["_id"] = result.inserted_id
            
            logger.info(
                f"Document created: {filename}",
                extra={
                    "document_id": str(result.inserted_id),
                    "user_id": user_id,
                    "file_type": file_type.value
                }
            )
            
            return DocumentInDB(**document_dict)
            
        except PyMongoError as e:
            logger.error(f"Failed to create document: {e}")
            raise
    
    async def get_by_id(self, document_id: str) -> Optional[DocumentInDB]:
        """
        Get document by ID
        
        Args:
            document_id: Document ID
            
        Returns:
            Optional[DocumentInDB]: Document if found
        """
        if not ObjectId.is_valid(document_id):
            return None
        
        doc_dict = await self.collection.find_one({"_id": ObjectId(document_id)})
        
        if doc_dict:
            return DocumentInDB(**doc_dict)
        return None
    
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[DocumentStatus] = None
    ) -> List[DocumentInDB]:
        """
        Get documents by user
        
        Args:
            user_id: User ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            status: Filter by status
            
        Returns:
            List[DocumentInDB]: List of documents
        """
        query = {"user_id": user_id}
        
        if status:
            query["status"] = status.value
        
        cursor = self.collection.find(query).sort("uploaded_at", -1).skip(skip).limit(limit)
        
        documents = []
        async for doc_dict in cursor:
            documents.append(DocumentInDB(**doc_dict))
        
        return documents
    
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[DocumentStatus] = None
    ) -> int:
        """
        Count documents for a user
        
        Args:
            user_id: User ID
            status: Filter by status
            
        Returns:
            int: Number of documents
        """
        query = {"user_id": user_id}
        
        if status:
            query["status"] = status.value
        
        return await self.collection.count_documents(query)
    
    async def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
        chunk_count: Optional[int] = None,
        processing_error: Optional[str] = None
    ) -> bool:
        """
        Update document processing status
        
        Args:
            document_id: Document ID
            status: New status
            chunk_count: Number of chunks created
            processing_error: Error message if failed
            
        Returns:
            bool: True if updated
        """
        if not ObjectId.is_valid(document_id):
            return False
        
        update_dict = {
            "status": status.value,
        }
        
        if status == DocumentStatus.PROCESSED:
            update_dict["processed_at"] = datetime.utcnow()
        
        if chunk_count is not None:
            update_dict["chunk_count"] = chunk_count
        
        if processing_error is not None:
            update_dict["processing_error"] = processing_error
        
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count > 0:
            logger.info(
                f"Document status updated: {document_id} -> {status.value}",
                extra={"document_id": document_id}
            )
            return True
        
        return False
    
    async def delete(self, document_id: str) -> bool:
        """
        Delete document record
        
        Args:
            document_id: Document ID
            
        Returns:
            bool: True if deleted
        """
        if not ObjectId.is_valid(document_id):
            return False
        
        result = await self.collection.delete_one({"_id": ObjectId(document_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Document deleted: {document_id}")
            return True
        
        return False
    
    async def check_file_exists(self, file_hash: str, user_id: str) -> Optional[DocumentInDB]:
        """
        Check if file with same hash already exists for user
        
        Args:
            file_hash: SHA256 hash of file
            user_id: User ID
            
        Returns:
            Optional[DocumentInDB]: Existing document if found
        """
        doc_dict = await self.collection.find_one({
            "file_hash": file_hash,
            "user_id": user_id
        })
        
        if doc_dict:
            return DocumentInDB(**doc_dict)
        return None


# Global repository instance
document_repository = DocumentRepository()