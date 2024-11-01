from pydantic import BaseModel, Field
from typing import Optional, List, Generic, TypeVar
import uuid

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    offset: int
    limit: int
    search_id: str
    competitors: List[T] = Field(description="The list of competitors")

    class Config:
        from_attributes = True

class SocialMedia(BaseModel):
    facebook: Optional[str]
    twitter: Optional[str]
    youtube: Optional[str]
    instagram: Optional[str]

class CompetitorBase(BaseModel):
    name: str
    business_type: str
    location: str
    logo: str
    revenue_range: str = Field(..., example="$1M-$10M")
    what_they_sell: List[str]
    target_market: str = Field(..., example="Global, Nigeria, Brazil, etc...")
    description: Optional[str]
    website: Optional[str]
    strengths: List[str]
    social_media: SocialMedia

class CompetitorBaseList(CompetitorBase):
    competitors: list[CompetitorBase] = Field(description="The list of competitors from AI")

class Competitor(CompetitorBase):
#    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None

class CompetitorList(PaginatedResponse[Competitor]):
    competitors: list[Competitor] = Field(description="The list of competitors")

class SingleCompetitorSearch(CompetitorBase):
    countries: List[str]

class SingleCompetitorSearchResult(PaginatedResponse[SingleCompetitorSearch]):
    competitors: list[SingleCompetitorSearch] = Field(description="The list of competitors from AI")
    
class CompetitorSearch(BaseModel):
    business_type: str
    location: str
    
class CompetitorSearchAi(BaseModel):
    business_description: str
    location: str

class CompetitorInsights(BaseModel):
    competitor_id: str
    insights: List[str]

class CompetitorCreate(CompetitorBase):
    pass

class CompetitorUpdate(CompetitorBase):
    pass
