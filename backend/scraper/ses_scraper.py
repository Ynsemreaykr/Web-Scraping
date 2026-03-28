import logging
import re
import time
from datetime import datetime
from typing import Optional, List
from scraper.base_scraper import BaseScraper, HEADERS
from scraper.cagdas_scraper import MONTH_MAP

logger = logging.getLogger(__name__)


class SesScraper(BaseScraper):
    """
    Ses Kocaeli scraper.
    Site Cloudflare korumalı olduğu için farklı bir User-Agent ve
    ek header'larla denenecek. Basarisiz olursa sessizce atlanır.
    """
    source_key = "seskocaeli"
    source_name = "Ses Kocaeli"
    base_url = "https://www.seskocaeli.com"

    NEWS_PATTERN = re.compile(r'/haber/\d+/[^"\s]+|/[a-z-]+-\d+\.html')

    CF_HEADERS = {
        **HEADERS,
        "sec-ch-ua": '"Google Chrome";v="122", "Chromium";v="122"',
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "upgrade-insecure-requests": "1",
        "cache-control": "max-age=0",
    }

    def get_news_urls(self) -> List[str]:
        urls = set()
        try:
            self.session.headers.update(self.CF_HEADERS)
            soup = self.get_page(self.base_url)
            if not soup:
                logger.warning("[seskocaeli] Ana sayfa alinamadi (Cloudflare?)")
                return []

            for a in soup.find_all('a', href=True):
                href = a['href']
                if not href.startswith('http'):
                    href = self.base_url + href
                if self.NEWS_PATTERN.search(href) and self.base_url in href:
                    urls.add(href.rstrip('/'))

            logger.info(f"[seskocaeli] {len(urls)} URL bulundu.")
        except Exception as e:
            logger.warning(f"[seskocaeli] URL listesi alinamadiL {e}")
        return list(urls)[:80]

    def parse_article(self, url: str) -> Optional[dict]:
        soup = self.get_page(url)
        if not soup:
            return None
        h1 = soup.find('h1')
        if not h1:
            return None
        title = h1.get_text(strip=True)
        if not title:
            return None

        content_tag = (
            soup.find('div', class_=re.compile(r'news-detail|haber|content|entry|article', re.I))
            or soup.find('article')
        )
        content = content_tag.get_text(separator=' ', strip=True) if content_tag else title
        published_at = self._parse_date(soup)
        return self._make_article(title, content, published_at, url)

    def _parse_date(self, soup) -> datetime:
        t = soup.find('time')
        if t:
            val = t.get('datetime') or t.get_text(strip=True)
            dt = self._try_parse(val)
            if dt:
                return dt
        m = soup.find('meta', property='article:published_time')
        if m:
            dt = self._try_parse(m.get('content', ''))
            if dt:
                return dt
        return datetime.utcnow()

    def _try_parse(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                return datetime.strptime(text[:len(fmt)], fmt)
            except Exception:
                pass
        m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
        if m:
            try:
                return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except Exception:
                pass
        return None
