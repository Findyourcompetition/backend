from app.models.competitor import CompetitorCreate, CompetitorUpdate, Competitor
from app.database import get_collection
from bson import ObjectId
from typing import List, Optional

async def create_competitor(competitor: CompetitorCreate, user_id: str):
    competitors = get_collection("competitors")
    competitor_dict = competitor.dict()
    competitor_dict["user_id"] = user_id
    result = await competitors.insert_one(competitor_dict)
    created_competitor = await competitors.find_one({"_id": result.inserted_id})
    return Competitor(**created_competitor, id=str(created_competitor["_id"]))

async def insert_competitors(competitors: List[Competitor]):
    competitor_collection = get_collection("competitors")
    for competitor in competitors:
        # Convert the Competitor object to a dictionary
        competitor_dict = competitor.dict(by_alias=True)        
        # Remove the 'id' field if it's None or an empty string
        #if not competitor_dict.get('id'):
        competitor_dict.pop('id', None)
 
        # Use the 'name' as a unique identifier to avoid duplicates
        await competitor_collection.update_one(
            {"name": competitor.name},
            {"$set": competitor_dict},
            upsert=True
        )

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

