import requests
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List
from bs4 import BeautifulSoup
from config import Config

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


class BaseScraper(ABC):
    """Tum scraperlar icin temel sinif"""

    source_key: str = ""    # ornek: "cagdaskocaeli"
    source_name: str = ""   # ornek: "Cagdas Kocaeli"
    base_url: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cutoff_date = datetime.utcnow() - timedelta(days=Config.SCRAPE_DAYS)

    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            time.sleep(Config.REQUEST_DELAY)
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning(f"[{self.source_key}] Sayfa alinamadi: {url} -> {e}")
            return None

    @abstractmethod
    def get_news_urls(self) -> List[str]:
        """Haber URL listesini dondur"""
        pass

    @abstractmethod
    def parse_article(self, url: str) -> Optional[dict]:
        """
        Tek bir haberi parse et.
        Returns dict with keys:
            title, content, published_at (datetime), url, source_key, source_name
        """
        pass

    def scrape(self) -> list[dict]:
        """Tum haberleri cek ve dondur"""
        logger.info(f"[{self.source_key}] Scraping basliyor...")
        urls = self.get_news_urls()
        logger.info(f"[{self.source_key}] {len(urls)} URL bulundu.")

        articles = []
        for url in urls:
            article = self.parse_article(url)
            if article:
                # Tarih filtresi
                if article.get("published_at") and article["published_at"] < self.cutoff_date:
                    logger.debug(f"Eski haber atlandi: {url}")
                    continue
                articles.append(article)

        logger.info(f"[{self.source_key}] {len(articles)} haber islendi.")
        return articles

    def _make_article(self, title, content, published_at, url) -> dict:
        return {
            "title": title,
            "content": content,
            "published_at": published_at,
            "url": url,
            "source_key": self.source_key,
            "source_name": self.source_name,
        }
