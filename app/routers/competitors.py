from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import List, Optional
from app.models.competitor import (
    CompetitorCreate,
    CompetitorUpdate,
    Competitor,
    CompetitorList,
    CompetitorSearch,
    CompetitorSearchAi,
    CompetitorInsights,
    SingleCompetitorSearchResult
)
from app.database import redis_client, get_collection
from app.models.user import User
from app.services.auth import get_current_user
from app.services.competitor import (
    create_competitor,
    get_competitors,
    update_competitor,
    delete_competitor,
    search_competitors,
    insert_competitors,
    handle_competitor_search
)
from app.services.ai_insights import (
    generate_competitor_insights,
    find_competitors_ai,
    lookup_competitor_ai,
)
from app.utils.logo_fetcher import (
    update_logo_url,
    fetch_logo_url,
    update_competitor_logo_in_db,
)

router = APIRouter()

@router.post("/", response_model=Competitor)
async def add_competitor(
        competitor: CompetitorCreate, current_user: User = Depends(get_current_user)
):
    return await create_competitor(competitor, current_user.id)

@router.get("/", response_model=List[Competitor])
async def list_competitors(current_user: User = Depends(get_current_user)):
    return await get_competitors(current_user.id)

@router.put("/{competitor_id}", response_model=Competitor)
async def update_competitor_info(
        competitor_id: str,
        competitor: CompetitorUpdate,
        current_user: User = Depends(get_current_user),
):
    updated_competitor = await update_competitor(competitor_id, competitor, current_user.id)
    if not updated_competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return updated_competitor

@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_competitor(
        competitor_id: str, current_user: User = Depends(get_current_user)
):
    deleted = await delete_competitor(competitor_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Competitor not found")

@router.post("/search", response_model=CompetitorList)
async def search_for_competitors(
        search: CompetitorSearch, current_user: User = Depends(get_current_user)
):
    return await search_competitors(search.business_type, search.location)

@router.post("/lookup", response_model=SingleCompetitorSearchResult)
async def lookup_competitor(
        name_or_url: str,
        background_tasks: BackgroundTasks,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=6, ge=1),
        search_id: Optional[str] = None 
):
    competitors, new_search_id = await handle_competitor_search(
        search_function=lookup_competitor_ai,
        search_params=(name_or_url,),
        background_tasks=background_tasks,
        offset=offset,
        limit=limit,
        search_id=search_id
    )
    paginated_competitors = competitors[offset:offset + limit]
    return SingleCompetitorSearchResult(
        competitors=paginated_competitors,
        total=len(competitors),
        offset=offset,
        limit=limit,
        search_id=new_search_id
    )

@router.post("/find", response_model=CompetitorList)
async def find_competitors_with_ai(
        find: CompetitorSearchAi,
        background_tasks: BackgroundTasks,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=6, ge=1),
        search_id: Optional[str] = None
):
    competitors, new_search_id = await handle_competitor_search(
        search_function=find_competitors_ai,
        search_params=(find.business_description, find.location),
        background_tasks=background_tasks,
        offset=offset,
        limit=limit,
        search_id=search_id
    )

    paginated_competitors = competitors[offset:offset + limit]
    
    return CompetitorList(
        competitors=paginated_competitors,
        total=len(competitors),
        offset=offset,
        limit=limit,
        search_id=new_search_id
    )

@router.get("/competitors/logos")
async def get_competitors_with_logos(
        search_id: str = Query(..., description="The search ID to fetch competitors for")
):
    competitors_collection = get_collection("competitors")
    competitors = await competitors_collection.find(
        {"search_id": search_id}
    ).to_list(None)
    
    if not competitors:
        raise HTTPException(
            status_code=404,
            detail=f"No competitors found for search_id: {search_id}"
        )
    
    # Update logos from Redis if available
    for competitor in competitors:
        if competitor.get('website'):
            cached_logo = redis_client.get(f"logo:{competitor['website']}")
            if cached_logo:
                logo_url = cached_logo.decode('utf-8')
                if competitor.get('logo') != logo_url:
                    competitor['logo'] = logo_url
                    # Update in database
                    await competitors_collection.update_one(
                        {"_id": competitor["_id"]},
                        {"$set": {"logo": logo_url}}
                    )

    return {"total": len(competitors), "competitors": competitors}


@router.get("/{competitor_id}/insights", response_model=CompetitorInsights)
async def get_competitor_insights(
        competitor_id: str, current_user: User = Depends(get_current_user)
):
    competitor = await get_competitors(current_user.id, competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    insights = await generate_competitor_insights(competitor)
    return CompetitorInsights(competitor_id=competitor_id, insights=insights)
