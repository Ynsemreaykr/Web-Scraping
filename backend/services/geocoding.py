import requests
import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GeocodingService:
    """Google Geocoding API ile koordinat donusturme"""

    def __init__(self, db_service=None):
        self.api_key = Config.GOOGLE_API_KEY
        self._db = db_service  # Cache icin (opsiyonel, lazy-load edilecek)

    def _get_db(self):
        if self._db is None:
            from services.db_service import db
            self._db = db
        return self._db

    def geocode(self, query: str) -> Optional[dict]:
        """
        Adres metnini koordinata donustur.
        Once cache'e bak, yoksa API'ye sor.

        Returns:
            {"lat": float, "lng": float, "formatted": str} veya None
        """
        if not query:
            return None

        # Cache kontrolu
        cached = self._get_db().get_cached_coords(query)
        if cached:
            logger.debug(f"Cache hit: {query}")
            return {"lat": cached["lat"], "lng": cached["lng"], "formatted": cached.get("formatted", "")}

        # API cagrisi
        try:
            params = {
                "address": query,
                "key": self.api_key,
                "language": "tr",
                "region": "tr",
                "components": "country:TR",
            }
            resp = requests.get(GEOCODE_URL, params=params, timeout=10)
            data = resp.json()

            if data["status"] == "OK":
                loc = data["results"][0]["geometry"]["location"]
                formatted = data["results"][0].get("formatted_address", "")
                lat, lng = loc["lat"], loc["lng"]

                # Cache'e yaz
                self._get_db().cache_coords(query, lat, lng, formatted)
                logger.info(f"Geocoded: '{query}' -> ({lat}, {lng})")
                return {"lat": lat, "lng": lng, "formatted": formatted}

            else:
                logger.warning(f"Geocoding basarisiz: '{query}' -> {data['status']}")
                return None

        except Exception as e:
            logger.error(f"Geocoding hatasi: {e}")
            return None


geocoder = GeocodingService()
