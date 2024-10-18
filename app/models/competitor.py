from pydantic import BaseModel, Field
from typing import Optional, List

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

class CompetitorCreate(CompetitorBase):
    pass

class CompetitorUpdate(CompetitorBase):
    pass

class Competitor(CompetitorBase):
    id: str
    user_id: Optional[str] = None

class CompetitorList(BaseModel):
    competitors: list[Competitor] = Field(description="The list of competitors")
    
class CompetitorSearch(BaseModel):
    business_type: str
    location: str

class CompetitorSearchAi(BaseModel):
    business_description: str
    location: str

class CompetitorInsights(BaseModel):
    competitor_id: str
    insights: List[str]
