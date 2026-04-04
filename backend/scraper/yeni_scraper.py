import logging
import re
from typing import Optional, List
from scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class YeniScraper(BaseScraper):
    source_key = "yenikocaeli"
    source_name = "Yeni Kocaeli"
    base_url = "https://www.yenikocaeli.com"
    NEWS_PATTERN = re.compile(r"/haber/[^/]+/[^/]+/\d+\.html")

    def listing_urls(self) -> List[str]:
        b = self.base_url.rstrip("/")
        return [
            b,
            f"{b}/haber/guncel",
            f"{b}/haber/kocaeli",
            f"{b}/haber/yasam.html",
            f"{b}/haber/kultur.html",
            f"{b}/haber/egitim.html",
            f"{b}/haber/spor.html",
            f"{b}/haber/asayis.html",
            f"{b}/haber/trafik.html",
            f"{b}/haber/yangin.html",
            f"{b}/haber/enerji.html",
            f"{b}/haber/ekonomi.html",
            f"{b}/haber/siyaset.html",
            f"{b}/haber/magazin.html",
        ]

    def get_news_urls(self) -> List[str]:
        return self._collect_links(self.NEWS_PATTERN)

    def parse_article(self, url: str) -> Optional[dict]:
        soup = self.get_page(url)
        if not soup:
            return None
        h1 = soup.find("h1")
        if not h1:
            return None
        title = h1.get_text(strip=True)
        content = self._extract_content(soup, title)
        published_at = self._parse_date(soup, url)
        return self._make_article(title, content, published_at, url)
