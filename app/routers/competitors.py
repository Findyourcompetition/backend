from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from app.services.background_tasks import create_background_task, get_task_status, TaskStatus
from app.models.competitor import (
    CompetitorCreate,
    CompetitorUpdate,
    Competitor,
    CompetitorList,
    CompetitorSearch,
    CompetitorSearchAi,
    CompetitorInsights,
)
from app.database import get_collection
from app.models.user import User
from app.services.auth import get_current_user
from app.services.competitor import (
    create_competitor,
    get_competitors,
    update_competitor,
    delete_competitor,
    search_competitors,
    insert_competitors,
    get_existing_search_results
)
from app.services.ai_insights import (
    generate_competitor_insights,
)
from app.utils.logo_fetcher import (
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


@router.post("/find", response_model=Dict[str, Any])
async def find_competitors_with_ai(
    find: CompetitorSearchAi,
    search_id: Optional[str] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=6, ge=1)
):
    """Endpoint for AI-powered competitor search with background processing"""
    if search_id:
        return await get_existing_search_results(search_id, offset, limit)
    
    # Create a background task for the search
    task_id = await create_background_task("competitor_search", {
        "business_description": find.business_description,
        "location": find.location
    })
    
    return {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "message": "Your search is being processed"
    }

@router.post("/lookup", response_model=Dict[str, Any])
async def lookup_competitor(
    name_or_url: str = Query(..., description="Company name or website URL"),
    search_id: Optional[str] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=6, ge=1)
):
    """Endpoint for looking up a specific competitor with background processing"""
    if search_id:
        return await get_existing_search_results(search_id, offset, limit)
    
    task_id = await create_background_task("competitor_lookup", {
        "name_or_url": name_or_url
    })
    
    return {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "message": "Your lookup request is being processed"
    }

@router.get("/search/status/{task_id}")
async def get_search_status(task_id: str):
    """Check the status of a search task"""
    task_data = await get_task_status(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    response = {
        "status": task_data["status"],
        "created_at": task_data["updated_at"]
    }
    
    if task_data["status"] == TaskStatus.COMPLETED:
        response["result"] = task_data["result"]
        response["search_id"] = task_data["result"]["search_id"]
    elif task_data["status"] == TaskStatus.FAILED:
        response["error"] = task_data["error"]
    
    return response

@router.get("/{competitor_id}/insights", response_model=CompetitorInsights)
async def get_competitor_insights(
        competitor_id: str, current_user: User = Depends(get_current_user)
):
    competitor = await get_competitors(current_user.id, competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    insights = await generate_competitor_insights(competitor)
    return CompetitorInsights(competitor_id=competitor_id, insights=insights)
