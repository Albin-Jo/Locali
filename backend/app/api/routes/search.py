from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field

from ...services.vector_search import HybridSearchService


# Dependency placeholder - will be overridden in main.py
async def get_search_service():
    raise NotImplementedError


# Request/Response Models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=10, ge=1, le=50)
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    min_score: float = Field(default=0.1, ge=0.0, le=1.0)


class SearchResultResponse(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    rank: int
    metadata: dict
    chunk_type: str
    language: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultResponse]
    total_results: int
    search_time_ms: float


class SearchStatsResponse(BaseModel):
    total_chunks: int
    vector_store_size: int
    keyword_index_size: int
    embedding_model: str


# Router
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search_documents(
        request: SearchRequest,
        search_service: HybridSearchService = Depends(get_search_service)
):
    """Search through indexed documents."""
    import time

    try:
        start_time = time.perf_counter()

        # Perform search
        search_results = await search_service.search(
            query=request.query,
            k=request.max_results,
            vector_weight=request.vector_weight,
            keyword_weight=request.keyword_weight,
            min_score=request.min_score
        )

        search_time_ms = (time.perf_counter() - start_time) * 1000

        # Convert to response format
        results = [
            SearchResultResponse(
                chunk_id=result.chunk.id,
                document_id=result.document_id,
                content=result.chunk.content,
                score=result.score,
                rank=result.rank,
                metadata=result.chunk.metadata,
                chunk_type=result.chunk.chunk_type,
                language=result.chunk.language
            )
            for result in search_results
        ]

        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/", response_model=SearchResponse)
async def search_documents_get(
        q: str = Query(..., description="Search query"),
        max_results: int = Query(default=10, ge=1, le=50),
        vector_weight: float = Query(default=0.7, ge=0.0, le=1.0),
        keyword_weight: float = Query(default=0.3, ge=0.0, le=1.0),
        min_score: float = Query(default=0.1, ge=0.0, le=1.0),
        search_service: HybridSearchService = Depends(get_search_service)
):
    """Search through indexed documents (GET endpoint)."""
    request = SearchRequest(
        query=q,
        max_results=max_results,
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        min_score=min_score
    )

    return await search_documents(request, search_service)


@router.get("/stats", response_model=SearchStatsResponse)
async def get_search_stats(
        search_service: HybridSearchService = Depends(get_search_service)
):
    """Get search service statistics."""
    try:
        stats = await search_service.get_stats()

        return SearchStatsResponse(
            total_chunks=stats['total_chunks'],
            vector_store_size=stats['vector_store_size'],
            keyword_index_size=stats['keyword_index_size'],
            embedding_model=stats['embedding_model']
        )

    except Exception as e:
        logger.error(f"Failed to get search stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get search stats")
