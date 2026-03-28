"""
Ana scraping pipeline.
Scrape -> Temizle -> Siniflandir -> Konum -> Duplicate Kontrol -> Geocode -> DB'ye Kaydet
"""
import logging
import sys
import os
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.cagdas_scraper import CagdasScraper
from scraper.ozgur_scraper import OzgurScraper
from scraper.ses_scraper import SesScraper
from scraper.yeni_scraper import YeniScraper
from scraper.bizimyaka_scraper import BizimyakaScraper
from processing.cleaner import cleaner
from processing.classifier import classifier, CATEGORY_DISPLAY
from processing.location_extractor import extractor
from processing.duplicate_detector import detector
from services.db_service import db
from services.geocoding import geocoder

logger = logging.getLogger(__name__)

ALL_SCRAPERS = [
    CagdasScraper,
    OzgurScraper,
    SesScraper,
    YeniScraper,
    BizimyakaScraper,
]


def run_pipeline(source_keys: list = None) -> dict:
    """
    Tam scraping pipeline'ini calistir.
    source_keys: None ise tum kaynaklar, liste verilirse sadece o kaynaklar
    """
    stats = {"scraped": 0, "saved": 0, "duplicate": 0, "no_category": 0, "no_location": 0, "errors": 0}

    # Mevcut embedding'leri onceden yukle (benzerlik icin)
    logger.info("Mevcut embedding'ler yukleniyor...")
    existing_docs = db.get_all_embeddings()
    logger.info(f"{len(existing_docs)} mevcut haber embedding'i yuklendi.")

    for ScraperClass in ALL_SCRAPERS:
        scraper_instance = ScraperClass()

        if source_keys and scraper_instance.source_key not in source_keys:
            continue

        try:
            articles = scraper_instance.scrape()
            stats["scraped"] += len(articles)

            for article in articles:
                try:
                    result = process_article(article, existing_docs, stats)
                    if result:
                        existing_docs.append(result)  # Yeni haberi listeye ekle
                except Exception as e:
                    logger.error(f"Haber islenemedi: {article.get('url')} -> {e}")
                    stats["errors"] += 1

        except Exception as e:
            logger.error(f"Scraper hatasi [{ScraperClass.source_key}]: {e}")
            stats["errors"] += 1

    logger.info(f"Pipeline tamamlandi: {stats}")
    return stats


def process_article(article: dict, existing_docs: list, stats: dict) -> Optional[dict]:
    """Tek bir haberi isle ve DB'ye kaydet"""

    # 1. Temizle
    title_clean = cleaner.clean(article["title"])
    content_clean = cleaner.clean(article["content"])

    if not title_clean:
        stats["errors"] += 1
        return None

    # 2. Siniflandir
    category_key = classifier.classify(title_clean, content_clean)
    if not category_key:
        logger.debug(f"Kategori bulunamadi: {article['url']}")
        stats["no_category"] += 1
        # Kategori bulunamazsa haberi kaydetmiyoruz
        return None

    category_display = CATEGORY_DISPLAY.get(category_key, category_key)

    # 3. Konum cikar
    location_info = extractor.extract(content_clean + " " + title_clean)

    # 4. Embedding olustur ve duplicate kontrol
    combined_text = f"{title_clean} {content_clean[:500]}"
    embedding = detector.get_embedding(combined_text)

    duplicate = detector.find_duplicate(embedding, existing_docs)
    if duplicate:
        # Ayni haber bulundu -> kaynagi ekle
        new_source = {
            "source_key": article["source_key"],
            "source_name": article["source_name"],
            "url": article["url"],
        }
        db.update_news_sources(str(duplicate["_id"]), new_source)
        stats["duplicate"] += 1
        logger.info(f"Duplicate: {article['url']} -> {duplicate.get('url', '?')}")
        return None

    # 5. Geocoding
    location = {"lat": None, "lng": None, "text": None, "district": None, "formatted": None}
    if location_info["geocode_query"]:
        coords = geocoder.geocode(location_info["geocode_query"])
        if coords:
            location["lat"] = coords["lat"]
            location["lng"] = coords["lng"]
            location["formatted"] = coords.get("formatted", "")
        else:
            stats["no_location"] += 1
    else:
        stats["no_location"] += 1

    location["text"] = location_info["location_text"]
    location["district"] = location_info["district"]

    # 6. Haberi olustur
    news_doc = {
        "title": title_clean,
        "content": content_clean,
        "category": category_key,
        "category_display": category_display,
        "location": location,
        "published_at": article.get("published_at"),
        "url": article["url"],
        "sources": [
            {
                "source_key": article["source_key"],
                "source_name": article["source_name"],
                "url": article["url"],
            }
        ],
        "embedding": embedding,
    }

    # 7. DB'ye kaydet
    inserted_id = db.insert_news(news_doc)
    if inserted_id:
        stats["saved"] += 1
        news_doc["_id"] = inserted_id
        logger.info(f"Kaydedildi [{category_display}]: {title_clean[:60]}")
        return news_doc
    else:
        # URL ile zaten var (upsert), ko kayit sayilmaz
        return None
