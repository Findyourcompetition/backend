from app.models.competitor import CompetitorCreate, CompetitorUpdate, Competitor, CompetitorList, CompetitorBaseList, SingleCompetitorSearchResult, SingleCompetitorSearch
from fastapi import BackgroundTasks
from app.database import get_collection, redis_client
from bson import ObjectId
from typing import List, Optional, Callable, Any, Union
from uuid import uuid4
from app.services.ai_insights import (
    find_competitors_ai,              
    lookup_competitor_ai,             
)
from app.services.background_tasks import TaskStatus


async def create_competitor(competitor: CompetitorCreate, user_id: str):
    competitors = get_collection("competitors")
    competitor_dict = competitor.dict()
    competitor_dict["user_id"] = user_id
    result = await competitors.insert_one(competitor_dict)
    created_competitor = await competitors.find_one({"_id": result.inserted_id})
    return Competitor(**created_competitor, id=str(created_competitor["_id"]))

async def insert_competitors(competitors: CompetitorList):
    competitor_collection = get_collection("competitors")

    for competitor in competitors:
        competitor_dict = competitor.dict(by_alias=True)
        await competitor_collection.update_one(
            {"name": competitor.name},
            {"$set": competitor_dict},
            upsert=True
        )
        # Get all competitors in a single query
    names = [competitor.name for competitor in competitors]
    cursor = competitor_collection.find({"name": {"$in": names}})
    
    inserted_competitors = []
    async for doc in cursor:
        inserted_competitors.append(Competitor(**doc))
        
    return inserted_competitors

async def get_existing_search_results(search_id: str, offset: int, limit: int):
    """Helper function to get existing search results"""
    competitor_collection = get_collection("competitors")
    competitors = await competitor_collection.find(
        {"search_id": search_id}
    ).to_list(None)
    
    if not competitors:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for search_id: {search_id}"
        )
    
    total = len(competitors)
    paginated = competitors[offset:offset + limit]
    
    return {
        "competitors": paginated,
        "total": total,
        "offset": offset,
        "limit": limit,
        "search_id": search_id,
        "status": TaskStatus.COMPLETED
    }

async def get_competitors(user_id: str, competitor_id: Optional[str] = None):
    competitors = get_collection("competitors")
    query = {"user_id": user_id}
    if competitor_id:
        query["_id"] = ObjectId(competitor_id)
        competitor = await competitors.find_one(query)
        return Competitor(**competitor, id=str(competitor["_id"])) if competitor else None
    else:
        cursor = competitors.find(query)
        return [Competitor(**comp, id=str(comp["_id"])) async for comp in cursor]

async def update_competitor(competitor_id: str, competitor: CompetitorUpdate, user_id: str):
    competitors = get_collection("competitors")
    result = await competitors.update_one(
        {"_id": ObjectId(competitor_id), "user_id": user_id},
        {"$set": competitor.dict(exclude_unset=True)}
    )
    if result.modified_count:
        updated_competitor = await competitors.find_one({"_id": ObjectId(competitor_id)})
        return Competitor(**updated_competitor, id=str(updated_competitor["_id"]))
    return None

async def delete_competitor(competitor_id: str, user_id: str):
    competitors = get_collection("competitors")
    result = await competitors.delete_one({"_id": ObjectId(competitor_id), "user_id": user_id})
    return result.deleted_count > 0

async def search_competitors(business_type: str, location: str) -> List[Competitor]:
    competitors = get_collection("competitors")
    query = {
        "business_type": {"$regex": business_type, "$options": "i"},
        "location": {"$regex": location, "$options": "i"}
    }
    cursor = competitors.find(query)
    return [Competitor(**comp, id=str(comp["_id"])) async for comp in cursor]

