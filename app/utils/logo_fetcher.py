import aiohttp
from bson import ObjectId
import logging
from app.database import redis_client, get_collection
from app.models.competitor import Competitor

logger = logging.getLogger(__name__)

async def fetch_logo_url(domain: str) -> str:
    """Fetch logo URL for a single domain."""
    try:
        # Try Clearbit first
        clearbit_url = f"https://logo.clearbit.com/{domain}"
        async with aiohttp.ClientSession() as session:
            async with session.get(clearbit_url) as response:
                if response.status == 200:
                    return clearbit_url
                
        # Fallback to Google Favicon
        return f"https://www.google.com/s2/favicons?domain={domain}"
    except Exception as e:
        logger.error(f"Error fetching logo for domain {domain}: {str(e)}")
        return "/placeholder-logo.png"

async def update_competitor_logo_in_db(competitor_id: str, logo_url: str):
    """Helper function to update logo in database"""
    try:
        competitors_collection = get_collection("competitors")
        await competitors_collection.update_one(
            {"_id": ObjectId(competitor_id)},
            {"$set": {"logo": logo_url}}
        )
    except Exception as e:
        logger.error(f"Error updating logo in database: {str(e)}")
