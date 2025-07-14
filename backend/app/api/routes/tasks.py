# backend/app/api/routes/tasks.py

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...services.background_tasks import BackgroundTaskManager, TaskResult, get_task_manager


# Dependency placeholder - will be overridden in main.py
async def get_background_task_manager():
    raise NotImplementedError


# Response Models
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: dict


class TaskListResponse(BaseModel):
    tasks: List[TaskStatusResponse]
    total_count: int
    running_count: int
    completed_count: int
    failed_count: int


# Router
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
        status: Optional[str] = None,
        task_manager: BackgroundTaskManager = Depends(get_background_task_manager)
):
    """List all background tasks, optionally filtered by status."""
    try:
        tasks = task_manager.get_all_tasks(status_filter=status)

        # Convert to response format
        task_responses = []
        for task in tasks:
            task_data = task.to_dict()
            task_responses.append(TaskStatusResponse(**task_data))

        # Calculate counts
        all_tasks = task_manager.get_all_tasks()
        counts = {
            'total_count': len(all_tasks),
            'running_count': len([t for t in all_tasks if t.status == 'running']),
            'completed_count': len([t for t in all_tasks if t.status == 'completed']),
            'failed_count': len([t for t in all_tasks if t.status == 'failed'])
        }

        return TaskListResponse(
            tasks=task_responses,
            **counts
        )

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tasks")


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
        task_id: str,
        task_manager: BackgroundTaskManager = Depends(get_background_task_manager)
):
    """Get status of a specific background task."""
    try:
        task = task_manager.get_task_status(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task_data = task.to_dict()
        return TaskStatusResponse(**task_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.post("/{task_id}/cancel")
async def cancel_task(
        task_id: str,
        task_manager: BackgroundTaskManager = Depends(get_background_task_manager)
):
    """Cancel a running background task."""
    try:
        success = await task_manager.cancel_task(task_id)

        if not success:
            raise HTTPException(status_code=404, detail="Task not found or not running")

        return {"message": f"Task {task_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.get("/stats/summary")
async def get_task_stats(
        task_manager: BackgroundTaskManager = Depends(get_background_task_manager)
):
    """Get background task statistics."""
    try:
        all_tasks = task_manager.get_all_tasks()

        stats = {
            'total_tasks': len(all_tasks),
            'by_status': {},
            'by_type': {},
            'running_tasks': len(task_manager.running_tasks),
            'max_concurrent': task_manager.max_concurrent_tasks
        }

        # Count by status
        for task in all_tasks:
            status = task.status
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1

        # Count by type
        for task in all_tasks:
            task_type = task.metadata.get('type', 'unknown')
            stats['by_type'][task_type] = stats['by_type'].get(task_type, 0) + 1

        return stats

    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task stats")

# backend/app/utils/__init__.py