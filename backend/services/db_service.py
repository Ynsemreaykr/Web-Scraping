from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import Config
import logging


def _doc_published_at(doc: dict) -> Optional[datetime]:
    return doc.get("published_at")


def _published_in_range(doc: dict, filters: Optional[dict]) -> bool:
    if not filters:
        return True
    df = filters.get("date_from")
    dt = filters.get("date_to")
    if not df and not dt:
        return True
    pt = _doc_published_at(doc)
    if pt is None:
        return False
    if df and pt < df:
        return False
    if dt and pt > dt:
        return False
    return True


def _has_valid_lat(doc: dict) -> bool:
    loc = doc.get("location") or {}
    return loc.get("lat") is not None

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
            self.client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=30000)
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
        news_col.create_index([("location.district", ASCENDING)])

        # Geocoding cache icin
        cache_col = self.db["geocoding_cache"]
        cache_col.create_index([("address", ASCENDING)], unique=True)

        logger.info("Index'ler olusturuldu.")

    # ─── Haber CRUD ───────────────────────────────────────────────
    def insert_news(self, news_doc: dict) -> Optional[str]:
        """Haberi ekle. Ayni URL varsa guncelle; her durumda _id don (bellekteki duplicate listesi icin)."""
        try:
            url = news_doc.get("url")
            if not url:
                return None
            result = self.db["news"].update_one(
                {"url": url},
                {"$set": news_doc},
                upsert=True,
            )
            if result.upserted_id:
                return str(result.upserted_id)
            hit = self.db["news"].find_one({"url": url}, {"_id": 1})
            return str(hit["_id"]) if hit else None
        except Exception as e:
            logger.error(f"Haber eklenemedi: {e}")
            return None

    def get_all_news(self, filters: Optional[dict] = None, limit: int = 500) -> list:
        """Filtreye gore haberleri getir.

        Atlas Flex / bazi ortamlarda $gte, $exists vb. sorgu operatörleri 0 sonuc
        döndürebiliyor; tarih ve konum filtreleri Python tarafinda uygulanir.
        """
        query: dict = {}
        if filters:
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("district"):
                query["location.district"] = filters["district"]

        need_python = bool(
            filters
            and (
                filters.get("date_from")
                or filters.get("date_to")
                or filters.get("has_location")
            )
        )
        fetch_cap = min(max(limit * 25, 500), 8000) if need_python else limit

        cursor = (
            self.db["news"]
            .find(query, {"embedding": 0})
            .sort("published_at", DESCENDING)
            .limit(fetch_cap)
        )
        docs = []
        for doc in cursor:
            if not _published_in_range(doc, filters):
                continue
            if filters and filters.get("has_location") and not _has_valid_lat(doc):
                continue
            doc["_id"] = str(doc["_id"])
            docs.append(doc)
            if len(docs) >= limit:
                break
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
            {},
            {"_id": 1, "url": 1, "embedding": 1, "sources": 1, "category": 1},
        )
        return [d for d in cursor if d.get("embedding")]

    def update_news_sources(self, news_id, new_source: dict) -> bool:
        """Ayni haberin yeni kaynagini ekle ($addToSet Atlas'ta sorun cikarabiliyor; read-modify-write)."""
        from bson import ObjectId

        if not new_source or not new_source.get("url"):
            return False
        oid = ObjectId(news_id)
        doc = self.db["news"].find_one({"_id": oid}, {"sources": 1})
        if not doc:
            return False
        sources = list(doc.get("sources") or [])
        urls = {s.get("url") for s in sources if isinstance(s, dict)}
        if new_source.get("url") in urls:
            return True
        sources.append(
            {
                "source_key": new_source.get("source_key", ""),
                "source_name": new_source.get("source_name", ""),
                "url": new_source.get("url", ""),
            }
        )
        self.db["news"].update_one({"_id": oid}, {"$set": {"sources": sources}})
        return True

    def purge_old_news(self, keep_days: int = 3) -> int:
        """keep_days'den eski haberleri siler."""
        cutoff = datetime.utcnow() - timedelta(days=keep_days)
        result = self.db["news"].delete_many({"published_at": {"$lt": cutoff}})
        if result.deleted_count:
            logger.warning("Eski haber temizligi: %s haber silindi (cutoff=%s)", result.deleted_count, cutoff)
        return result.deleted_count

    def clear_news_and_cache(self) -> dict:
        """Tum haberleri ve geocoding onbellegini siler (gelistirme / yeniden scrape)."""
        n_news = self.db["news"].delete_many({}).deleted_count
        n_cache = self.db["geocoding_cache"].delete_many({}).deleted_count
        logger.warning("DB temizlendi: news=%s, geocoding_cache=%s", n_news, n_cache)
        return {"news_deleted": n_news, "cache_deleted": n_cache}

    def get_stats(self) -> dict:
        """Aggregation bazı Atlas planlarında kapalı; sayımlar find + Python ile."""
        projection = {"category": 1, "location": 1, "sources": 1}
        all_docs = list(self.db["news"].find({}, projection))
        total = len(all_docs)
        by_category: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        mapped = 0
        for d in all_docs:
            cat = d.get("category") or "Diger"
            by_category[cat] = by_category.get(cat, 0) + 1
            if _has_valid_lat(d):
                mapped += 1
            sources = d.get("sources") or []
            if sources and isinstance(sources[0], dict):
                sname = sources[0].get("source_name", "Bilinmeyen")
                by_source[sname] = by_source.get(sname, 0) + 1
        return {
            "total": total,
            "mapped": mapped,
            "by_category": by_category,
            "by_source": by_source,
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
