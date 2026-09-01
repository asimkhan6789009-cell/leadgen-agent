import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id():
    return str(uuid.uuid4())


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=gen_id)
    location = Column(String, nullable=False)
    business_type = Column(String, nullable=False, default="restaurant")
    min_reviews = Column(Integer, default=0)
    min_rating = Column(Float, default=0.0)
    website_filter = Column(String, default="no_website")
    status = Column(String, default="created")
    created_at = Column(DateTime, default=datetime.utcnow)

    businesses = relationship("Business", back_populates="campaign", cascade="all, delete-orphan")


class Business(Base):
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, default=gen_id)
    campaign_id = Column(String, ForeignKey("campaigns.id"))

    name = Column(String, nullable=False)
    category = Column(String)

    address = Column(String)
    city = Column(String)
    country = Column(String)

    phone = Column(String)
    email = Column(String)
    email_confidence = Column(Float, default=0.0)

    google_place_id = Column(String, unique=True, index=True)
    google_maps_url = Column(String)

    rating = Column(Float)
    review_count = Column(Integer)

    website_url = Column(String)
    website_status = Column(String, default="UNKNOWN")
    website_score = Column(Integer)

    facebook_url = Column(String)
    instagram_url = Column(String)

    lead_score = Column(Integer)
    lead_priority = Column(String)
    lead_reason = Column(Text)
    personalization_points = Column(JSON)

    email_subject = Column(String)
    email_body = Column(Text)
    email_status = Column(String, default="NOT_SENT")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="businesses")
    events = relationship("EmailEvent", back_populates="business", cascade="all, delete-orphan")


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(String, primary_key=True, default=gen_id)
    business_id = Column(String, ForeignKey("businesses.id"))

    event_type = Column(String)
    event_time = Column(DateTime, default=datetime.utcnow)
    meta = Column(JSON, default=dict)

    business = relationship("Business", back_populates="events")
