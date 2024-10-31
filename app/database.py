# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import redis.asyncio as aioredis
import redis
import os
import logging

logger = logging.getLogger(__name__)

# Get the Redis URL and append SSL parameters for secure connection
redis_url = os.environ["REDIS_URL"]

# Sync Redis client
redis_client = redis.Redis.from_url(redis_url + "?ssl_cert_reqs=none")

# Async Redis client
redis_async = aioredis.from_url(redis_url + "?ssl_cert_reqs=none", decode_responses=True, encoding="utf-8")


# Existing MongoDB setup
client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.DATABASE_NAME]

async def init_db():
    try:
        # Check MongoDB connection
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Check async Redis connection
        is_redis_connected = await redis_async.ping()
        if is_redis_connected:
            logger.info("Successfully connected to Redis")
        else:
            raise Exception("Redis ping failed")
            
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def get_collection(collection_name: str):
    return db[collection_name]

# Add cleanup function
async def close_db():
    try:
        await redis_async.close()
        client.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")
