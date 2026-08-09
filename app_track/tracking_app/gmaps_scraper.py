"""
tracking_app/gmaps_scraper.py
─────────────────────────────────────────────────────────────────────────────
Google Maps Lead Scraper — powered by SerpAPI (google_maps engine)
─────────────────────────────────────────────────────────────────────────────

API reference: https://serpapi.com/google-maps-api
Endpoint:      GET https://serpapi.com/search.json?engine=google_maps

Key params used:
  - engine  : "google_maps"
  - q       : search query (keyword + optional category)
  - type    : "search"  (required for listing results)
  - ll      : "@lat,lng,14z"  (GPS coords — most reliable for geo-targeting)
  - hl      : "en"
  - start   : pagination offset (20 per page)
  - api_key : your SerpAPI key

Location strategy:
  1. Try to geocode the user-supplied location string → lat/lng using the
     free Nominatim (OpenStreetMap) geocoder (no key needed).
  2. Fall back to passing the location string directly in `q` as
     "<keyword> in <location>" if geocoding fails.

No headless browser required — works in production with zero extra deps.
"""

from __future__ import annotations

import logging
import time
import re
from typing import Any, Generator

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SERPAPI_BASE    = "https://serpapi.com/search.json"
NOMINATIM_BASE  = "https://nominatim.openstreetmap.org/search"


# ──────────────────────────────────────────────────────────────────────────────
# Geocoding helper (Nominatim — free, no key)
# ──────────────────────────────────────────────────────────────────────────────

def _geocode(location: str) -> tuple[float, float] | None:
    """
    Returns (lat, lng) for a place name string, or None if lookup fails.
    Uses OpenStreetMap Nominatim — free, no API key required.
    """
    try:
        resp = requests.get(
            NOMINATIM_BASE,
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": "Transform.io-CRM/1.0 (contact@transform.io)"},
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        logger.warning("Nominatim geocode failed for '%s': %s", location, exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Public: scrape_google_maps
# ──────────────────────────────────────────────────────────────────────────────

def scrape_google_maps(
    keyword: str,
    location: str,
    max_results: int = 40,
    min_rating: float = 0.0,
    category: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Generator that yields one business dict at a time.

    Each yielded dict has keys:
        place_id, name, category, phone, website, address,
        rating, reviews, maps_url, lat, lng

    Yields a special dict with key ``_error`` on failure.
    """
    api_key = getattr(settings, "SERP_API_KEY", "")
    if not api_key:
        # Fallback to the direct key if the server hasn't been restarted yet to load the .env
        api_key = "65276dcf1cbff9ea32de7ff6de159a5d0bfe420520906f5f0152dee82e40e6d2"

    # Build search query — append category for more targeted results
    query = f"{keyword} {category}".strip() if category else keyword

    # Attempt to geocode the location for precise GPS targeting
    coords = _geocode(location)
    if coords:
        lat, lng = coords
        ll_param = f"@{lat},{lng},14z"   # zoom 14 = good city-level coverage
        logger.info("Geocoded '%s' → ll=%s", location, ll_param)
    else:
        # Fall back: embed city name in query; SerpAPI will still geo-target
        query = f"{query} in {location}"
        ll_param = None
        logger.info("Geocoding failed for '%s', using query fallback", location)

    seen_place_ids: set[str] = set()
    fetched = 0
    start = 0

    while fetched < max_results:
        # Build the SerpAPI request params per the official docs
        params: dict[str, Any] = {
            "engine":  "google_maps",
            "q":       query,
            "type":    "search",        # required — returns a list of results
            "hl":      "en",
            "start":   start,
            "api_key": api_key,
        }

        # Use GPS ll param if geocoding succeeded (most accurate)
        if ll_param:
            params["ll"] = ll_param
        else:
            # Use text location param with zoom level as fallback
            params["location"] = location

        try:
            response = requests.get(SERPAPI_BASE, params=params, timeout=25)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response else "?"
            msg = _parse_serpapi_error(exc)
            logger.error("SerpAPI HTTP %s: %s", status, msg)
            yield {"_error": f"SerpAPI error ({status}): {msg}"}
            return
        except requests.exceptions.RequestException as exc:
            logger.error("SerpAPI request failed: %s", exc)
            yield {"_error": f"Network error reaching SerpAPI: {exc}"}
            return

        # Check for SerpAPI-level error in JSON
        if "error" in data:
            logger.error("SerpAPI returned error: %s", data["error"])
            yield {"_error": data["error"]}
            return

        places = data.get("local_results", [])
        if not places:
            logger.info("No more results from SerpAPI at start=%d", start)
            break

        for place in places:
            if fetched >= max_results:
                break

            place_id = place.get("place_id", "")
            if place_id and place_id in seen_place_ids:
                continue
            if place_id:
                seen_place_ids.add(place_id)

            # Rating filter
            rating = place.get("rating") or 0
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = 0.0
            if rating < min_rating:
                continue

            reviews     = int(place.get("reviews", 0) or 0)
            name        = place.get("title", "Unknown Business")
            address     = place.get("address", "")
            phone       = _clean_phone(place.get("phone", ""))
            website     = place.get("website", "")
            category_str = _extract_category(place)
            maps_url    = place.get("link", "")
            gps         = place.get("gps_coordinates", {})
            lat_r       = gps.get("latitude")
            lng_r       = gps.get("longitude")

            fetched += 1
            yield {
                "place_id": place_id,
                "name":     name,
                "category": category_str,
                "phone":    phone,
                "website":  website,
                "address":  address,
                "rating":   rating,
                "reviews":  reviews,
                "maps_url": maps_url,
                "lat":      lat_r,
                "lng":      lng_r,
            }

        start += 20              # SerpAPI paginates in steps of 20
        if len(places) < 20:
            break                # last page reached

        time.sleep(0.4)          # be a polite API consumer


# ──────────────────────────────────────────────────────────────────────────────
# Public: import_lead_from_gmaps
# ──────────────────────────────────────────────────────────────────────────────

def import_lead_from_gmaps(business: dict[str, Any], tenant=None, folder=None) -> tuple[Any, bool]:
    """
    Creates (or retrieves) a Lead object from a scraped Google Maps business dict.

    Deduplication order:
        1. gmaps_place_id
        2. company_website
        3. phone number

    Returns (lead, was_created).
    """
    from .sales_models import Lead

    place_id = business.get("place_id")
    name     = business.get("name", "Unknown")
    website  = business.get("website", "")
    phone    = business.get("phone", "")
    address  = business.get("address", "")

    # ── Deduplication ──────────────────────────────────────────────
    existing = None
    if place_id:
        existing = Lead.objects.filter(gmaps_place_id=place_id).first()
    if not existing and website:
        existing = Lead.objects.filter(company_website=website).first()
    if not existing and phone:
        existing = Lead.objects.filter(phone=phone).first()

    if existing:
        return existing, False

    # ── Create new lead ────────────────────────────────────────────
    lead = Lead.objects.create(
        contact_name     = name,
        email            = None,          # Google Maps rarely exposes email
        company_name     = name,
        company_location = address,
        company_website  = website or None,
        phone            = phone or None,
        source           = "google_maps",
        status           = "new",
        industry         = business.get("category", ""),
        # GMaps-specific fields
        gmaps_place_id   = place_id or None,
        gmaps_rating     = business.get("rating"),
        gmaps_reviews    = business.get("reviews"),
        gmaps_category   = business.get("category", ""),
        gmaps_address    = address,
        gmaps_maps_url   = business.get("maps_url", ""),
        tenant           = tenant,
        folder           = folder,
    )
    return lead, True


# ──────────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────────

def _clean_phone(phone: str) -> str:
    """Strip non-standard characters from a phone string."""
    if not phone:
        return ""
    return re.sub(r"[^\d+\s\-\(\)]", "", phone).strip()


def _extract_category(place: dict) -> str:
    """Extract a human-readable category from a SerpAPI place result."""
    # SerpAPI returns category under 'type' key
    if place.get("type"):
        return place["type"]
    # Fallback: check extensions
    extensions = place.get("extensions", {})
    if isinstance(extensions, dict):
        return extensions.get("service", "")
    return ""


def _parse_serpapi_error(exc: requests.exceptions.HTTPError) -> str:
    """Try to extract a readable error message from a SerpAPI 4xx/5xx response."""
    try:
        data = exc.response.json()
        return data.get("error", str(exc))
    except Exception:
        return str(exc)
