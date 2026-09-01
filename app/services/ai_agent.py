import json
from typing import Dict

import httpx

from app.config import settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def _call_gemini(system: str, user_content: str, max_tokens: int = 600) -> str:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

    resp = httpx.post(
        GEMINI_URL,
        params={"key": settings.GEMINI_API_KEY},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


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
        "website. Do NOT invent any facts not present in the input. "
        "Respond with ONLY a JSON object, no preamble, no markdown fences: "
        '{"score": 0-100, "priority": "HIGH|MEDIUM|LOW", "reason": "one or two sentences", '
        '"personalization_points": ["short factual point", ...]}'
    )

    try:
        text = _call_gemini(system, json.dumps(payload), max_tokens=500)
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
        f"({sender_name}) offering {sender_service}. Be concise and polite. Do not "
        "exaggerate or invent information. If website_status is NO_WEBSITE, say you "
        "noticed they don't have a dedicated website yet. Mention only the verified "
        "facts given. Do not use manipulative language. Include exactly one clear "
        "call to action. Sign off with the sender's name only. "
        "Respond with ONLY a JSON object, no preamble, no markdown fences: "
        '{"subject": "...", "body": "..."}'
    )

    try:
        text = _call_gemini(system, json.dumps(payload), max_tokens=600)
        return _extract_json(text)
    except Exception:
        return {"subject": f"Website idea for {business.get('name')}", "body": ""}


def classify_reply(reply_text: str, business_name: str) -> Dict:
    valid = ["INTERESTED", "NOT_INTERESTED", "ASKING_PRICE", "ASKING_QUESTION",
             "LATER", "UNSUBSCRIBE", "UNKNOWN"]

    system = (
        "Classify this email reply to a cold outreach about website design. "
        f"Valid classifications: {', '.join(valid)}. "
        "Then draft a brief, polite, factual suggested next reply (skip this if "
        "classification is UNSUBSCRIBE or NOT_INTERESTED). "
        "Respond with ONLY JSON, no preamble: "
        '{"classification": "...", "suggested_reply": "..."}'
    )

    try:
        text = _call_gemini(system, json.dumps({"business_name": business_name, "reply": reply_text}), max_tokens=400)
        return _extract_json(text)
    except Exception:
        return {"classification": "UNKNOWN", "suggested_reply": None}
