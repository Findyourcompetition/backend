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
from app.config import settings
from concurrent.futures import ThreadPoolExecutor

# Initialize logging
logger = logging.getLogger(__name__)

# Global event loop policy
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# Create a global thread pool executor
thread_pool = ThreadPoolExecutor(max_workers=3)

def run_in_executor(func, *args):
    """Run a function in the thread pool"""
    return thread_pool.submit(func, *args).result()

def get_redis_url():
    """Get Redis URL from environment with fallback"""
    redis_url = os.environ.get('REDIS_URL', settings.REDIS_URL)
    if not redis_url:
        raise ValueError("Redis URL not configured")
    return redis_url

def get_celery_config():
    """Get Celery configuration with Redis as broker and backend"""
    try:
        redis_url = get_redis_url()
        logger.info(f"Configuring Celery with Redis URL: {redis_url[:8]}...") # Log only the protocol part
        
        config = {
            'broker_url': redis_url,
            'result_backend': redis_url,
            'broker_connection_retry_on_startup': True,
            'broker_connection_timeout': 30,
            'broker_connection_max_retries': 10,
            'broker_pool_limit': None,
            'task_serializer': 'json',
            'accept_content': ['json'],
            'result_serializer': 'json',
            'timezone': 'UTC',
            'enable_utc': True,
            'worker_max_tasks_per_child': 50,
            'worker_prefetch_multiplier': 1,
            'task_time_limit': 300,
            'task_soft_time_limit': 240,
        }
        
        # Add SSL configuration if using secure Redis
        if redis_url.startswith('rediss://'):
            ssl_settings = {
                'ssl_cert_reqs': ssl.CERT_NONE,
                'ssl_keyfile': None,
                'ssl_certfile': None,
                'ssl_ca_certs': None,
            }
            config['broker_use_ssl'] = ssl_settings
            config['redis_backend_use_ssl'] = ssl_settings
        
        return config
    except Exception as e:
        logger.error(f"Failed to configure Celery: {str(e)}")
        raise

# Initialize Celery app
try:
    celery_app = Celery('competitor_tasks')
    celery_app.config_from_object(get_celery_config())
    logger.info("Celery app initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Celery app: {str(e)}")
    raise

# Add startup task to verify configuration
@celery_app.task(name='verify_config')
def verify_config():
    """Verify Celery configuration is working"""
    return {
        'status': 'ok',
        'broker_type': 'redis',
        'timestamp': datetime.utcnow().isoformat()
    }

# Add error handling for Redis operations
def update_task_status(task_id: str, status: str, result=None, error=None):
    """Update task status in Redis with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    task_data = {
        "status": status,
        "updated_at": str(datetime.utcnow())
    }
    
    if result:
        task_data["result"] = result
    if error:
        task_data["error"] = error
    
    for attempt in range(max_retries):
        try:
            redis_client.set(
                f"task:{task_id}",
                json.dumps(task_data),
                ex=3600  # 1 hour expiration
            )
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to update task status after {max_retries} attempts: {str(e)}")
                raise
            asyncio.sleep(retry_delay * (attempt + 1))

def store_search_results_sync(competitors, search_id):
    """Synchronous version of store_search_results"""
    processed_competitors = []
    competitor_collection = get_collection("competitors")
    
    for competitor in competitors:
        try:
            competitor_dict = competitor.dict(by_alias=True)
            competitor_dict['search_id'] = search_id
            
            if competitor.website:
                try:
                    cached_logo = redis_client.get(f"logo:{competitor.website}")
                    if cached_logo:
                        logo_url = cached_logo.decode() if isinstance(cached_logo, bytes) else cached_logo
                    else:
                        # Synchronous fallback for logo
                        logo_url = run_in_executor(fetch_logo_url, competitor.website)
                    competitor_dict['logo'] = logo_url
                except Exception as e:
                    logger.error(f"Error fetching logo for {competitor.website}: {str(e)}")
                    competitor_dict['logo'] = "default_logo_url"
            else:
                competitor_dict['logo'] = run_in_executor(fetch_logo_url, competitor.website)

            unique_id = str(uuid4())
            competitor_dict['_id'] = unique_id
            
            # Synchronous insert
            competitor_collection.insert_one(competitor_dict)
            processed_competitors.append(competitor_dict)
        except Exception as e:
            logger.error(f"Error processing competitor: {str(e)}")
            continue
    
    return {
        "competitors": processed_competitors,
        "search_id": search_id,
        "total": len(processed_competitors)
    }

@celery_app.task(name='process_competitor_search')
def process_competitor_search(task_type: str, params: dict, task_id: str):
    """Celery task to process competitor searches"""
    search_id = str(uuid4())
    
    try:
        update_task_status(task_id, "processing")
        
        # Run async operations in a dedicated thread
        def run_async_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if task_type == "competitor_search":
                    competitors = loop.run_until_complete(find_competitors_ai(
                        params["business_description"],
                        params["location"]
                    ))
                else:
                    competitors = loop.run_until_complete(lookup_competitor_ai(
                        params["name_or_url"]
                    ))
                return competitors
            finally:
                loop.close()
        
        # Run the async operation in the thread pool
        competitors = run_in_executor(run_async_task)
        
        # Process results synchronously
        result = store_search_results_sync(competitors, search_id)
        update_task_status(task_id, "completed", result=result)
        return result
        
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        update_task_status(task_id, "failed", error=str(e))
        raise
