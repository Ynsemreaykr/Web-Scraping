import re
import logging
from config import Config

logger = logging.getLogger(__name__)

# Kocaeli ilçeleri - genisletilmis liste (aksan varyasyonlari dahil)
DISTRICTS = [
    "İzmit", "Izmit", "Gebze", "Darıca", "Darica",
    "Çayırova", "Cayirova", "Dilovası", "Dilovasi",
    "Gölcük", "Golcuk", "Karamürsel", "Karamursel",
    "Kandıra", "Kandira", "Kartepe", "Başiskele", "Basiskele",
    "Derince", "Körfez", "Korfez",
]

# Mahalle / semt pattern'leri
NEIGHBORHOOD_PATTERNS = [
    r"(\w+)\s+mahallesi",
    r"(\w+)\s+mah\.",
    r"(\w+)\s+semti",
    r"(\w+)\s+sokak",
    r"(\w+)\s+sk\.",
    r"(\w+)\s+caddesi",
    r"(\w+)\s+cad\.",
    r"(\w+)\s+bulvari",
    r"(\w+)\s+blv\.",
]

# Adres blogu pattern'i (cadde/sokak no vb.)
ADDRESS_BLOCK_PATTERN = re.compile(
    r"(?:(?:[\w\s]+)(?:mahallesi|mah\.|sokak|sk\.|cadde|cad\.|bulvar|blv\.|cd\.)\s*(?:no[:\s]?\d+)?)",
    flags=re.IGNORECASE | re.UNICODE,
)


class LocationExtractor:
    """
    Haber metninden konum bilgisi cikarir.
    Oncelik: sokak/mahalle > ilce > Kocaeli genel
    """

    def extract(self, text: str) -> dict:
        """
        Returns:
            {
                "location_text": str,   # Ham konum metni
                "district": str | None, # Ilce
                "address": str | None,  # Tam adres (mahalle/sokak)
                "geocode_query": str,   # Geocoding icin kullanilacak sorgu
            }
        """
        if not text:
            return self._empty()

        result = self._empty()
        text_lower = text.lower()

        # 1) Ilce tespiti
        for district in DISTRICTS:
            if district.lower() in text_lower:
                result["district"] = district
                break

        # 2) Adres blogu tespiti (mahalle / sokak)
        address_match = ADDRESS_BLOCK_PATTERN.search(text)
        if address_match:
            result["address"] = address_match.group(0).strip()

        # 3) location_text olustur
        if result["address"] and result["district"]:
            result["location_text"] = f"{result['address']}, {result['district']}, Kocaeli"
        elif result["address"]:
            result["location_text"] = f"{result['address']}, Kocaeli"
        elif result["district"]:
            result["location_text"] = f"{result['district']}, Kocaeli"
        else:
            # Kocaeli gelsin mi? Hayir - raporlama icin None birak
            return self._empty()

        # 4) Geocoding sorgusu
        result["geocode_query"] = result["location_text"]

        logger.debug(f"Konum tespit edildi: {result['location_text']}")
        return result

    def _empty(self) -> dict:
        return {
            "location_text": None,
            "district": None,
            "address": None,
            "geocode_query": None,
        }


extractor = LocationExtractor()
