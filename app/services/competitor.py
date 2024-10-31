from app.models.competitor import CompetitorCreate, CompetitorUpdate, Competitor, CompetitorList, CompetitorBaseList, SingleCompetitorSearchResult, SingleCompetitorSearch
from fastapi import BackgroundTasks
from app.database import get_collection, redis_client
from bson import ObjectId
from typing import List, Optional, Callable, Any, Union
from uuid import uuid4
from app.utils.logo_fetcher import update_logo_url
from app.services.ai_insights import (
    find_competitors_ai,              
    lookup_competitor_ai,             
)


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


async def check_existing_search(
    competitor_collection, search_id: str, offset: int, limit: int, search_function: Optional[Callable]
) -> CompetitorList | SingleCompetitorSearchResult:
    existing_competitors = await competitor_collection.find(
        {"search_id": search_id}
    ).to_list(12)

    if existing_competitors:
        total = len(existing_competitors)

        # Convert MongoDB docs to Competitor objects
        competitors = [
            SingleCompetitorSearch(**doc) if 'countries' in doc else Competitor(**doc)
            for doc in existing_competitors
        ]

    if search_function == lookup_competitor_ai:
        return SingleCompetitorSearchResult(
            competitors=competitors,
            total=len(competitors),
            offset=offset,
            limit=limit,
            search_id=search_id
        )
    else:
        return CompetitorList(
            competitors=competitors,
            total=len(competitors),
            offset=offset,
            limit=limit,
            search_id=search_id
        )
    return CompetitorList(competitors=[], total=0, offset=offset, limit=limit, search_id=search_id)


async def store_search_and_cache_logo(all_competitors: CompetitorList | SingleCompetitorSearchResult, background_tasks: BackgroundTasks, competitor_collection) -> str:
    new_search_id = str(uuid4()) 
    for competitor in all_competitors:
        competitor_dict = competitor.dict(by_alias=True)
        competitor_dict['search_id'] = new_search_id

        cached_logo = redis_client.get(f"logo:{competitor.website}")
        if cached_logo:
            competitor_dict['logo'] = cached_logo.decode('utf-8')
        else:
            competitor_dict['logo'] = "/placeholder-logo.png"
            background_tasks.add_task(update_logo_url, competitor)

        unique_id = str(uuid4())
        competitor_dict['_id'] = unique_id
        competitor_dict['id'] = unique_id
        await competitor_collection.update_one(
            {"name": competitor.name, "search_id": new_search_id},
            {"$set": competitor_dict},
            upsert=True
        )
    return new_search_id

async def handle_competitor_search(
        search_function: Callable,
        search_params: Any,
        background_tasks: BackgroundTasks,
        offset: int = 0,
        limit: int = 6,
        search_id: Optional[str] = None,
) -> tuple[List[dict], Optional[str]]:
    """
    Base function to handle competitor searches with shared logic
    
    Args:
        search_function: The specific search function to use (lookup_competitor_ai or find_competitors_ai)
        search_params: Parameters to pass to the search function
        background_tasks: FastAPI BackgroundTasks
        offset: Pagination offset
        limit: Pagination limit
        search_id: Optional ID for existing searches
        
    Returns:
        tuple: (list of competitors, search_id)
    """
    competitor_collection = get_collection("competitors")
    if search_id:
        existing_result = await check_existing_search(
            competitor_collection,
            search_id, 
            offset, 
            limit,
            search_function
        )
        return existing_result.competitors, existing_result.search_id
    all_competitors = await search_function(*search_params)
    new_search_id = await store_search_and_cache_logo(
        all_competitors, 
        background_tasks, 
        competitor_collection
    )
    competitors_from_db = await insert_competitors(all_competitors)
    
    return all_competitors, new_search_id

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

