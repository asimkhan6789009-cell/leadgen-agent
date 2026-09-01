from typing import List, Dict
import googlemaps

from app.config import settings


def _client():
    if not settings.GOOGLE_PLACES_API_KEY:
        raise RuntimeError(
            "GOOGLE_PLACES_API_KEY is not set. Add it to your .env file. "
            "Get one at https://console.cloud.google.com/google/maps-apis"
        )
    return googlemaps.Client(key=settings.GOOGLE_PLACES_API_KEY)


def find_businesses(location: str, business_type: str = "restaurant", limit: int = 60) -> List[Dict]:
    gmaps = _client()
    query = f"{business_type} in {location}"

    results: List[Dict] = []
    resp = gmaps.places(query=query)
    results.extend(resp.get("results", []))

    while resp.get("next_page_token") and len(results) < limit:
        import time
        time.sleep(2)
        resp = gmaps.places(query=query, page_token=resp["next_page_token"])
        results.extend(resp.get("results", []))

    results = results[:limit]

    businesses = []
    for place in results:
        place_id = place.get("place_id")
        details = {}
        try:
            details_resp = gmaps.place(
                place_id=place_id,
                fields=[
                    "name", "formatted_address", "formatted_phone_number",
                    "website", "rating", "user_ratings_total", "url",
                    "address_component", "type",
                ],
            )
            details = details_resp.get("result", {})
        except Exception:
            pass

        city, country = _extract_city_country(details.get("address_components", []))

        businesses.append({
            "name": details.get("name") or place.get("name"),
            "category": business_type,
            "address": details.get("formatted_address") or place.get("formatted_address"),
            "city": city,
            "country": country,
            "phone": details.get("formatted_phone_number"),
            "google_place_id": place_id,
            "google_maps_url": details.get("url"),
            "rating": details.get("rating") or place.get("rating"),
            "review_count": details.get("user_ratings_total") or place.get("user_ratings_total"),
            "website_url": details.get("website"),
        })

    return businesses


def _extract_city_country(components: List[Dict]):
    city, country = None, None
    for comp in components:
        types = comp.get("types", [])
        if "locality" in types:
            city = comp.get("long_name")
        if "country" in types:
            country = comp.get("long_name")
    return city, country
