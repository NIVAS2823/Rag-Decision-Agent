"""
Document Models
===============
Pydantic models for uploaded documents and metadata.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field
from bson import ObjectId

from app.models.user import PyObjectId



class DocumentStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document file types"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"



class DocumentInDB(BaseModel):
    """Document metadata in database"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str = Field(..., description="User who uploaded the document")
    
    filename: str = Field(..., description="Original filename")
    file_type: DocumentType = Field(..., description="File type")
    file_size_bytes: int = Field(..., description="File size in bytes")
    file_hash: str = Field(..., description="SHA256 hash of file")
    storage_path: str = Field(..., description="Path in cloud storage (R2)")
    
    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    chunk_count: Optional[int] = Field(default=None, description="Number of chunks created")
    processing_error: Optional[str] = Field(default=None, description="Error message if failed")
    
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)
    
    metadata: dict = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }



class Document(BaseModel):
    """Document response model"""
    id: str
    user_id: str
    filename: str
    file_type: DocumentType
    file_size_bytes: int
    status: DocumentStatus
    chunk_count: Optional[int] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    @classmethod
    def from_db(cls, doc_db: DocumentInDB) -> "Document":
        """Convert database model to response model"""
        return cls(
            id=str(doc_db.id),
            user_id=doc_db.user_id,
            filename=doc_db.filename,
            file_type=doc_db.file_type,
            file_size_bytes=doc_db.file_size_bytes,
            status=doc_db.status,
            chunk_count=doc_db.chunk_count,
            uploaded_at=doc_db.uploaded_at,
            processed_at=doc_db.processed_at,
        )