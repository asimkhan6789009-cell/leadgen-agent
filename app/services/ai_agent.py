import json
from typing import Dict

import anthropic

from app.config import settings

MODEL = "claude-sonnet-4-6"


def _client():
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _extract_json(text: str) -> Dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def score_lead(business: Dict) -> Dict:
    payload = {
        "business_name": business.get("name"),
        "category": business.get("category"),
        "location": business.get("city") or business.get("address"),
        "rating": business.get("rating"),
        "review_count": business.get("review_count"),
        "website_status": business.get("website_status"),
        "has_facebook": bool(business.get("facebook_url")),
        "has_instagram": bool(business.get("instagram_url")),
    }

    system = (
        "You are a local-business lead qualification assistant for a web design "
        "freelancer. Score how good a prospect this business is for a professional "
        "website. Consider review count, rating, apparent business maturity, "
        "existing online presence, and whether a website would plausibly help them. "
        "Do NOT invent any facts not present in the input. "
        "Respond with ONLY a JSON object, no preamble, no markdown fences: "
        '{"score": 0-100, "priority": "HIGH|MEDIUM|LOW", "reason": "one or two sentences", '
        '"personalization_points": ["short factual point", ...]}'
    )

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(text)
    except Exception:
        return {"score": 0, "priority": "LOW", "reason": "Could not score (parse error).",
                 "personalization_points": []}


def write_email(business: Dict, sender_name: str, sender_service: str = "professional restaurant/small-business website design") -> Dict:
    payload = {
        "business_name": business.get("name"),
        "city": business.get("city") or business.get("address"),
        "rating": business.get("rating"),
        "review_count": business.get("review_count"),
        "website_status": business.get("website_status"),
        "personalization_points": business.get("personalization_points") or [],
    }

    system = (
        "Write a concise, factual cold outreach email from a freelance web designer "
        f"({sender_name}) offering {sender_service}. Rules: "
        "Be concise and polite. Do not exaggerate or invent information. "
        "Do not claim their website is bad if website_status is not BROKEN/POOR - "
        "if website_status is NO_WEBSITE, say you noticed they don't have a dedicated "
        "website yet. Mention only the verified facts given. Do not use manipulative "
        "or high-pressure language. Include exactly one clear call to action. "
        "Do not pretend to have a personal relationship with the recipient. "
        "Sign off with the sender's name only - do not invent a company name. "
        "Respond with ONLY a JSON object, no preamble, no markdown fences: "
        '{"subject": "...", "body": "..."}'
    )

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(text)
    except Exception:
        return {"subject": f"Website idea for {business.get('name')}", "body": text}


def classify_reply(reply_text: str, business_name: str) -> Dict:
    valid = ["INTERESTED", "NOT_INTERESTED", "ASKING_PRICE", "ASKING_QUESTION",
             "LATER", "UNSUBSCRIBE", "UNKNOWN"]

    system = (
        "Classify this email reply to a cold outreach about website design. "
        f"Valid classifications: {', '.join(valid)}. "
        "Then draft a brief, polite, factual suggested next reply (skip this if "
        "classification is UNSUBSCRIBE or NOT_INTERESTED - just acknowledge and close politely). "
        "Respond with ONLY JSON, no preamble: "
        '{"classification": "...", "suggested_reply": "..."}'
    )

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": json.dumps({"business_name": business_name, "reply": reply_text})}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(text)
    except Exception:
        return {"classification": "UNKNOWN", "suggested_reply": None}
