from typing import Optional, List
from pydantic import BaseModel


class CampaignCreate(BaseModel):
    location: str
    business_type: str = "restaurant"
    min_reviews: int = 0
    min_rating: float = 0.0
    website_filter: str = "no_website"


class CampaignOut(BaseModel):
    id: str
    location: str
    business_type: str
    min_reviews: int
    min_rating: float
    website_filter: str
    status: str

    class Config:
        from_attributes = True


class BusinessOut(BaseModel):
    id: str
    campaign_id: str
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    email_confidence: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    website_url: Optional[str] = None
    website_status: Optional[str] = None
    website_score: Optional[int] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    lead_score: Optional[int] = None
    lead_priority: Optional[str] = None
    lead_reason: Optional[str] = None
    personalization_points: Optional[List[str]] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    email_status: str

    class Config:
        from_attributes = True


class CampaignStats(BaseModel):
    leads_found: int
    qualified: int
    emails_drafted: int
    emails_approved: int
    sent: int
    bounced: int
    replies: int


class ReplyClassifyIn(BaseModel):
    reply_text: str


class ReplyClassifyOut(BaseModel):
    classification: str
    suggested_reply: Optional[str] = None
