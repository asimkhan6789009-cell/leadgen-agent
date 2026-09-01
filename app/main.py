from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import models, schemas
from app.services import places_service, website_checker, ai_agent, email_service

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Local Business Lead Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/campaigns", response_model=schemas.CampaignOut)
def create_campaign(payload: schemas.CampaignCreate, db: Session = Depends(get_db)):
    campaign = models.Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/campaigns/{campaign_id}", response_model=schemas.CampaignOut)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.get(models.Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    return campaign


@app.get("/campaigns", response_model=List[schemas.CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(models.Campaign).order_by(models.Campaign.created_at.desc()).all()


@app.post("/campaigns/{campaign_id}/search")
def search_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.get(models.Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    campaign.status = "searching"
    db.commit()

    try:
        raw_businesses = places_service.find_businesses(campaign.location, campaign.business_type)
    except Exception as e:
        campaign.status = "error"
        db.commit()
        raise HTTPException(400, f"Places search failed: {e}")

    created = 0
    for b in raw_businesses:
        if campaign.min_rating and (b.get("rating") or 0) < campaign.min_rating:
            continue
        if campaign.min_reviews and (b.get("review_count") or 0) < campaign.min_reviews:
            continue

        existing = db.query(models.Business).filter_by(google_place_id=b["google_place_id"]).first()
        if existing:
            continue

        site_check = website_checker.check_website(b.get("website_url"))

        if campaign.website_filter == "no_website" and site_check["status"] != "NO_WEBSITE":
            continue
        if campaign.website_filter == "no_or_poor" and site_check["status"] not in ("NO_WEBSITE", "BROKEN", "POOR"):
            continue

        business = models.Business(
            campaign_id=campaign.id,
            name=b["name"],
            category=b.get("category"),
            address=b.get("address"),
            city=b.get("city"),
            country=b.get("country"),
            phone=b.get("phone"),
            google_place_id=b.get("google_place_id"),
            google_maps_url=b.get("google_maps_url"),
            rating=b.get("rating"),
            review_count=b.get("review_count"),
            website_url=b.get("website_url"),
            website_status=site_check["status"],
            website_score=site_check.get("score"),
            facebook_url=site_check.get("facebook_url"),
            instagram_url=site_check.get("instagram_url"),
        )
        db.add(business)
        created += 1

    campaign.status = "ready"
    db.commit()
    return {"campaign_id": campaign_id, "new_leads": created}


@app.get("/campaigns/{campaign_id}/businesses", response_model=List[schemas.BusinessOut])
def campaign_businesses(campaign_id: str, db: Session = Depends(get_db)):
    return db.query(models.Business).filter_by(campaign_id=campaign_id).all()


@app.get("/campaigns/{campaign_id}/stats", response_model=schemas.CampaignStats)
def campaign_stats(campaign_id: str, db: Session = Depends(get_db)):
    q = db.query(models.Business).filter_by(campaign_id=campaign_id)
    return schemas.CampaignStats(
        leads_found=q.count(),
        qualified=q.filter(models.Business.lead_score.isnot(None)).count(),
        emails_drafted=q.filter(models.Business.email_status.in_(["DRAFT", "APPROVED", "SENT"])).count(),
        emails_approved=q.filter(models.Business.email_status.in_(["APPROVED", "SENT"])).count(),
        sent=q.filter(models.Business.email_status == "SENT").count(),
        bounced=q.filter(models.Business.email_status == "BOUNCED").count(),
        replies=q.filter(models.Business.email_status == "REPLIED").count(),
    )


@app.get("/businesses/{business_id}", response_model=schemas.BusinessOut)
def get_business(business_id: str, db: Session = Depends(get_db)):
    business = db.get(models.Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    return business


@app.post("/businesses/{business_id}/analyze", response_model=schemas.BusinessOut)
def analyze_business(business_id: str, db: Session = Depends(get_db)):
    business = db.get(models.Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")

    site_check = website_checker.check_website(business.website_url)
    business.website_status = site_check["status"]
    business.website_score = site_check.get("score")
    business.facebook_url = business.facebook_url or site_check.get("facebook_url")
    business.instagram_url = business.instagram_url or site_check.get("instagram_url")
    db.commit()
    db.refresh(business)
    return business


@app.post("/businesses/{business_id}/generate-email", response_model=schemas.BusinessOut)
def generate_email(business_id: str, sender_name: str = "Your Name", db: Session = Depends(get_db)):
    business = db.get(models.Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")

    b_dict = {
        "name": business.name, "category": business.category,
        "city": business.city or business.address,
        "rating": business.rating, "review_count": business.review_count,
        "website_status": business.website_status,
        "facebook_url": business.facebook_url, "instagram_url": business.instagram_url,
    }

    score_result = ai_agent.score_lead(b_dict)
    business.lead_score = score_result.get("score")
    business.lead_priority = score_result.get("priority")
    business.lead_reason = score_result.get("reason")
    business.personalization_points = score_result.get("personalization_points")

    b_dict["personalization_points"] = business.personalization_points
    email_result = ai_agent.write_email(b_dict, sender_name=sender_name)
    business.email_subject = email_result.get("subject")
    business.email_body = email_result.get("body")
    business.email_status = "DRAFT"

    db.commit()
    db.refresh(business)
    return business


@app.post("/businesses/{business_id}/approve-email", response_model=schemas.BusinessOut)
def approve_email(business_id: str, db: Session = Depends(get_db)):
    business = db.get(models.Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    if business.email_status != "DRAFT":
        raise HTTPException(400, f"Cannot approve from status {business.email_status}")
    business.email_status = "APPROVED"
    db.commit()
    db.refresh(business)
    return business


@app.post("/businesses/{business_id}/send-email", response_model=schemas.BusinessOut)
def send_email_route(business_id: str, db: Session = Depends(get_db)):
    business = db.get(models.Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")

    if settings_manual_required() and business.email_status != "APPROVED":
        raise HTTPException(400, "Email must be APPROVED before sending (manual review is required).")

    if not business.email:
        raise HTTPException(400, "No verified contact email on file for this business.")

    email_service.send_email(business.email, business.email_subject, business.email_body)
    business.email_status = "SENT"
    db.add(models.EmailEvent(business_id=business.id, event_type="SENT"))
    db.commit()
    db.refresh(business)
    return business


def settings_manual_required() -> bool:
    from app.config import settings
    return settings.AUTOMATION_LEVEL != "auto"


@app.post("/emails/{business_id}/classify-reply", response_model=schemas.ReplyClassifyOut)
def classify_reply(business_id: str, payload: schemas.ReplyClassifyIn, db: Session = Depends(get_db)):
    business = db.get(models.Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")

    result = ai_agent.classify_reply(payload.reply_text, business.name)

    status_map = {"UNSUBSCRIBE": "OPTED_OUT"}
    business.email_status = status_map.get(result["classification"], "REPLIED")
    db.add(models.EmailEvent(
        business_id=business.id, event_type="REPLIED",
        meta={"classification": result["classification"], "reply_text": payload.reply_text},
    ))
    db.commit()
    return result


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def dashboard():
    return FileResponse("static/index.html")
