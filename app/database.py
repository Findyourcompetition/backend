from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import redis.asyncio as aioredis
import redis
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Get Redis URL with fallback for development
def get_redis_url() -> str:
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        # Production Redis URL with SSL parameters
        return redis_url + "?ssl_cert_reqs=none"
    
    # Local development fallback
    return "redis://localhost:6379"

# Initialize Redis clients with error handling
def init_redis_clients() -> tuple[Optional[redis.Redis], Optional[aioredis.Redis]]:
    try:
        redis_url = get_redis_url()
        # Sync Redis client
        sync_client = redis.Redis.from_url(redis_url)
        # Test connection
        sync_client.ping()
        
        # Async Redis client
        async_client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            encoding="utf-8"
        )
        
        logger.info(f"Successfully connected to Redis at {redis_url}")
        return sync_client, async_client
    except Exception as e:
        logger.error(f"Error connecting to Redis: {str(e)}")
        logger.warning("Running without Redis - some features may be limited")
        return None, None

# Initialize MongoDB client
client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.DATABASE_NAME]

# Initialize Redis clients
redis_client, redis_async = init_redis_clients()

async def init_db():
    try:
        # Check MongoDB connection
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Check async Redis connection if available
        if redis_async:
            is_redis_connected = await redis_async.ping()
            if is_redis_connected:
                logger.info("Successfully connected to Redis")
            else:
                logger.warning("Redis ping failed - some features may be limited")
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def get_collection(collection_name: str):
    return db[collection_name]

async def close_db():
    try:
        if redis_async:
            await redis_async.close()
        if redis_client:
            redis_client.close()
        client.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")

# Utility function to check if Redis is available
def is_redis_available() -> bool:
    return redis_client is not None and redis_async is not None
