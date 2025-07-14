# backend/app/api/routes/documents.py

import os
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from loguru import logger
from pydantic import BaseModel

from ...services.document_processor import DocumentProcessor
from ...services.vector_search import HybridSearchService


# Dependency placeholders - will be overridden in main.py
async def get_document_processor():
    raise NotImplementedError


async def get_search_service():
    raise NotImplementedError


# Request/Response Models
class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    total_chunks: int
    processed_at: str


class DocumentDetailResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    chunks: List[dict]
    metadata: dict
    processed_at: str


class ProcessDocumentRequest(BaseModel):
    content: str
    filename: str
    content_type: str = "text/plain"


# Router
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
        file: UploadFile = File(...),
        document_processor: DocumentProcessor = Depends(get_document_processor),
        search_service: HybridSearchService = Depends(get_search_service)
):
    """Upload and process a document."""
    try:
        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024
        content = await file.read()

        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")

        # Validate file type
        allowed_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
                              '.rs', '.go', '.php', '.rb', '.swift', '.kt', '.md', '.txt',
                              '.json', '.yaml', '.yml', '.csv', '.html', '.css'}

        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        # Save file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix=file_extension, delete=False) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        try:
            # Process the document
            document = await document_processor.process_uploaded_file(temp_path)

            # Index for search
            await search_service.index_document(document)

            return DocumentResponse(
                id=document.id,
                filename=document.filename,
                content_type=document.content_type,
                size_bytes=document.size_bytes,
                total_chunks=len(document.chunks),
                processed_at=document.processed_at.isoformat()
            )

        finally:
            # Clean up temp file
            if temp_path.exists():
                os.unlink(temp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.post("/process-text", response_model=DocumentResponse)
async def process_text_content(
        request: ProcessDocumentRequest,
        document_processor: DocumentProcessor = Depends(get_document_processor),
        search_service: HybridSearchService = Depends(get_search_service)
):
    """Process text content directly."""
    try:
        # Create temporary file with content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(request.content)
            temp_path = Path(temp_file.name)

        try:
            # Process the document
            document = await document_processor.process_document(temp_path, request.content)
            document.filename = request.filename
            document.content_type = request.content_type

            # Save metadata
            await document_processor._save_document_metadata(document)

            # Index for search
            await search_service.index_document(document)

            return DocumentResponse(
                id=document.id,
                filename=document.filename,
                content_type=document.content_type,
                size_bytes=document.size_bytes,
                total_chunks=len(document.chunks),
                processed_at=document.processed_at.isoformat()
            )

        finally:
            # Clean up temp file
            if temp_path.exists():
                os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Text processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process text: {str(e)}")


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
        document_processor: DocumentProcessor = Depends(get_document_processor)
):
    """List all processed documents."""
    try:
        documents = await document_processor.list_documents()

        return [
            DocumentResponse(
                id=doc['id'],
                filename=doc['filename'],
                content_type=doc['content_type'],
                size_bytes=doc['size_bytes'],
                total_chunks=doc['total_chunks'],
                processed_at=doc['processed_at']
            )
            for doc in documents
        ]

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
        document_id: str,
        document_processor: DocumentProcessor = Depends(get_document_processor)
):
    """Get a specific document with all chunks."""
    try:
        document = await document_processor.get_document(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentDetailResponse(
            id=document.id,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            chunks=[chunk.to_dict() for chunk in document.chunks],
            metadata=document.metadata,
            processed_at=document.processed_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.delete("/{document_id}")
async def delete_document(
        document_id: str,
        document_processor: DocumentProcessor = Depends(get_document_processor),
        search_service: HybridSearchService = Depends(get_search_service)
):
    """Delete a document and remove from search index."""
    try:
        # Remove from search index
        await search_service.remove_document(document_id)

        # Delete document
        success = await document_processor.delete_document(document_id)

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")
