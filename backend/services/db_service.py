from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import Config
import logging

logger = logging.getLogger(__name__)


class DBService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        try:
            self.client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            self.db = self.client[Config.MONGODB_DB_NAME]
            self._ensure_indexes()
            logger.info("MongoDB baglantisi basarili.")
        except ConnectionFailure as e:
            logger.error(f"MongoDB baglanti hatasi: {e}")
            raise

    def _ensure_indexes(self):
        """Gerekli index'leri olustur"""
        news_col = self.db["news"]
        news_col.create_index([("url", ASCENDING)], unique=True)
        news_col.create_index([("published_at", DESCENDING)])
        news_col.create_index([("category", ASCENDING)])
        news_col.create_index([("district", ASCENDING)])

        # Geocoding cache icin
        cache_col = self.db["geocoding_cache"]
        cache_col.create_index([("address", ASCENDING)], unique=True)

        logger.info("Index'ler olusturuldu.")

    # ─── Haber CRUD ───────────────────────────────────────────────
    def insert_news(self, news_doc: dict) -> Optional[str]:
        """Haberi ekle. Ayni URL varsa guncelle."""
        try:
            result = self.db["news"].update_one(
                {"url": news_doc["url"]},
                {"$set": news_doc},
                upsert=True
            )
            return str(result.upserted_id) if result.upserted_id else None
        except Exception as e:
            logger.error(f"Haber eklenemedi: {e}")
            return None

    def get_all_news(self, filters: Optional[dict] = None, limit: int = 500) -> list:
        """Filtreye gore haberleri getir"""
        query = {}
        if filters:
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("district"):
                query["district"] = {"$regex": filters["district"], "$options": "i"}
            if filters.get("date_from"):
                query.setdefault("published_at", {})["$gte"] = filters["date_from"]
            if filters.get("date_to"):
                query.setdefault("published_at", {})["$lte"] = filters["date_to"]
            if filters.get("has_location"):
                query["location.lat"] = {"$exists": True, "$ne": None}

        cursor = self.db["news"].find(query, {"embedding": 0}).sort("published_at", DESCENDING).limit(limit)
        docs = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(doc)
        return docs

    def get_news_by_id(self, news_id: str) -> Optional[dict]:
        from bson import ObjectId
        doc = self.db["news"].find_one({"_id": ObjectId(news_id)}, {"embedding": 0})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def get_all_embeddings(self) -> list:
        """Benzerlik kontrolu icin tum embedding'leri getir"""
        cursor = self.db["news"].find(
            {"embedding": {"$exists": True}},
            {"_id": 1, "url": 1, "embedding": 1, "sources": 1}
        )
        return list(cursor)

    def update_news_sources(self, news_id, new_source: dict):
        """Ayni haberin yeni kaynagini ekle"""
        from bson import ObjectId
        self.db["news"].update_one(
            {"_id": ObjectId(news_id)},
            {"$addToSet": {"sources": new_source}}
        )

    def get_stats(self) -> dict:
        pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        ]
        categories = list(self.db["news"].aggregate(pipeline))
        total = self.db["news"].count_documents({})
        mapped = self.db["news"].count_documents({"location.lat": {"$exists": True, "$ne": None}})
        return {
            "total": total,
            "mapped": mapped,
            "by_category": {c["_id"]: c["count"] for c in categories}
        }

    # ─── Geocoding Cache ──────────────────────────────────────────
    def get_cached_coords(self, address: str) -> Optional[dict]:
        return self.db["geocoding_cache"].find_one({"address": address})

    def cache_coords(self, address: str, lat: float, lng: float, formatted: str = ""):
        try:
            self.db["geocoding_cache"].update_one(
                {"address": address},
                {"$set": {"lat": lat, "lng": lng, "formatted": formatted, "cached_at": datetime.utcnow()}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Geocoding cache hatasi: {e}")

    def close(self):
        self.client.close()


# Singleton erisim
db = DBService()
