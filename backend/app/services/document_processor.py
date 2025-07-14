# backend/app/services/document_processor.py

import asyncio
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from loguru import logger
from ..core.config import settings
from ..core.logging import log_performance


@dataclass
class DocumentChunk:
    """Represents a processed document chunk."""
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any]
    position: int
    chunk_type: str  # 'text', 'code', 'markdown'
    language: Optional[str] = None
    embedding: Optional[List[float]] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentChunk':
        return cls(**data)


@dataclass
class ProcessedDocument:
    """Represents a processed document with metadata."""
    id: str
    filename: str
    file_path: str
    content_type: str
    size_bytes: int
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processed_at: datetime
    checksum: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data['processed_at'] = self.processed_at.isoformat()
        data['chunks'] = [chunk.to_dict() for chunk in self.chunks]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedDocument':
        data['processed_at'] = datetime.fromisoformat(data['processed_at'])
        data['chunks'] = [DocumentChunk.from_dict(chunk) for chunk in data['chunks']]
        return cls(**data)


class CodeParser:
    """Parse code files with tree-sitter."""

    def __init__(self):
        self.supported_languages = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rs': 'rust',
            '.go': 'go',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin'
        }

    async def parse_code(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Parse code into semantic chunks."""
        try:
            # Try to import tree-sitter (optional dependency)
            import tree_sitter
            import tree_sitter_python

            # For now, use simple function-based chunking
            # This could be enhanced with actual tree-sitter parsing
            return await self._simple_code_parse(content, language)

        except ImportError:
            logger.warning("tree-sitter not available, using simple parsing")
            return await self._simple_code_parse(content, language)

    async def _simple_code_parse(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Simple code parsing without tree-sitter."""
        chunks = []
        lines = content.split('\n')

        current_chunk = []
        current_function = None
        chunk_start = 0

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Detect function/class definitions
            if language == 'python':
                if line_stripped.startswith(('def ', 'class ', 'async def ')):
                    if current_chunk:
                        chunks.append({
                            'content': '\n'.join(current_chunk),
                            'type': 'code_block',
                            'start_line': chunk_start,
                            'end_line': i - 1,
                            'function': current_function
                        })
                    current_chunk = [line]
                    current_function = line_stripped.split('(')[0].replace('def ', '').replace('class ', '').replace(
                        'async ', '').strip()
                    chunk_start = i
                else:
                    current_chunk.append(line)

            elif language in ['javascript', 'typescript']:
                if any(keyword in line_stripped for keyword in
                       ['function ', 'class ', '=> {', 'const ', 'let ', 'var ']):
                    if current_chunk and len(current_chunk) > 10:  # Only split if chunk is substantial
                        chunks.append({
                            'content': '\n'.join(current_chunk),
                            'type': 'code_block',
                            'start_line': chunk_start,
                            'end_line': i - 1,
                            'function': current_function
                        })
                        current_chunk = [line]
                        chunk_start = i
                    else:
                        current_chunk.append(line)
                else:
                    current_chunk.append(line)

        # Add remaining chunk
        if current_chunk:
            chunks.append({
                'content': '\n'.join(current_chunk),
                'type': 'code_block',
                'start_line': chunk_start,
                'end_line': len(lines) - 1,
                'function': current_function
            })

        return chunks

    def get_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        return self.supported_languages.get(file_path.suffix.lower())


class MarkdownParser:
    """Parse markdown documents."""

    async def parse_markdown(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown into semantic chunks."""
        chunks = []
        lines = content.split('\n')

        current_chunk = []
        current_section = None
        chunk_start = 0
        in_code_block = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Track code blocks
            if line_stripped.startswith('```'):
                in_code_block = not in_code_block

            # Detect headers
            if line_stripped.startswith('#') and not in_code_block:
                if current_chunk:
                    chunks.append({
                        'content': '\n'.join(current_chunk),
                        'type': 'markdown_section',
                        'start_line': chunk_start,
                        'end_line': i - 1,
                        'section': current_section,
                        'has_code': '```' in '\n'.join(current_chunk)
                    })

                current_chunk = [line]
                current_section = line_stripped.lstrip('#').strip()
                chunk_start = i
            else:
                current_chunk.append(line)

        # Add remaining chunk
        if current_chunk:
            chunks.append({
                'content': '\n'.join(current_chunk),
                'type': 'markdown_section',
                'start_line': chunk_start,
                'end_line': len(lines) - 1,
                'section': current_section,
                'has_code': '```' in '\n'.join(current_chunk)
            })

        return chunks


class DocumentProcessor:
    """Main document processing service."""

    def __init__(self):
        self.code_parser = CodeParser()
        self.markdown_parser = MarkdownParser()
        self.documents_dir = Path(settings.database_url).parent / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        # Chunk size settings
        self.max_chunk_size = 1000  # characters
        self.chunk_overlap = 100  # characters

        logger.info("DocumentProcessor initialized")

    @log_performance("process_document")
    async def process_document(self, file_path: Path, content: str = None) -> ProcessedDocument:
        """Process a document into chunks."""
        if content is None:
            content = file_path.read_text(encoding='utf-8')

        # Generate document ID and metadata
        doc_id = str(uuid.uuid4())
        checksum = hashlib.sha256(content.encode()).hexdigest()

        # Detect content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = 'text/plain'

        # Process based on file type
        chunks = await self._process_by_type(file_path, content, doc_id)

        document = ProcessedDocument(
            id=doc_id,
            filename=file_path.name,
            file_path=str(file_path),
            content_type=content_type,
            size_bytes=len(content.encode()),
            chunks=chunks,
            metadata={
                'language': self.code_parser.get_language(file_path),
                'total_chunks': len(chunks),
                'total_characters': len(content),
                'file_extension': file_path.suffix
            },
            processed_at=datetime.now(),
            checksum=checksum
        )

        logger.info(f"Processed document {file_path.name}: {len(chunks)} chunks")
        return document

    async def _process_by_type(self, file_path: Path, content: str, doc_id: str) -> List[DocumentChunk]:
        """Process document based on its type."""
        chunks = []

        # Determine processing strategy
        language = self.code_parser.get_language(file_path)

        if language:
            # Code file
            parsed_chunks = await self.code_parser.parse_code(content, language)

            for i, chunk_data in enumerate(parsed_chunks):
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    content=chunk_data['content'],
                    metadata={
                        'type': chunk_data['type'],
                        'start_line': chunk_data['start_line'],
                        'end_line': chunk_data['end_line'],
                        'function': chunk_data.get('function')
                    },
                    position=i,
                    chunk_type='code',
                    language=language
                )
                chunks.append(chunk)

        elif file_path.suffix.lower() in ['.md', '.markdown']:
            # Markdown file
            parsed_chunks = await self.markdown_parser.parse_markdown(content)

            for i, chunk_data in enumerate(parsed_chunks):
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    content=chunk_data['content'],
                    metadata={
                        'type': chunk_data['type'],
                        'start_line': chunk_data['start_line'],
                        'end_line': chunk_data['end_line'],
                        'section': chunk_data.get('section'),
                        'has_code': chunk_data.get('has_code', False)
                    },
                    position=i,
                    chunk_type='markdown'
                )
                chunks.append(chunk)

        else:
            # Plain text - split into chunks
            text_chunks = self._split_text(content)

            for i, chunk_content in enumerate(text_chunks):
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    content=chunk_content,
                    metadata={'type': 'text_chunk'},
                    position=i,
                    chunk_type='text'
                )
                chunks.append(chunk)

        return chunks

    def _split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.max_chunk_size, len(text))

            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + self.max_chunk_size - 100, start), -1):
                    if text[i] in '.!?\n':
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = max(start + self.max_chunk_size - self.chunk_overlap, end)

        return chunks

    async def process_uploaded_file(self, file_path: Path) -> ProcessedDocument:
        """Process an uploaded file."""
        try:
            # Check file size
            file_size = file_path.stat().st_size
            max_size = 50 * 1024 * 1024  # 50MB limit

            if file_size > max_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")

            # Process the document
            document = await self.process_document(file_path)

            # Save processed document metadata
            await self._save_document_metadata(document)

            return document

        except Exception as e:
            logger.error(f"Failed to process uploaded file {file_path}: {e}")
            raise

    async def _save_document_metadata(self, document: ProcessedDocument):
        """Save document metadata to storage."""
        metadata_file = self.documents_dir / f"{document.id}.json"

        with open(metadata_file, 'w') as f:
            import json
            json.dump(document.to_dict(), f, indent=2)

    async def get_document(self, document_id: str) -> Optional[ProcessedDocument]:
        """Retrieve a processed document."""
        metadata_file = self.documents_dir / f"{document_id}.json"

        if not metadata_file.exists():
            return None

        try:
            import json
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            return ProcessedDocument.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load document {document_id}: {e}")
            return None

    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all processed documents."""
        documents = []

        for metadata_file in self.documents_dir.glob("*.json"):
            try:
                import json
                with open(metadata_file, 'r') as f:
                    data = json.load(f)

                documents.append({
                    'id': data['id'],
                    'filename': data['filename'],
                    'content_type': data['content_type'],
                    'size_bytes': data['size_bytes'],
                    'processed_at': data['processed_at'],
                    'total_chunks': data['metadata']['total_chunks']
                })
            except Exception as e:
                logger.error(f"Failed to load document metadata from {metadata_file}: {e}")

        return sorted(documents, key=lambda x: x['processed_at'], reverse=True)

    async def delete_document(self, document_id: str) -> bool:
        """Delete a processed document."""
        metadata_file = self.documents_dir / f"{document_id}.json"

        if metadata_file.exists():
            metadata_file.unlink()
            logger.info(f"Deleted document {document_id}")
            return True

        return False