import requests
import logging
from typing import Optional, List

from config import Config

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GeocodingService:
    """Google Geocoding API — cache, ulke bileseni ac/kapa, coklu sorgu zinciri."""

    def __init__(self, db_service=None):
        self.api_key = Config.GOOGLE_API_KEY
        self._db = db_service

    def _get_db(self):
        if self._db is None:
            from services.db_service import db

            self._db = db
        return self._db

    def geocode(self, query: str, use_country_component: bool = True) -> Optional[dict]:
        if not query or not str(query).strip():
            return None
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY tanimli degil; geocoding atlaniyor.")
            return None

        query = query.strip()
        cached = self._get_db().get_cached_coords(query)
        if cached:
            return {
                "lat": cached["lat"],
                "lng": cached["lng"],
                "formatted": cached.get("formatted", ""),
            }

        try:
            params = {
                "address": query,
                "key": self.api_key,
                "language": "tr",
                "region": "tr",
            }
            if use_country_component:
                params["components"] = "country:TR"
            resp = requests.get(GEOCODE_URL, params=params, timeout=12)
            data = resp.json()
            status = data.get("status")

            if status == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                formatted = data["results"][0].get("formatted_address", "")
                lat, lng = loc["lat"], loc["lng"]
                self._get_db().cache_coords(query, lat, lng, formatted)
                logger.info("Geocoded: '%s' -> (%s, %s)", query[:80], lat, lng)
                return {"lat": lat, "lng": lng, "formatted": formatted}

            logger.debug("Geocoding bos: '%s' -> %s", query[:80], status)
            return None

        except Exception as e:
            logger.error("Geocoding hatasi: %s", e)
            return None

    def geocode_chain(self, queries: List[str]) -> Optional[dict]:
        """Ayni adres icin: once country:TR ile, sonra TR sinirlamasiz dene."""
        seen = set()
        ordered: List[str] = []
        for q in queries:
            q = (q or "").strip()
            if q and q not in seen:
                seen.add(q)
                ordered.append(q)
        max_q = getattr(Config, "GEOCODE_MAX_QUERIES", 6)
        if max_q > 0:
            ordered = ordered[:max_q]
        for q in ordered:
            r = self.geocode(q, use_country_component=True)
            if r:
                return r
        for q in ordered:
            r = self.geocode(q, use_country_component=False)
            if r:
                return r
        return None


geocoder = GeocodingService()
