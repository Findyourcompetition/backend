import os
from celery import Celery
import asyncio
from datetime import datetime
import json
from uuid import uuid4
import logging
from app.services.ai_insights import find_competitors_ai, lookup_competitor_ai
from app.database import redis_client, get_collection
from app.utils.logo_fetcher import fetch_logo_url
import ssl
from urllib.parse import urlparse

# Initialize logging
logger = logging.getLogger(__name__)

def get_redis_config():
    """Configure Redis connection with SSL if needed"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    if redis_url.startswith('rediss://'):
        # Parse the Redis URL
        parsed_url = urlparse(redis_url)
        
        # Configure broker URL with SSL parameters
        broker_url = f"{redis_url}?ssl_cert_reqs=CERT_NONE"
        
        # Configure Celery Redis backend settings
        backend_settings = {
            'redis_backend_use_ssl': {
                'ssl_cert_reqs': ssl.CERT_NONE
            }
        }
        
        return broker_url, backend_settings
    
    return redis_url, {}

# Get Redis configuration
broker_url, backend_settings = get_redis_config()

# Initialize Celery
celery_app = Celery('competitor_tasks')

# Configure Celery
config = {
    'broker_url': broker_url,
    'result_backend': broker_url,
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'broker_connection_retry_on_startup': True,
}

# Update with SSL settings if needed
config.update(backend_settings)
celery_app.conf.update(config)

def update_task_status(task_id: str, status: str, result=None, error=None):
    """Update task status in Redis"""
    task_data = {
        "status": status,
        "updated_at": str(datetime.utcnow())
    }
    
    if result:
        task_data["result"] = result
    if error:
        task_data["error"] = error
        
    redis_client.set(
        f"task:{task_id}",
        json.dumps(task_data),
        ex=3600  # 1 hour expiration
    )

async def store_search_results(competitors, search_id):
    """Store search results with logos"""
    processed_competitors = []
    competitor_collection = get_collection("competitors")
    
    for competitor in competitors:
        competitor_dict = competitor.dict(by_alias=True)
        competitor_dict['search_id'] = search_id
        
        # Handle logo
        if competitor.website:
            try:
                cached_logo = redis_client.get(f"logo:{competitor.website}")
                if cached_logo:
                    logo_url = cached_logo.decode('utf-8')
                else:
                    logo_url = await fetch_logo_url(competitor.website)
                    redis_client.set(f"logo:{competitor.website}", logo_url, ex=86400)
                competitor_dict['logo'] = logo_url
            except Exception as e:
                logger.error(f"Error fetching logo: {str(e)}")
                competitor_dict['logo'] = "/placeholder-logo.png"
        else:
            competitor_dict['logo'] = "/placeholder-logo.png"

        # Store in database
        unique_id = str(uuid4())
        competitor_dict['_id'] = unique_id
        
        await competitor_collection.update_one(
            {"name": competitor.name, "search_id": search_id},
            {"$set": competitor_dict},
            upsert=True
        )
        processed_competitors.append(competitor_dict)
    
    return {
        "competitors": processed_competitors,
        "search_id": search_id,
        "total": len(processed_competitors)
    }

async def _process_search(task_type: str, params: dict, task_id: str):
    """Async helper function to process the search"""
    search_id = str(uuid4())
    
    try:
        # Update task status to processing
        update_task_status(task_id, "processing")
        
        # Perform the search
        if task_type == "competitor_search":
            competitors = await find_competitors_ai(
                params["business_description"],
                params["location"]
            )
        else:  # lookup
            competitors = await lookup_competitor_ai(
                params["name_or_url"]
            )

        # Process and store results
        result = await store_search_results(competitors, search_id)
        
        # Update task status
        update_task_status(task_id, "completed", result=result)
        return result
        
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        update_task_status(task_id, "failed", error=str(e))
        raise

@celery_app.task(name='process_competitor_search')
def process_competitor_search(task_type: str, params: dict, task_id: str):
    """Celery task to process competitor searches"""
    try:
        # Create new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_process_search(task_type, params, task_id))
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        update_task_status(task_id, "failed", error=str(exc))
        raise
