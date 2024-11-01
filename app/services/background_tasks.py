from typing import Dict, Any, Optional
import json
from datetime import datetime
from uuid import uuid4
from app.database import redis_client
from app.celery_app import celery_app
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class TaskStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

def get_redis_url_with_ssl():
    """Get Redis URL with SSL parameters if needed"""
    redis_url = settings.REDIS_URL
    if redis_url.startswith('rediss://'):
        return f"{redis_url}?ssl_cert_reqs=CERT_NONE"
    return redis_url

async def create_background_task(task_type: str, params: Dict[Any, Any]) -> str:
    """Create a new background task and return its ID."""
    try:
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
        
        # Launch Celery task
        celery_app.send_task(
            'process_competitor_search',
            args=[task_type, params, task_id],
            task_id=task_id
        )
        
        return task_id
    except Exception as e:
        logger.error(f"Error creating background task: {str(e)}")
        raise

async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status of a task."""
    try:
        task_data = redis_client.get(f"task:{task_id}")
        if not task_data:
            return None
        return json.loads(task_data)
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return None
