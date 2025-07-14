# backend/app/utils/helpers.py

import asyncio
import hashlib
import mimetypes
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from datetime import datetime, timedelta
import json

from loguru import logger


def calculate_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
    """Calculate hash of a file."""
    hash_obj = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def calculate_string_hash(content: str, algorithm: str = 'sha256') -> str:
    """Calculate hash of a string."""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()


def detect_content_type(file_path: Path) -> str:
    """Detect MIME type of a file."""
    content_type, _ = mimetypes.guess_type(str(file_path))

    if not content_type:
        # Fallback based on extension
        extension_map = {
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.ts': 'text/typescript',
            '.jsx': 'text/jsx',
            '.tsx': 'text/tsx',
            '.md': 'text/markdown',
            '.yaml': 'text/yaml',
            '.yml': 'text/yaml',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        content_type = extension_map.get(file_path.suffix.lower(), 'text/plain')

    return content_type


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)

    # Trim and ensure it's not empty
    filename = filename.strip('_. ')

    if not filename:
        filename = 'unnamed_file'

    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        max_name_length = 255 - len(ext)
        filename = name[:max_name_length] + ext

    return filename


def format_bytes(bytes_value: int) -> str:
    """Format bytes in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def validate_model_name(model_name: str) -> bool:
    """Validate model name format."""
    # Allow alphanumeric, hyphens, underscores, and dots
    pattern = r'^[a-zA-Z0-9._-]+$'
    return bool(re.match(pattern, model_name)) and len(model_name) <= 100


def validate_conversation_id(conversation_id: str) -> bool:
    """Validate conversation ID format (UUID)."""
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, conversation_id.lower()))


def extract_code_blocks(content: str) -> List[Dict[str, str]]:
    """Extract code blocks from markdown-like content."""
    code_block_pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(code_block_pattern, content, re.DOTALL)

    code_blocks = []
    for language, code in matches:
        code_blocks.append({
            'language': language or 'text',
            'code': code.strip()
        })

    return code_blocks


def clean_text_content(content: str) -> str:
    """Clean and normalize text content."""
    # Remove excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r' {2,}', ' ', content)

    # Remove trailing whitespace from lines
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)

    return content.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def split_text_into_sentences(text: str) -> List[str]:
    """Split text into sentences (basic implementation)."""
    # Simple sentence splitting - could be improved with proper NLP
    sentence_endings = r'[.!?]'
    sentences = re.split(sentence_endings, text)

    # Clean and filter sentences
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in minutes."""
    word_count = len(text.split())
    reading_time = max(1, round(word_count / words_per_minute))
    return reading_time


def is_code_content(content: str) -> bool:
    """Heuristically detect if content is code."""
    code_indicators = [
        'def ', 'function ', 'class ', 'import ', 'from ',
        '{', '}', ';', '//', '/*', '*/', '#!/',
        'if (', 'for (', 'while (', 'return ', 'var ', 'let ', 'const '
    ]

    # Count indicators
    indicator_count = sum(1 for indicator in code_indicators if indicator in content)

    # Simple heuristic: if multiple indicators present
    return indicator_count >= 3


class RateLimiter:
    """Simple rate limiter for API endpoints."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for given identifier."""
        now = time.time()

        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window_seconds
            ]
        else:
            self.requests[identifier] = []

        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True

        return False

    def get_reset_time(self, identifier: str) -> Optional[float]:
        """Get time when rate limit resets for identifier."""
        if identifier not in self.requests or not self.requests[identifier]:
            return None

        oldest_request = min(self.requests[identifier])
        return oldest_request + self.window_seconds


class SimpleCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, default_ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check if expired
        if time.time() > entry['expires_at']:
            del self.cache[key]
            return None

        return entry['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        if ttl is None:
            ttl = self.default_ttl

        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        now = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now > entry['expires_at']
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)


async def async_retry(
        func,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
):
    """Retry an async function with exponential backoff."""
    last_exception = None

    for attempt in range(max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except exceptions as e:
            last_exception = e

            if attempt == max_attempts - 1:
                break

            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay *= backoff

    raise last_exception


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size."""
    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i:i + chunk_size])
    return chunks


async def async_chunk_processor(
        items: List[Any],
        processor_func,
        chunk_size: int = 10,
        max_concurrent: int = 3
) -> List[Any]:
    """Process items in chunks with concurrency control."""
    chunks = chunk_list(items, chunk_size)

    async def process_chunk(chunk):
        results = []
        for item in chunk:
            if asyncio.iscoroutinefunction(processor_func):
                result = await processor_func(item)
            else:
                result = processor_func(item)
            results.append(result)
        return results

    # Process chunks with concurrency limit
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_chunk_with_semaphore(chunk):
        async with semaphore:
            return await process_chunk(chunk)

    chunk_results = await asyncio.gather(*[
        process_chunk_with_semaphore(chunk) for chunk in chunks
    ])

    # Flatten results
    results = []
    for chunk_result in chunk_results:
        results.extend(chunk_result)

    return results


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely parse JSON string with default fallback."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "null") -> str:
    """Safely serialize object to JSON with default fallback."""
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError):
        return default


# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance."""

    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.debug(f"{func.__name__} took {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
            raise

    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.debug(f"{func.__name__} took {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper