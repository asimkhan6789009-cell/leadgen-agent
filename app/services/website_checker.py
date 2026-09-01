from typing import Dict, Optional
import re
import httpx
from bs4 import BeautifulSoup

SOCIAL_DOMAINS = ("facebook.com", "instagram.com", "linktr.ee", "linktree.com")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadResearchBot/1.0)"}


def check_website(url: Optional[str]) -> Dict:
    if not url:
        return {"status": "NO_WEBSITE", "score": 0, "facebook_url": None, "instagram_url": None}

    if any(domain in url for domain in SOCIAL_DOMAINS):
        social = {"facebook_url": url if "facebook.com" in url else None,
                  "instagram_url": url if "instagram.com" in url else None}
        return {"status": "NO_WEBSITE", "score": 0, **social}

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
    except Exception:
        return {"status": "BROKEN", "score": 0, "facebook_url": None, "instagram_url": None}

    if resp.status_code >= 400:
        return {"status": "BROKEN", "score": 0, "facebook_url": None, "instagram_url": None}

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    score = _score_website(soup, html)
    facebook_url, instagram_url = _find_social_links(soup)

    if score < 55:
        status = "POOR"
    else:
        status = "GOOD"

    return {"status": status, "score": score, "facebook_url": facebook_url, "instagram_url": instagram_url}


def _score_website(soup: BeautifulSoup, html: str) -> int:
    score = 0
    text_len = len(soup.get_text(strip=True))

    if text_len > 200:
        score += 15
    if text_len > 800:
        score += 15

    if soup.title and soup.title.text.strip():
        score += 10
    if soup.find("meta", attrs={"name": "description"}):
        score += 10

    if soup.find("meta", attrs={"name": "viewport"}):
        score += 15

    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", html):
        score += 10
    if re.search(r"(\+?\d[\d\-\s().]{7,}\d)", html):
        score += 10

    links = soup.find_all("a", href=True)
    if len(links) > 5:
        score += 10
    if len(links) > 15:
        score += 5

    return min(score, 100)


def _find_social_links(soup: BeautifulSoup):
    facebook_url, instagram_url = None, None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "facebook.com" in href and not facebook_url:
            facebook_url = href
        if "instagram.com" in href and not instagram_url:
            instagram_url = href
    return facebook_url, instagram_url
