"""
Ana scraping pipeline.
Scrape -> Temizle -> Siniflandir -> Konum -> Duplicate Kontrol -> Geocode -> DB'ye Kaydet
"""
import logging
import sys
import os
import threading
import concurrent.futures
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
from config import Config
from services.db_service import db
from services.geocoding import geocoder
from scrape_state import set_progress
from processing.dedupe_db_merge import merge_duplicate_news_in_db
from processing.summarizer import smart_summary

logger = logging.getLogger(__name__)

ALL_SCRAPERS = [
    CagdasScraper,
    OzgurScraper,
    SesScraper,
    YeniScraper,
    BizimyakaScraper,
]

_stats_lock = threading.Lock()
# Paralel scraper'lar ayni haberi ayni anda islerse ikisi de "duplicate yok" goruyordu.
_dedupe_lock = threading.Lock()


def _bump(stats: dict, key: str, n: int = 1) -> None:
    with _stats_lock:
        stats[key] = stats.get(key, 0) + n


def run_pipeline(source_keys: list = None) -> dict:
    """
    Tam scraping pipeline'ini calistir.
    source_keys: None ise tum kaynaklar, liste verilirse sadece o kaynaklar
    """
    stats = {
        "scraped": 0,
        "saved": 0,
        "duplicate": 0,
        "no_category": 0,
        "no_location": 0,
        "geocode_failed": 0,
        "geocode_fallback": 0,
        "errors": 0,
        "db_merged": 0,
    }

    set_progress(phase="embedding", message="Mevcut haberler ve embedding yukleniyor...")
    logger.info("Mevcut embedding'ler yukleniyor...")
    existing_docs = db.get_all_embeddings()
    logger.info("%s mevcut haber embedding'i yuklendi.", len(existing_docs))

    set_progress(phase="model", message="Yapay zeka modeli yukleniyor (ilk seferde 1-2 dk surebilir)...")
    logger.info("Embedding modeli ilk yukleme / isinma...")
    detector.get_embedding("Kocaeli haber")
    logger.info("Embedding modeli hazir.")

    set_progress(phase="scraping", message="Siteler taranıyor (5 kaynak)...")

    def scrape_and_process(ScraperClass):
        scraper_instance = ScraperClass()

        if source_keys and scraper_instance.source_key not in source_keys:
            return

        try:
            set_progress(
                current_source=scraper_instance.source_key,
                message=f"{scraper_instance.source_name}: liste ve haber sayfalari...",
            )
            articles = scraper_instance.scrape()
            _bump(stats, "scraped", len(articles))
            set_progress(
                message=f"{scraper_instance.source_name}: {len(articles)} haber — siniflandirma / geocode...",
            )

            for article in articles:
                try:
                    process_article(article, existing_docs, stats)
                except Exception as e:
                    logger.error("Haber islenemedi: %s -> %s", article.get("url"), e)
                    _bump(stats, "errors")

        except Exception as e:
            logger.error("Scraper hatasi [%s]: %s", ScraperClass.source_key, e)
            _bump(stats, "errors")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_and_process, Cls) for Cls in ALL_SCRAPERS]
        concurrent.futures.wait(futures)

    set_progress(
        phase="merge",
        message="Aynı haberler farklı sitelerden birleştiriliyor...",
    )
    try:
        merged_n = merge_duplicate_news_in_db()
        stats["db_merged"] = merged_n
        logger.info("Veritabani birlestirme: %s yinelenen kayit silindi.", merged_n)
    except Exception as e:
        logger.error("DB birlestirme hatasi: %s", e)
        _bump(stats, "errors")

    set_progress(phase="done", message="Tamamlandi — sonuclar kaydedildi.")
    logger.info("Pipeline tamamlandi: %s", stats)
    return stats


def process_article(article: dict, existing_docs: list, stats: dict) -> Optional[dict]:
    """Tek bir haberi isle ve DB'ye kaydet"""

    title_clean = cleaner.clean(article["title"])
    content_clean = cleaner.clean(article["content"])

    if not title_clean or len(title_clean) < 5 or "javascript" in title_clean.lower():
        _bump(stats, "errors")
        return None

    category_key = classifier.classify(
        title_clean, content_clean, article_url=article.get("url") or ""
    )
    if not category_key:
        logger.debug("Kategori bulunamadi: %s", article["url"])
        _bump(stats, "no_category")
        return None

    category_display = CATEGORY_DISPLAY.get(category_key, category_key)

    location_info = extractor.extract(
        text=content_clean,
        title=title_clean,
        assume_local=True,
        category_hint=category_key,
        url=article.get("url", ""),
    )

    if not location_info.get("geocode_query"):
        _bump(stats, "no_location")
        return None

    # DB'deki eski embedding'lerle uyum icin formulu sabit tut (degisirse benzerlik duser)
    combined_text = f"{title_clean} {content_clean[:2500]}"
    embedding = detector.get_embedding(combined_text)

    queries = []
    gq = location_info.get("geocode_query")
    lt = location_info.get("location_text")
    if gq:
        queries.append(gq)
    if lt and lt != gq:
        queries.append(f"{lt}, Türkiye")
        queries.append(lt)
    d = location_info.get("district")
    if d:
        queries.append(f"{d}, Kocaeli, Türkiye")
    queries.extend(
        [
            "İzmit, Kocaeli, Türkiye",
            "Izmit, Kocaeli, Turkey",
            "Kocaeli, Türkiye",
        ]
    )

    with _dedupe_lock:
        duplicate = detector.find_duplicate(
            embedding, existing_docs, category=category_key
        )
        if duplicate:
            new_source = {
                "source_key": article["source_key"],
                "source_name": article["source_name"],
                "url": article["url"],
            }
            db.update_news_sources(str(duplicate["_id"]), new_source)
            _bump(stats, "duplicate")
            logger.info(
                "Coklu kaynak: %s -> mevcut %s",
                article["url"][:60],
                duplicate.get("url", "?")[:60],
            )
            return None

        coords = geocoder.geocode_chain(queries)
        geocode_fallback = False
        if not coords and getattr(Config, "GEOCODE_CENTER_FALLBACK", True):
            coords = {
                "lat": Config.KOCAELI_CENTER_LAT,
                "lng": Config.KOCAELI_CENTER_LNG,
                "formatted": "Kocaeli (genel konum)",
            }
            geocode_fallback = True
            _bump(stats, "geocode_fallback")

        if not coords:
            _bump(stats, "geocode_failed")
            logger.info("Geocoding tum adaylar basarisiz: %s", article.get("url"))
            return None

        location = {
            "lat": coords["lat"],
            "lng": coords["lng"],
            "text": location_info["location_text"],
            "district": location_info["district"],
            "formatted": coords.get("formatted", ""),
            "geocode_fallback": geocode_fallback,
        }

        summary = smart_summary(title_clean, content_clean)

        news_doc = {
            "title": title_clean,
            "content": content_clean,
            "summary": summary,
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

        inserted_id = db.insert_news(news_doc)
        if inserted_id:
            _bump(stats, "saved")
            news_doc["_id"] = inserted_id
            news_doc["category"] = category_key
            sid = str(inserted_id)
            existing_docs[:] = [d for d in existing_docs if str(d.get("_id")) != sid]
            existing_docs.append(news_doc)
            logger.info("Kaydedildi [%s]: %s", category_display, title_clean[:60])
            return news_doc

    return None
