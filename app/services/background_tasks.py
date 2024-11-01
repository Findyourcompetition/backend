from typing import Dict, Any, Optional
import json
from datetime import datetime
from uuid import uuid4
from app.database import redis_client
from app.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

class TaskStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

async def create_background_task(task_type: str, params: Dict[Any, Any]) -> str:
    """Create a new background task and return its ID."""
    task_id = str(uuid4())
    
    # Store initial task status in Redis
    task_data = {
        "id": task_id,
        "type": task_type,
        "status": TaskStatus.PENDING,
        "created_at": str(datetime.utcnow()),
    }
    
    redis_client.set(
        f"task:{task_id}",
        json.dumps(task_data),
        ex=3600  # 1 hour expiration
    )
    
    # Launch Celery task with the simplified task name
    celery_app.send_task(
        'process_competitor_search',
        args=[task_type, params, task_id],
        task_id=task_id
    )
    
    return task_id

async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status of a task."""
    task_data = redis_client.get(f"task:{task_id}")
    if not task_data:
        return None
    return json.loads(task_data)
