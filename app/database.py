from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import redis.asyncio as aioredis
import redis
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_redis_ssl_config(url: str) -> dict:
    """Get Redis SSL configuration based on URL"""
    if url.startswith('rediss://'):
        return {
            'ssl_cert_reqs': None,  # CERT_NONE
            'ssl': True
        }
    return {}

# Initialize Redis clients with SSL support
redis_url = settings.REDIS_URL
ssl_config = get_redis_ssl_config(redis_url)

# Sync Redis client
redis_client = redis.from_url(redis_url, **ssl_config)

# Async Redis client
redis_async = aioredis.from_url(
    redis_url,
    decode_responses=True,
    encoding="utf-8",
    **ssl_config
)

# Initialize MongoDB client
client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.DATABASE_NAME]

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
