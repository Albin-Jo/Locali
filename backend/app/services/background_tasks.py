# backend/app/services/background_tasks.py

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from pathlib import Path

from loguru import logger
from ..core.logging import log_performance


@dataclass
class TaskResult:
    """Represents the result of a background task."""
    task_id: str
    status: str  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        data = asdict(self)
        for field in ['created_at', 'started_at', 'completed_at']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data


class BackgroundTaskManager:
    """Manages background tasks with progress tracking."""

    def __init__(self, max_concurrent_tasks: int = 5, task_retention_hours: int = 24):
        self.tasks: Dict[str, TaskResult] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_retention_hours = task_retention_hours

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_old_tasks())

        logger.info(f"BackgroundTaskManager initialized (max concurrent: {max_concurrent_tasks})")

    async def submit_task(
            self,
            coro_func: Callable,
            task_name: str = None,
            metadata: Dict[str, Any] = None,
            *args,
            **kwargs
    ) -> str:
        """Submit a coroutine function as a background task."""
        task_id = str(uuid.uuid4())

        # Create task result
        task_result = TaskResult(
            task_id=task_id,
            status='pending',
            metadata={'name': task_name or 'unknown', **(metadata or {})}
        )

        self.tasks[task_id] = task_result

        # Check if we can start the task immediately
        if len(self.running_tasks) < self.max_concurrent_tasks:
            await self._start_task(task_id, coro_func, args, kwargs)
        else:
            logger.info(f"Task {task_id} queued (max concurrent tasks reached)")

        return task_id

    async def _start_task(self, task_id: str, coro_func: Callable, args: tuple, kwargs: dict):
        """Start executing a background task."""
        task_result = self.tasks[task_id]
        task_result.status = 'running'
        task_result.started_at = datetime.now()

        # Create and start the asyncio task
        async_task = asyncio.create_task(
            self._execute_task(task_id, coro_func, args, kwargs)
        )

        self.running_tasks[task_id] = async_task

        logger.info(f"Started background task {task_id}: {task_result.metadata.get('name')}")

    async def _execute_task(self, task_id: str, coro_func: Callable, args: tuple, kwargs: dict):
        """Execute a background task with error handling."""
        task_result = self.tasks[task_id]

        try:
            # Execute the coroutine
            if asyncio.iscoroutinefunction(coro_func):
                result = await coro_func(*args, **kwargs)
            else:
                # Run in thread pool if not async
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, coro_func, *args, **kwargs)

            # Task completed successfully
            task_result.status = 'completed'
            task_result.result = result
            task_result.progress = 1.0
            task_result.completed_at = datetime.now()

            logger.info(f"Background task {task_id} completed successfully")

        except asyncio.CancelledError:
            task_result.status = 'cancelled'
            task_result.completed_at = datetime.now()
            logger.info(f"Background task {task_id} was cancelled")

        except Exception as e:
            task_result.status = 'failed'
            task_result.error = str(e)
            task_result.completed_at = datetime.now()
            logger.error(f"Background task {task_id} failed: {e}")

        finally:
            # Remove from running tasks
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

            # Start next queued task if any
            await self._start_next_queued_task()

    async def _start_next_queued_task(self):
        """Start the next queued task if there's capacity."""
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            return

        # Find next pending task
        for task_id, task_result in self.tasks.items():
            if task_result.status == 'pending':
                # We need to store the original function and args somehow
                # For now, this is a simplified implementation
                break

    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get status of a background task."""
        return self.tasks.get(task_id)

    def get_all_tasks(self, status_filter: str = None) -> List[TaskResult]:
        """Get all tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())

        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]

        return sorted(tasks, key=lambda x: x.created_at, reverse=True)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running background task."""
        if task_id in self.running_tasks:
            async_task = self.running_tasks[task_id]
            async_task.cancel()

            # Update task status
            if task_id in self.tasks:
                self.tasks[task_id].status = 'cancelled'
                self.tasks[task_id].completed_at = datetime.now()

            logger.info(f"Cancelled background task {task_id}")
            return True

        return False

    async def _cleanup_old_tasks(self):
        """Periodically clean up old completed tasks."""
        while True:
            try:
                cutoff_time = datetime.now() - timedelta(hours=self.task_retention_hours)

                tasks_to_remove = [
                    task_id for task_id, task_result in self.tasks.items()
                    if (task_result.completed_at and task_result.completed_at < cutoff_time and
                        task_result.status in ['completed', 'failed', 'cancelled'])
                ]

                for task_id in tasks_to_remove:
                    del self.tasks[task_id]
                    logger.debug(f"Cleaned up old task {task_id}")

                if tasks_to_remove:
                    logger.info(f"Cleaned up {len(tasks_to_remove)} old background tasks")

                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Error in background task cleanup: {e}")
                await asyncio.sleep(3600)

    async def shutdown(self):
        """Shutdown the task manager and cancel all running tasks."""
        logger.info("Shutting down BackgroundTaskManager...")

        # Cancel cleanup task
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()

        # Cancel all running tasks
        for task_id, async_task in self.running_tasks.items():
            async_task.cancel()
            if task_id in self.tasks:
                self.tasks[task_id].status = 'cancelled'

        # Wait for tasks to complete cancellation
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        logger.info("BackgroundTaskManager shutdown complete")


class DocumentProcessingTasks:
    """Specialized background tasks for document processing."""

    def __init__(self, task_manager: BackgroundTaskManager):
        self.task_manager = task_manager

    async def process_document_async(
            self,
            document_processor,
            search_service,
            file_path: Path,
            content: str = None
    ) -> str:
        """Process a document in the background."""

        async def process_task():
            # Process document
            document = await document_processor.process_document(file_path, content)

            # Index for search
            await search_service.index_document(document)

            return {
                'document_id': document.id,
                'filename': document.filename,
                'chunks': len(document.chunks),
                'size_bytes': document.size_bytes
            }

        return await self.task_manager.submit_task(
            process_task,
            task_name=f"process_document_{file_path.name}",
            metadata={'filename': file_path.name, 'type': 'document_processing'}
        )

    async def batch_process_documents(
            self,
            document_processor,
            search_service,
            file_paths: List[Path]
    ) -> str:
        """Process multiple documents in the background."""

        async def batch_process_task():
            results = []

            for i, file_path in enumerate(file_paths):
                try:
                    # Process document
                    document = await document_processor.process_document(file_path)

                    # Index for search
                    await search_service.index_document(document)

                    results.append({
                        'success': True,
                        'document_id': document.id,
                        'filename': document.filename,
                        'chunks': len(document.chunks)
                    })

                    # Update progress
                    progress = (i + 1) / len(file_paths)
                    # Note: Would need to implement progress callback in task manager

                except Exception as e:
                    results.append({
                        'success': False,
                        'filename': file_path.name,
                        'error': str(e)
                    })

            return {
                'total_files': len(file_paths),
                'successful': sum(1 for r in results if r['success']),
                'failed': sum(1 for r in results if not r['success']),
                'results': results
            }

        return await self.task_manager.submit_task(
            batch_process_task,
            task_name=f"batch_process_{len(file_paths)}_documents",
            metadata={'file_count': len(file_paths), 'type': 'batch_document_processing'}
        )


class ModelManagementTasks:
    """Specialized background tasks for model management."""

    def __init__(self, task_manager: BackgroundTaskManager):
        self.task_manager = task_manager

    async def download_model_async(
            self,
            download_manager,
            model_name: str
    ) -> str:
        """Download a model in the background."""

        async def download_task():
            results = []

            async for progress in download_manager.download_model(model_name):
                results.append(progress)

                # Update task progress based on download progress
                if 'progress' in progress:
                    download_progress = progress['progress'].get('progress_percent', 0)
                    # Note: Would need progress callback in task manager

            return {
                'model_name': model_name,
                'status': results[-1]['status'] if results else 'unknown',
                'download_steps': len(results)
            }

        return await self.task_manager.submit_task(
            download_task,
            task_name=f"download_model_{model_name}",
            metadata={'model_name': model_name, 'type': 'model_download'}
        )

    async def model_benchmark_async(
            self,
            model_manager,
            model_name: str,
            test_prompts: List[str]
    ) -> str:
        """Benchmark a model in the background."""

        async def benchmark_task():
            results = []

            # Load model if not loaded
            if model_manager.current_model != model_name:
                await model_manager.load_model(model_name)

            for prompt in test_prompts:
                start_time = asyncio.get_event_loop().time()

                response = ""
                async for token in model_manager.generate_stream(prompt, max_tokens=100):
                    response += token

                end_time = asyncio.get_event_loop().time()

                results.append({
                    'prompt': prompt[:50] + "..." if len(prompt) > 50 else prompt,
                    'response_length': len(response),
                    'generation_time': end_time - start_time,
                    'tokens_per_second': len(response.split()) / (end_time - start_time)
                })

            avg_tokens_per_sec = sum(r['tokens_per_second'] for r in results) / len(results)

            return {
                'model_name': model_name,
                'test_count': len(test_prompts),
                'average_tokens_per_second': avg_tokens_per_sec,
                'results': results
            }

        return await self.task_manager.submit_task(
            benchmark_task,
            task_name=f"benchmark_model_{model_name}",
            metadata={'model_name': model_name, 'type': 'model_benchmark'}
        )


# Global task manager instance
task_manager: Optional[BackgroundTaskManager] = None


async def get_task_manager() -> BackgroundTaskManager:
    """Get or create the global task manager."""
    global task_manager

    if task_manager is None:
        task_manager = BackgroundTaskManager()

    return task_manager


async def shutdown_task_manager():
    """Shutdown the global task manager."""
    global task_manager

    if task_manager:
        await task_manager.shutdown()
        task_manager = None