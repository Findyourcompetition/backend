import aiohttp
from bson import ObjectId
from app.database import redis_client 
from app.models.competitor import Competitor
from app.database import get_collection

async def fetch_logo_url(domain: str) -> str:
    # Try Clearbit first
    clearbit_url = f"https://logo.clearbit.com/{domain}"
    async with aiohttp.ClientSession() as session:
        async with session.get(clearbit_url) as response:
            if response.status == 200:
                return clearbit_url
            
    # Fallback to Google Favicon
    return f"https://www.google.com/s2/favicons?domain={domain}"

async def update_logo_url(competitor: Competitor):
    logo_url = await fetch_logo_url(competitor.website)
    competitor.logo = logo_url
    # Cache the result
    redis_client.set(f"logo:{competitor.website}", logo_url, ex=86400)  # Cache for 24 hours

async def update_competitor_logo_in_db(competitor_id: str, logo_url: str):
    """Helper function to update logo in database"""
    competitors_collection = get_collection("competitors")
    await competitors_collection.update_one(
        {"_id": ObjectId(competitor_id)},
        {"$set": {"logo": logo_url}}
    )
