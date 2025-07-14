# backend/app/services/vector_search.py

import asyncio
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

from loguru import logger
from ..core.config import settings
from ..core.logging import log_performance
from .document_processor import DocumentChunk, ProcessedDocument


@dataclass
class SearchResult:
    """Represents a search result with relevance score."""
    chunk: DocumentChunk
    score: float
    document_id: str
    rank: int

    def to_dict(self) -> dict:
        return {
            'chunk': self.chunk.to_dict(),
            'score': self.score,
            'document_id': self.document_id,
            'rank': self.rank
        }


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""

    def __init__(self):
        self.model = None
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"  # Lightweight model
        self.embedding_dim = 384
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer

            # Set cache directory to avoid permission issues
            cache_dir = Path(settings.vector_db_path) / "sentence_transformers_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Set environment variable for sentence transformers cache
            os.environ['SENTENCE_TRANSFORMERS_HOME'] = str(cache_dir)

            # Try to load model with custom cache directory
            logger.info(f"Initializing embedding model: {self.model_name}")
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=str(cache_dir)
            )
            logger.info(f"Embedding model initialized successfully: {self.model_name}")

        except ImportError:
            logger.warning("sentence-transformers not installed. Using dummy embeddings.")
            logger.info("Install with: pip install sentence-transformers")
            self.model = None
        except PermissionError as e:
            logger.error(f"Permission error loading embedding model: {e}")
            logger.info("Using dummy embeddings. Check cache directory permissions.")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            logger.info("Using dummy embeddings as fallback.")
            self.model = None

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self.model:
            # Return dummy embedding if model not available
            logger.debug("Using dummy embedding (model not available)")
            return [0.1] * self.embedding_dim  # Small non-zero values for better search

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode([text], convert_to_numpy=True)[0]
            )
            return embedding.tolist()

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.1] * self.embedding_dim

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self.model:
            logger.debug("Using dummy embeddings for batch (model not available)")
            return [[0.1] * self.embedding_dim for _ in texts]

        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts, convert_to_numpy=True)
            )
            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [[0.1] * self.embedding_dim for _ in texts]


class VectorStore:
    """Simple vector store using numpy for similarity search."""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.vectors_file = self.storage_path / "vectors.npy"
        self.metadata_file = self.storage_path / "metadata.json"

        # In-memory storage
        self.vectors: Optional[np.ndarray] = None
        self.metadata: List[Dict[str, Any]] = []

        self._load_from_disk()

    def _load_from_disk(self):
        """Load vectors and metadata from disk."""
        try:
            if self.vectors_file.exists():
                self.vectors = np.load(str(self.vectors_file))
                logger.info(f"Loaded {len(self.vectors)} vectors from disk")

            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded {len(self.metadata)} metadata entries")

        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            self.vectors = None
            self.metadata = []

    async def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        """Add chunks with their embeddings to the store."""
        if not chunks or not embeddings:
            return

        # Convert embeddings to numpy array
        new_vectors = np.array(embeddings)

        # Update vectors
        if self.vectors is None:
            self.vectors = new_vectors
        else:
            self.vectors = np.vstack([self.vectors, new_vectors])

        # Update metadata
        for chunk in chunks:
            self.metadata.append({
                'chunk_id': chunk.id,
                'document_id': chunk.document_id,
                'position': chunk.position,
                'chunk_type': chunk.chunk_type,
                'language': chunk.language,
                'content_preview': chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
            })

        # Save to disk
        await self._save_to_disk()

        logger.info(f"Added {len(chunks)} chunks to vector store")

    async def search(self, query_embedding: List[float], k: int = 10, min_score: float = 0.1) -> List[
        Tuple[int, float]]:
        """Search for similar vectors."""
        if self.vectors is None or len(self.vectors) == 0:
            return []

        try:
            query_vec = np.array(query_embedding)

            # Handle case where all embeddings are dummy (zeros)
            if np.allclose(self.vectors, 0):
                logger.debug("All embeddings are zero/dummy - returning empty results")
                return []

            # Compute cosine similarity
            norms = np.linalg.norm(self.vectors, axis=1)
            query_norm = np.linalg.norm(query_vec)

            if query_norm == 0:
                logger.debug("Query embedding is zero - returning empty results")
                return []

            # Avoid division by zero
            valid_indices = norms > 0
            if not np.any(valid_indices):
                logger.debug("No valid vector norms - returning empty results")
                return []

            similarities = np.zeros(len(self.vectors))
            similarities[valid_indices] = np.dot(self.vectors[valid_indices], query_vec) / (
                    norms[valid_indices] * query_norm
            )

            # Get top k results
            top_indices = np.argsort(similarities)[::-1][:k]

            results = []
            for i, idx in enumerate(top_indices):
                score = float(similarities[idx])
                if score >= min_score:
                    results.append((int(idx), score))
                else:
                    break

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def get_chunk_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get chunk metadata by vector index."""
        if 0 <= index < len(self.metadata):
            return self.metadata[index]
        return None

    async def delete_document_chunks(self, document_id: str):
        """Remove all chunks for a document."""
        if not self.metadata:
            return

        # Find indices to remove
        indices_to_remove = [
            i for i, meta in enumerate(self.metadata)
            if meta['document_id'] == document_id
        ]

        if not indices_to_remove:
            return

        # Remove from vectors and metadata
        if self.vectors is not None:
            mask = np.ones(len(self.vectors), dtype=bool)
            mask[indices_to_remove] = False
            self.vectors = self.vectors[mask]

        for index in reversed(indices_to_remove):  # Remove in reverse order
            del self.metadata[index]

        await self._save_to_disk()
        logger.info(f"Removed {len(indices_to_remove)} chunks for document {document_id}")

    async def _save_to_disk(self):
        """Save vectors and metadata to disk."""
        try:
            if self.vectors is not None:
                np.save(str(self.vectors_file), self.vectors)

            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")


class KeywordSearch:
    """Simple keyword-based search for exact matches."""

    def __init__(self):
        self.index: Dict[str, List[Tuple[str, int]]] = {}  # word -> [(chunk_id, frequency)]

    def index_chunk(self, chunk: DocumentChunk):
        """Add a chunk to the keyword index."""
        words = self._extract_keywords(chunk.content)

        for word, freq in words.items():
            if word not in self.index:
                self.index[word] = []
            self.index[word].append((chunk.id, freq))

    def search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """Search for chunks containing query keywords."""
        query_words = self._extract_keywords(query)

        # Score chunks based on keyword matches
        chunk_scores: Dict[str, float] = {}

        for word in query_words:
            if word in self.index:
                for chunk_id, freq in self.index[word]:
                    if chunk_id not in chunk_scores:
                        chunk_scores[chunk_id] = 0
                    chunk_scores[chunk_id] += freq * query_words[word]

        # Sort and return top k
        sorted_results = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:k]

    def _extract_keywords(self, text: str) -> Dict[str, int]:
        """Extract keywords from text with frequency."""
        # Simple word extraction - could be improved with proper tokenization
        words = text.lower().split()

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

        word_freq = {}
        for word in words:
            # Clean word
            word = ''.join(c for c in word if c.isalnum())
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        return word_freq

    def remove_document_chunks(self, document_id: str):
        """Remove chunks for a document from keyword index."""
        # This is simplified - in a real implementation, you'd track document->chunk mapping
        pass


class HybridSearchService:
    """Hybrid search combining vector similarity and keyword matching."""

    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore(settings.vector_db_path)
        self.keyword_search = KeywordSearch()
        self.chunk_store: Dict[str, DocumentChunk] = {}  # chunk_id -> chunk

        logger.info("HybridSearchService initialized")

    @log_performance("index_document")
    async def index_document(self, document: ProcessedDocument):
        """Index a document for search."""
        if not document.chunks:
            return

        # Generate embeddings for all chunks
        chunk_texts = [chunk.content for chunk in document.chunks]
        embeddings = await self.embedding_generator.generate_embeddings_batch(chunk_texts)

        # Add embeddings to chunks
        for chunk, embedding in zip(document.chunks, embeddings):
            chunk.embedding = embedding

        # Add to vector store
        await self.vector_store.add_chunks(document.chunks, embeddings)

        # Add to keyword index
        for chunk in document.chunks:
            self.keyword_search.index_chunk(chunk)
            self.chunk_store[chunk.id] = chunk

        logger.info(f"Indexed document {document.filename} with {len(document.chunks)} chunks")

    @log_performance("hybrid_search")
    async def search(
            self,
            query: str,
            k: int = 10,
            vector_weight: float = 0.7,
            keyword_weight: float = 0.3,
            min_score: float = 0.1
    ) -> List[SearchResult]:
        """Perform hybrid search combining vector and keyword results."""

        # Generate query embedding
        query_embedding = await self.embedding_generator.generate_embedding(query)

        # Vector search
        vector_results = await self.vector_store.search(query_embedding, k=k * 2)

        # Keyword search
        keyword_results = self.keyword_search.search(query, k=k * 2)

        # Combine results
        combined_scores: Dict[str, float] = {}
        chunk_indices: Dict[str, int] = {}

        # Process vector results
        for rank, (idx, score) in enumerate(vector_results):
            chunk_meta = await self.vector_store.get_chunk_by_index(idx)
            if chunk_meta:
                chunk_id = chunk_meta['chunk_id']
                combined_scores[chunk_id] = vector_weight * score
                chunk_indices[chunk_id] = idx

        # Process keyword results
        max_keyword_score = max([score for _, score in keyword_results], default=1.0)
        for chunk_id, score in keyword_results:
            normalized_score = score / max_keyword_score if max_keyword_score > 0 else 0
            if chunk_id in combined_scores:
                combined_scores[chunk_id] += keyword_weight * normalized_score
            else:
                combined_scores[chunk_id] = keyword_weight * normalized_score

        # Create search results
        results = []
        for rank, (chunk_id, score) in enumerate(
                sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:k]
        ):
            if score >= min_score and chunk_id in self.chunk_store:
                chunk = self.chunk_store[chunk_id]
                result = SearchResult(
                    chunk=chunk,
                    score=score,
                    document_id=chunk.document_id,
                    rank=rank + 1
                )
                results.append(result)

        logger.info(f"Hybrid search for '{query}' returned {len(results)} results")
        return results

    async def remove_document(self, document_id: str):
        """Remove all chunks for a document from search indices."""
        await self.vector_store.delete_document_chunks(document_id)
        self.keyword_search.remove_document_chunks(document_id)

        # Remove from chunk store
        chunks_to_remove = [
            chunk_id for chunk_id, chunk in self.chunk_store.items()
            if chunk.document_id == document_id
        ]

        for chunk_id in chunks_to_remove:
            del self.chunk_store[chunk_id]

        logger.info(f"Removed document {document_id} from search indices")

    async def get_stats(self) -> Dict[str, Any]:
        """Get search service statistics."""
        return {
            'total_chunks': len(self.chunk_store),
            'vector_store_size': len(self.vector_store.vectors) if self.vector_store.vectors is not None else 0,
            'keyword_index_size': len(self.keyword_search.index),
            'embedding_model': self.embedding_generator.model_name
        }