import logging
import re
from typing import Optional, List
from scraper.base_scraper import BaseScraper, HEADERS

logger = logging.getLogger(__name__)


class SesScraper(BaseScraper):
    source_key = "seskocaeli"
    source_name = "Ses Kocaeli"
    base_url = "https://www.seskocaeli.com"
    NEWS_PATTERN = re.compile(r"/haber/\d+/[^\s]+|/[a-z-]+-\d+\.html")
    CF_HEADERS = {**HEADERS, "upgrade-insecure-requests": "1", "cache-control": "max-age=0"}

    def __init__(self):
        super().__init__()
        self.session.headers.update(self.CF_HEADERS)

    def listing_urls(self) -> List[str]:
        b = self.base_url.rstrip("/")
        return [
            b,
            f"{b}/kocaeli-trafik-haberleri",
            f"{b}/kocaeli-yangin-haberleri",
            f"{b}/kocaeli-asayis-haberleri",
            f"{b}/kocaeli-son-dakika-haberleri",
            f"{b}/kocaeli-gundem-haberleri",
            f"{b}/kocaeli-yasam-haberleri",
            f"{b}/kocaeli-spor-haberleri",
            f"{b}/kocaeli-ekonomi-haberleri",
            f"{b}/kocaeli-egitim-haberleri",
            f"{b}/kocaeli-kultur-sanat-haberleri",
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
