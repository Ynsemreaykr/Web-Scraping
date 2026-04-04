import re
import logging
import unicodedata

logger = logging.getLogger(__name__)


class TextCleaner:
    """HTML tag temizleme, bosluk normalizasyonu, karakter temizleme"""

    # Reklam/alakasiz bölüm ipuçlari (kaldırılacak satırlar)
    AD_PATTERNS = [
        r"reklam", r"sponsor", r"advertisement", r"cookie", r"çerez politika",
        r"abone ol", r"bülten", r"haber bülten", r"sosyal medya",
        r"paylaş", r"yorum yap", r"yorum ekle",
        r"bu haberi oylayin", r"haberi değerlendir",
        r"önerilen haberler", r"ilgili haberler",
        r"daha fazla haber", r"tüm haberler",
        r"whatsapp", r"facebook", r"twitter", r"instagram",
        r"© \d{4}", r"tüm hakları saklıdır",
    ]

    def clean(self, text: str) -> str:
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)

        # HTML tag temizligi
        text = self._remove_html_tags(text)

        # HTML entity decode
        text = self._decode_html_entities(text)

        # Reklam satirlarini kaldir
        text = self._remove_ad_lines(text)

        # Ozel karakter temizligi
        text = self._clean_special_chars(text)

        # Bosluk normalizasyonu
        text = self._normalize_whitespace(text)

        return text.strip()

    def _remove_html_tags(self, text: str) -> str:
        """HTML taglerini kaldir"""
        clean = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<style[^>]*>.*?</style>", " ", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", " ", clean)
        return clean

    def _decode_html_entities(self, text: str) -> str:
        """HTML entity'leri decode et"""
        entities = {
            "&amp;": "&", "&lt;": "<", "&gt;": ">",
            "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
            "&apos;": "'", "&#8216;": "'", "&#8217;": "'",
            "&#8220;": '"', "&#8221;": '"', "&#8211;": "-",
            "&#8212;": "—", "&#8230;": "...",
        }
        for entity, char in entities.items():
            text = text.replace(entity, char)
        return text

    def _remove_ad_lines(self, text: str) -> str:
        """Reklam ve alakasiz satirlari kaldir"""
        lines = text.splitlines()
        cleaned = []
        pattern = re.compile(
            "|".join(self.AD_PATTERNS), flags=re.IGNORECASE
        )
        for line in lines:
            stripped = line.strip()
            if stripped:
                # Eger satir 200 karakterden kucukse reklam/sosyal medya linki olma ihtimali yuksektir. Uzun ve paragraf ise kaldirma.
                if len(stripped) <= 200 and pattern.search(stripped):
                    continue
                cleaned.append(stripped)
        return "\n".join(cleaned)

    def _clean_special_chars(self, text: str) -> str:
        """Gereksiz ozel karakterleri temizle"""
        # Birden fazla noktalama isaretini tekile indir
        text = re.sub(r"\.{3,}", "...", text)
        text = re.sub(r"-{2,}", "-", text)
        text = re.sub(r"_{2,}", "_", text)
        # Kontrol karakterleri
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Bosluk normalizasyonu"""
        text = re.sub(r"\t", " ", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text


cleaner = TextCleaner()
