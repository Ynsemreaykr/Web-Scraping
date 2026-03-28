import logging
import re
from datetime import datetime
from typing import Optional, List
from scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "ocak": 1, "subat": 2, "mart": 3, "nisan": 4,
    "mayis": 5, "haziran": 6, "temmuz": 7,
    "agustos": 8, "eylul": 9, "ekim": 10,
    "kasim": 11, "aralik": 12,
}


class CagdasScraper(BaseScraper):
    source_key = "cagdaskocaeli"
    source_name = "Çağdaş Kocaeli"
    base_url = "https://www.cagdaskocaeli.com.tr"

    # URL pattern: /haber/[id]/[slug]
    NEWS_PATTERN = re.compile(r'/haber/\d+/[^"\s]+')

    def get_news_urls(self) -> List[str]:
        urls = set()
        soup = self.get_page(self.base_url)
        if soup:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if not href.startswith('http'):
                    href = self.base_url + href
                if self.NEWS_PATTERN.search(href):
                    urls.add(href.rstrip('/'))
        return list(urls)[:100]

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

        # Icerik
        content_tag = (
            soup.find('div', class_=re.compile(r'news-detail|haber-detay|content|icerik|entry|article-body', re.I))
            or soup.find('article')
            or soup.find('div', id=re.compile(r'content|icerik|haber', re.I))
        )
        content = content_tag.get_text(separator=' ', strip=True) if content_tag else title

        published_at = self._parse_date(soup)
        return self._make_article(title, content, published_at, url)

    def _parse_date(self, soup) -> datetime:
        # <time datetime="...">
        t = soup.find('time')
        if t:
            val = t.get('datetime') or t.get_text(strip=True)
            dt = self._try_parse(val)
            if dt:
                return dt

        # meta
        m = soup.find('meta', property='article:published_time')
        if m:
            dt = self._try_parse(m.get('content', ''))
            if dt:
                return dt

        # Tarih span/div
        for sel in ['.date', '.pub-date', '.time', '.haber-tarih', '[class*=date]', '[class*=time]']:
            tag = soup.select_one(sel)
            if tag:
                dt = self._try_parse(tag.get_text(strip=True))
                if dt:
                    return dt

        return datetime.utcnow()

    def _try_parse(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        # ISO
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                return datetime.strptime(text[:len(fmt)], fmt)
            except Exception:
                pass
        # dd.mm.yyyy
        m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
        if m:
            try:
                return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except Exception:
                pass
        # TR: "25 Mart 2025"
        m2 = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', text, re.IGNORECASE)
        if m2:
            day, month_str, year = m2.groups()
            norm = month_str.lower()
            norm = norm.replace('ğ','g').replace('ş','s').replace('ı','i').replace('ö','o').replace('ü','u').replace('ç','c')
            month = MONTH_MAP.get(norm)
            if month:
                try:
                    return datetime(int(year), month, int(day))
                except Exception:
                    pass
        return None
