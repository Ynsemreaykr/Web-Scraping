import requests
import time
import logging
import re
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List, Any, Iterable
from urllib.parse import urljoin

try:
    import cloudscraper
    _HAS_CLOUDSCRAPER = True
except ImportError:
    _HAS_CLOUDSCRAPER = False

from bs4 import BeautifulSoup, Tag
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

MONTH_MAP = {
    "ocak": 1,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "agustos": 8,
    "eylul": 9,
    "ekim": 10,
    "kasim": 11,
    "aralik": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# Yayın tarihi için meta (property veya name)
_META_PUBLISHED = (
    ("property", "article:published_time"),
    ("property", "og:published_time"),
    ("property", "og:updated_time"),
    ("name", "datePublished"),
    ("name", "pubdate"),
    ("name", "publish-date"),
    ("name", "date"),
    ("name", "DC.date.issued"),
    ("name", "parsely-pub-date"),
)


def _iter_jsonld_dates(obj: Any) -> Iterable[str]:
    keys = ("datePublished", "dateCreated", "uploadDate", "dateModified")
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                yield v
        for v in obj.values():
            yield from _iter_jsonld_dates(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_jsonld_dates(item)


class BaseScraper(ABC):
    """Tum scraperlar icin temel sinif"""

    source_key: str = ""
    source_name: str = ""
    base_url: str = ""

    def __init__(self):
        if _HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
        else:
            self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cutoff_date = datetime.utcnow() - timedelta(days=Config.SCRAPE_DAYS)

    def _parse_date_from_url(self, page_url: str) -> Optional[datetime]:
        """URL icindeki /YYYY/MM/DD/ veya -DD-MM-YYYY gibi desenler."""
        if not page_url:
            return None
        m = re.search(r"/(\d{4})/(\d{1,2})/(\d{1,2})(?:/|$)", page_url)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
        m = re.search(r"[/_-](\d{1,2})[.\-](\d{1,2})[.\-](\d{4})(?:[/_\-]|\.html|$)", page_url)
        if m:
            try:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y >= 2000 and 1 <= mo <= 12 and 1 <= d <= 31:
                    return datetime(y, mo, d)
            except ValueError:
                pass
        return None

    def _parse_jsonld_scripts(self, soup: BeautifulSoup) -> Optional[datetime]:
        for s in soup.find_all("script", type=lambda x: x and "ld+json" in x.lower()):
            raw = (s.string or s.get_text() or "").strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for d_str in _iter_jsonld_dates(data):
                dt = self._try_parse(d_str)
                if dt:
                    return dt
        return None

    def _parse_meta_dates(self, soup: BeautifulSoup) -> Optional[datetime]:
        for attr, key in _META_PUBLISHED:
            m = soup.find("meta", attrs={attr: key})
            if not m:
                continue
            content = (m.get("content") or "").strip()
            if not content:
                continue
            dt = self._try_parse(content)
            if dt:
                return dt
        return None

    def _parse_time_tag(self, soup: BeautifulSoup) -> Optional[datetime]:
        for t in soup.find_all("time"):
            val = (t.get("datetime") or "").strip()
            if val:
                dt = self._try_parse(val)
                if dt:
                    return dt
            text = t.get_text(separator=" ", strip=True)
            if text and re.search(r"\d{4}", text):
                dt = self._try_parse(text)
                if dt:
                    return dt
        return None

    def _parse_date(self, soup: BeautifulSoup, page_url: str = "") -> Optional[datetime]:
        """
        Yayin tarihi. Basarisizsa None (utcnow kullanilmaz — yanlis tarih onlenir).
        Siralama: JSON-LD ve meta once; saat-only <time> sona alinir.
        """
        dt = self._parse_jsonld_scripts(soup)
        if dt:
            return dt

        dt = self._parse_meta_dates(soup)
        if dt:
            return dt

        dt = self._parse_time_tag(soup)
        if dt:
            return dt

        for sel in [
            ".haber-tarih",
            ".news-date",
            ".post-date",
            ".article-date",
            ".published",
            ".tarih",
            ".info",
            ".date",
            ".pub-date",
            ".time",
            "[class*=date]",
            "[class*=time]",
        ]:
            tag = soup.select_one(sel)
            if tag:
                dt = self._try_parse(tag.get_text(separator=" ", strip=True))
                if dt:
                    return dt

        dt = self._parse_date_from_url(page_url)
        if dt:
            return dt

        logger.warning("[%s] Tarih cikarilamadi: %s", self.source_key, page_url[:80] if page_url else "")
        return None

    def _try_parse(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()

        if re.search(r"\d{4}-\d{2}-\d{2}", text):
            s = text.strip().replace("Z", "+00:00")
            if " " in s and "T" not in s[:11]:
                s = s.replace(" ", "T", 1)
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                pass
            m = re.match(
                r"(\d{4}-\d{2}-\d{2})[T ](\d{1,2}:\d{2}(?::\d{2})?)(?:\.\d+)?",
                text,
            )
            if m:
                try:
                    return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
                    except ValueError:
                        pass
            m = re.match(r"(\d{4}-\d{2}-\d{2})", text)
            if m:
                try:
                    return datetime.strptime(m.group(1), "%Y-%m-%d")
                except ValueError:
                    pass

        m_dot = re.search(
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{1,2}))?",
            text,
        )
        if m_dot:
            try:
                day, month, year = int(m_dot.group(1)), int(m_dot.group(2)), int(m_dot.group(3))
                hh = int(m_dot.group(4)) if m_dot.group(4) else 0
                mm = int(m_dot.group(5)) if m_dot.group(5) else 0
                return datetime(year, month, day, hh, mm)
            except ValueError:
                pass

        m_word = re.search(
            r"(\d{1,2})\s+([a-zA-ZğüşıöçĞÜŞİÖÇ]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{1,2}))?",
            text,
            re.IGNORECASE | re.UNICODE,
        )
        if m_word:
            day, month_str, year = m_word.group(1), m_word.group(2), m_word.group(3)
            hh = int(m_word.group(4)) if m_word.group(4) else 0
            mm = int(m_word.group(5)) if m_word.group(5) else 0
            norm = (
                month_str.lower()
                .replace("ğ", "g")
                .replace("ş", "s")
                .replace("ı", "i")
                .replace("ö", "o")
                .replace("ü", "u")
                .replace("ç", "c")
            )
            month = MONTH_MAP.get(norm) or MONTH_MAP.get(norm[:3])
            if month:
                try:
                    return datetime(int(year), month, int(day), hh, mm)
                except ValueError:
                    pass

        return None

    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            time.sleep(Config.REQUEST_DELAY)
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning("[%s] Sayfa hatasi: %s -> %s", self.source_key, url, e)
            return None

    def listing_urls(self) -> List[str]:
        """Cok sayfali haber listesi (ana sayfa + bolumler). Alt siniflar genisletir."""
        return [self.base_url.rstrip("/")]

    def _to_naive_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt
        try:
            return datetime.utcfromtimestamp(dt.timestamp())
        except (OSError, OverflowError, ValueError):
            return dt.replace(tzinfo=None)

    def _expand_listing_urls(self, pages: List[str]) -> List[str]:
        """Liste URL'lerine ?page=N ekler (tek parametre — 3x istek patlamasini onler)."""
        max_n = getattr(Config, "LISTING_PAGINATION_MAX", 1)
        if max_n <= 1:
            return pages
        out: List[str] = []
        seen = set()
        for raw in pages:
            p = raw.rstrip("/")
            if p not in seen:
                seen.add(p)
                out.append(p)
            for n in range(2, max_n + 1):
                sep = "&" if "?" in p else "?"
                for key in ("page", "sayfa"):
                    u = f"{p}{sep}{key}={n}"
                    if u not in seen:
                        seen.add(u)
                        out.append(u)
        return out

    def _collect_links(self, pattern: re.Pattern, pages: Optional[List[str]] = None) -> List[str]:
        """Birden fazla liste sayfasindan haber URL'lerini toplar."""
        pages = pages or self.listing_urls()
        pages = self._expand_listing_urls(pages)
        limit = getattr(Config, "MAX_ARTICLE_URLS_PER_SOURCE", 220)
        max_fetches = getattr(Config, "MAX_LISTING_PAGE_FETCHES", 50)
        urls: List[str] = []
        base = self.base_url.rstrip("/")
        fetches = 0
        empty_streak = 0
        for page in pages:
            if fetches >= max_fetches:
                logger.info(
                    "[%s] Liste tarama limiti (%s sayfa), toplanan link: %s",
                    self.source_key,
                    max_fetches,
                    len(urls),
                )
                break
            before = len(urls)
            fetches += 1
            soup = self.get_page(page)
            if not soup:
                empty_streak += 1
                if empty_streak >= 12:
                    logger.info("[%s] Ust uste bos/hatali liste; tarama kesiliyor.", self.source_key)
                    break
                continue
            for a in soup.find_all("a", href=True):
                href = (a.get("href") or "").strip()
                if not href or href.startswith("#") or "javascript:" in href.lower():
                    continue
                full = urljoin(base + "/", href)
                full = full.split("#")[0].rstrip("/")
                if not full.startswith(base):
                    continue
                if pattern.search(full) and full not in urls:
                    urls.append(full)
                if len(urls) >= limit:
                    return urls[:limit]
            if len(urls) == before:
                empty_streak += 1
                if empty_streak >= 10:
                    logger.info("[%s] Ard arda yeni link yok; liste taramasi sonlandiriliyor.", self.source_key)
                    break
            else:
                empty_streak = 0
        return urls[:limit]

    @abstractmethod
    def get_news_urls(self) -> List[str]:
        pass

    @abstractmethod
    def parse_article(self, url: str) -> Optional[dict]:
        pass

    def scrape(self) -> list[dict]:
        urls = self.get_news_urls()
        articles = []
        cutoff = self._to_naive_utc(self.cutoff_date) or self.cutoff_date
        for url in urls:
            article = self.parse_article(url)
            if not article:
                continue
            pub = self._to_naive_utc(article.get("published_at"))
            article["published_at"] = pub
            if pub is None:
                fb = self._parse_date_from_url(url)
                if fb:
                    pub = self._to_naive_utc(fb)
                    article["published_at"] = pub
            if pub is None:
                logger.info("[%s] Tarihsiz haber atlandi: %s", self.source_key, url[:70])
                continue
            if pub < cutoff:
                continue
            articles.append(article)
        return articles

    # ── Gelismis icerik cekme ──────────────────────────────────────

    _CONTENT_SELECTORS = [
        "div.news-detail-content",
        "div.news-content",
        "div.haber-detay-icerik",
        "div.haber-metni",
        "div.haber_metni",
        "div.haberMetni",
        "div.detay-icerik",
        "div.article-body",
        "div.entry-content",
        "div.post-content",
        "div.content-text",
        "div.news-text",
        "div[itemprop='articleBody']",
        "article",
    ]

    _CONTENT_CLASS_RE = re.compile(
        r"news[-_]?detail|haber[-_]?detay|haber[-_]?metin|article[-_]?body|"
        r"entry[-_]?content|post[-_]?content|content[-_]?text|news[-_]?text|"
        r"detail[-_]?content|icerik|article",
        re.IGNORECASE,
    )

    def _extract_content(self, soup: BeautifulSoup, title: str = "") -> str:
        """Sayfadan haber metnini robust sekilde ceker."""
        # 1. CSS selector ile dene
        for sel in self._CONTENT_SELECTORS:
            tag = soup.select_one(sel)
            if tag:
                text = self._clean_tag_text(tag)
                if len(text) > 60:
                    return text

        # 2. Class/id regex ile div ara
        for div in soup.find_all("div"):
            classes = " ".join(div.get("class", []))
            did = div.get("id", "")
            if self._CONTENT_CLASS_RE.search(classes + " " + did):
                text = self._clean_tag_text(div)
                if len(text) > 60:
                    return text

        # 3. Tum paragraflardan uzun metinleri topla
        paragraphs = []
        for p in soup.find_all("p"):
            txt = p.get_text(strip=True)
            if len(txt) > 30 and "cookie" not in txt.lower():
                paragraphs.append(txt)
        if paragraphs:
            combined = " ".join(paragraphs)
            if len(combined) > 60:
                return combined

        # 4. og:description fallback
        desc = self._extract_meta_description(soup)
        if desc and len(desc) > 20:
            return desc

        return title

    @staticmethod
    def _clean_tag_text(tag: Tag) -> str:
        """Tag icinden script/style cikarip temiz metin dondurur."""
        for unwanted in tag.find_all(["script", "style", "noscript", "iframe", "button"]):
            unwanted.decompose()
        text = tag.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if text in ("A A", "A  A", "AA"):
            return ""
        return text

    @staticmethod
    def _extract_meta_description(soup: BeautifulSoup) -> str:
        """og:description veya meta description dondurur."""
        for attr, key in [
            ("property", "og:description"),
            ("name", "description"),
            ("name", "twitter:description"),
        ]:
            m = soup.find("meta", attrs={attr: key})
            if m:
                content = (m.get("content") or "").strip()
                if content and len(content) > 15:
                    return content
        return ""

    def _make_article(self, title, content, published_at, url) -> dict:
        return {
            "title": title,
            "content": content,
            "published_at": published_at,
            "url": url,
            "source_key": self.source_key,
            "source_name": self.source_name,
        }
