"""
Document Routes
===============
Document upload and management endpoints.
"""

import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse

from app.models.user import UserInDB
from app.models.document import Document, DocumentInDB, DocumentType, DocumentStatus
from app.api.dependencies.auth import get_current_user
from app.services.database.repositories import document_repository
from app.services.storage import r2_storage
from app.core.config import settings
from app.core.logging_config import get_logger


logger = get_logger(__name__)
router = APIRouter()


# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
CONTENT_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_file_type(filename: str) -> DocumentType:
    """
    Validate file type and return DocumentType enum
    
    Args:
        filename: Original filename
        
    Returns:
        DocumentType: Document type enum
        
    Raises:
        HTTPException: If file type not allowed
    """
    extension = get_file_extension(filename)
    
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Map extension to DocumentType
    extension_map = {
        ".pdf": DocumentType.PDF,
        ".txt": DocumentType.TXT,
        ".docx": DocumentType.DOCX,
    }
    
    return extension_map[extension]


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


# ============================================================================
# DOCUMENT UPLOAD
# ============================================================================

@router.post(
    "/upload",
    response_model=Document,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document",
    description="Upload a document for RAG processing (PDF, TXT, DOCX)",
    tags=["documents"],
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Upload Document
    
    Uploads a document to cloud storage and creates a database record.
    Supported formats: PDF, TXT, DOCX
    
    Args:
        file: Uploaded file
        current_user: Current authenticated user
        
    Returns:
        Document: Created document metadata
        
    Raises:
        HTTPException 400: If file type not allowed or file too large
        HTTPException 409: If file already exists (duplicate hash)
        HTTPException 500: If upload fails
    """
    try:
        # Validate file is provided
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Validate file type
        file_type = validate_file_type(file.filename)
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Calculate file hash
        file_hash = calculate_file_hash(file_content)
        
        # Check for duplicate
        existing_doc = await document_repository.check_file_exists(
            file_hash=file_hash,
            user_id=str(current_user.id)
        )
        
        if existing_doc:
            logger.warning(
                f"Duplicate file upload attempt: {file.filename}",
                extra={
                    "user_id": str(current_user.id),
                    "file_hash": file_hash,
                    "existing_doc_id": str(existing_doc.id)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File already exists (uploaded as '{existing_doc.filename}')"
            )
        
        # Upload to storage
        content_type = CONTENT_TYPE_MAP.get(get_file_extension(file.filename), "application/octet-stream")
        
        storage_path = await r2_storage.upload_file(
            file_content=file_content,
            filename=file.filename,
            content_type=content_type,
            user_id=str(current_user.id)
        )
        
        # Create database record
        document = await document_repository.create(
            user_id=str(current_user.id),
            filename=file.filename,
            file_type=file_type,
            file_size_bytes=file_size,
            file_hash=file_hash,
            storage_path=storage_path,
            metadata={
                "content_type": content_type,
                "original_filename": file.filename
            }
        )
        
        logger.info(
            f"Document uploaded successfully: {file.filename}",
            extra={
                "document_id": str(document.id),
                "user_id": str(current_user.id),
                "file_size": file_size,
                "file_type": file_type.value
            }
        )
        
        return Document.from_db(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


# ============================================================================
# DOCUMENT RETRIEVAL
# ============================================================================

@router.get(
    "",
    response_model=dict,
    summary="List user documents",
    description="Get list of documents uploaded by current user",
    tags=["documents"],
)
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of documents to return"),
    status: DocumentStatus = Query(None, description="Filter by status"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    List User Documents
    
    Returns paginated list of documents uploaded by the current user.
    
    Args:
        skip: Number of documents to skip (pagination)
        limit: Maximum documents to return (max 100)
        status: Filter by processing status
        current_user: Current authenticated user
        
    Returns:
        dict: Documents list with pagination info
    """
    try:
        # Get documents
        documents = await document_repository.get_by_user(
            user_id=str(current_user.id),
            skip=skip,
            limit=limit,
            status=status
        )
        
        # Get total count
        total = await document_repository.count_by_user(
            user_id=str(current_user.id),
            status=status
        )
        
        return {
            "documents": [Document.from_db(doc) for doc in documents],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.get(
    "/{document_id}",
    response_model=Document,
    summary="Get document details",
    description="Get details of a specific document",
    tags=["documents"],
)
async def get_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get Document Details
    
    Returns metadata for a specific document.
    Only the document owner can access it.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        
    Returns:
        Document: Document metadata
        
    Raises:
        HTTPException 404: If document not found
        HTTPException 403: If user doesn't own the document
    """
    try:
        # Get document
        document = await document_repository.get_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check ownership
        if document.user_id != str(current_user.id):
            logger.warning(
                f"Unauthorized document access attempt",
                extra={
                    "document_id": document_id,
                    "user_id": str(current_user.id),
                    "owner_id": document.user_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this document"
            )
        
        return Document.from_db(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


# ============================================================================
# DOCUMENT DELETION
# ============================================================================

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete document",
    description="Delete a document and its storage file",
    tags=["documents"],
)
async def delete_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Delete Document
    
    Deletes a document from both storage and database.
    Only the document owner can delete it.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        
    Returns:
        dict: Deletion confirmation
        
    Raises:
        HTTPException 404: If document not found
        HTTPException 403: If user doesn't own the document
    """
    try:
        # Get document
        document = await document_repository.get_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check ownership
        if document.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this document"
            )
        
        # Delete from storage
        storage_deleted = await r2_storage.delete_file(document.storage_path)
        
        if not storage_deleted:
            logger.warning(
                f"Failed to delete file from storage: {document.storage_path}",
                extra={"document_id": document_id}
            )
        
        # Delete from database
        db_deleted = await document_repository.delete(document_id)
        
        if not db_deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document from database"
            )
        
        logger.info(
            f"Document deleted: {document.filename}",
            extra={
                "document_id": document_id,
                "user_id": str(current_user.id)
            }
        )
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
            "filename": document.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )   