from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.competitor import (
    CompetitorCreate,
    CompetitorUpdate,
    Competitor,
    CompetitorList,
    CompetitorSearch,
    CompetitorSearchAi,
    CompetitorInsights,
)
from app.models.user import User
from app.services.auth import get_current_user
from app.services.competitor import (
    create_competitor,
    get_competitors,
    update_competitor,
    delete_competitor,
    search_competitors,
)
from app.services.ai_insights import (
    generate_competitor_insights,
    find_competitors_ai,
    lookup_competitor_ai,
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

@router.post("/lookup", response_model=CompetitorList)
async def lookup_competitor(name_or_url: str):
    return lookup_competitor_ai(name_or_url)

@router.post("/find", response_model=CompetitorList)
async def find_competitors_with_ai(
    find: CompetitorSearchAi, current_user: User = Depends(get_current_user)
):
    results = await find_competitors_ai(find.business_description, find.location)
    return results
    

@router.get("/{competitor_id}/insights", response_model=CompetitorInsights)
async def get_competitor_insights(
    competitor_id: str, current_user: User = Depends(get_current_user)
):
    competitor = await get_competitors(current_user.id, competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    insights = await generate_competitor_insights(competitor)
    return CompetitorInsights(competitor_id=competitor_id, insights=insights)
