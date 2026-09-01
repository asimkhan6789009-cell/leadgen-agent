from typing import List, Dict
import httpx

HEADERS = {"User-Agent": "leadgen-agent (contact: your-email@example.com)"}


def find_businesses(location: str, business_type: str = "restaurant", limit: int = 60) -> List[Dict]:
    """
    Free business discovery using OpenStreetMap's Nominatim + Overpass APIs.
    No API key needed. Data coverage is thinner than Google Places, especially
    for reviews/ratings (OSM doesn't track those at all).
    """
    geo = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": location, "format": "json", "limit": 1},
        headers=HEADERS, timeout=15,
    ).json()

    if not geo:
        return []

    lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])

    query = f"""
    [out:json][timeout:25];
    node["amenity"~"{business_type}",i](around:8000,{lat},{lon});
    out body {limit};
    """
    resp = httpx.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": query}, headers=HEADERS, timeout=30,
    )
    resp.raise_for_status()
    elements = resp.json().get("elements", [])

    businesses = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        businesses.append({
            "name": name,
            "category": business_type,
            "address": ", ".join(filter(None, [
                tags.get("addr:housenumber"), tags.get("addr:street"),
                tags.get("addr:city"),
            ])) or None,
            "city": tags.get("addr:city"),
            "country": tags.get("addr:country"),
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "google_place_id": f"osm_{el.get('id')}",
            "google_maps_url": f"https://www.openstreetmap.org/node/{el.get('id')}",
            "rating": None,
            "review_count": None,
            "website_url": tags.get("website") or tags.get("contact:website"),
        })

    return businesses
