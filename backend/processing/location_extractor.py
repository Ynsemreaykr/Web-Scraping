import re
import logging
from typing import Optional

from config import Config
from processing.text_utils import tr_lower

logger = logging.getLogger(__name__)

_MAH_WORD = r"[\w\sçğıöşüÇĞİÖŞÜ\.']{1,40}"

MAHALLE_PATTERN = re.compile(
    rf"(?P<block>{_MAH_WORD}?)\s+mahallesi(?:'nde|'nden|'ne|'de|'den)?",
    flags=re.IGNORECASE | re.UNICODE,
)

SOKAK_CADRE = re.compile(
    rf"(?P<block>{_MAH_WORD}?)\s+(?:sokak|sk\.|sokağı|caddesi|cad\.|cadde|bulvarı|bulvar|blv\.)\s*(?:no[:\s.]?\s*\d+)?",
    flags=re.IGNORECASE | re.UNICODE,
)

LANDMARK_PATTERNS = [
    re.compile(r"[\w\sçğıöşü]{3,40}?\s+otogarı", re.I | re.U),
    re.compile(r"[\w\sçğıöşü]{3,40}?\s+otogar", re.I | re.U),
    re.compile(r"[\w\sçğıöşü]{3,40}?\s+terminali?", re.I | re.U),
    re.compile(r"[\w\sçğıöşü]{3,40}?\s+köprüsü", re.I | re.U),
    re.compile(r"organize\s+sanayi", re.I | re.U),
    re.compile(r"OSB(?:'|\s|$)", re.I | re.U),
    re.compile(r"[\w\sçğıöşü]{2,30}?\s+sanayi\s+sitesi", re.I | re.U),
    re.compile(r"(?:kent|şehir)\s+meydanı", re.I | re.U),
    re.compile(r"(?:kent|sehir)\s+meydani", re.I | re.U),
    re.compile(r"kültür\s+merkezi", re.I | re.U),
    re.compile(r"kultur\s+merkezi", re.I | re.U),
]

_LOCAL_HINTS = (
    "ilimizde",
    "ilimiz",
    "kocaelide",
    "kocaeli'de",
    "kocaelideki",
    "buyuksehir",
    "büyükşehir",
    "belediyesi",
    "belediye başkanı",
    "belediye baskani",
    "kbb",
    "kentte",
    "şehrimizde",
    "sehrimizde",
    "körfezde",
    "korfezde",
)

# ── Mahalle / semt / yer adı → ilçe eşleme ──────────────────────
NEIGHBORHOOD_TO_DISTRICT = {
    # Gebze
    "güzeller": "Gebze", "guzeller": "Gebze",
    "pelitli": "Gebze", "tavşanlı": "Gebze", "tavsanli": "Gebze",
    "arapçeşme": "Gebze", "arapcesme": "Gebze",
    "osman yılmaz": "Gebze", "osman yilmaz": "Gebze",
    "güzeller osb": "Gebze", "guzeller osb": "Gebze",
    "gebze osb": "Gebze", "gebze organize": "Gebze",
    "eskihisar": "Gebze", "muallimköy": "Gebze", "muallimkoy": "Gebze",
    "balçık": "Gebze", "balcik": "Gebze",
    "sultanorhan": "Gebze", "cayırova": "Gebze",
    "tübitak": "Gebze", "tubitak": "Gebze",
    "güvercinlik": "Gebze", "guvercindere": "Gebze",
    "darıca sınır": "Gebze",
    # Darıca
    "bayramoğlu": "Darica", "bayramoglu": "Darica",
    "nene hatun": "Darica",
    "osmangazi": "Darica",
    "kazım karabekir": "Darica", "kazim karabekir": "Darica",
    "bağlarbaşı": "Darica", "baglarbasi": "Darica",
    "piri reis": "Darica",
    # Gölcük
    "donanma": "Golcuk",
    "değirmendere": "Golcuk", "degirmendere": "Golcuk",
    "ihsaniye": "Golcuk", "İhsaniye": "Golcuk",
    "halıdere": "Golcuk", "halidere": "Golcuk",
    "ulaşlı": "Golcuk", "ulasli": "Golcuk",
    "yazlık": "Golcuk", "yazlik": "Golcuk",
    "donanma komutanlığ": "Golcuk", "donanma komutanlig": "Golcuk",
    "deniz üssü": "Golcuk", "deniz ussu": "Golcuk",
    # Körfez
    "hereke": "Korfez", "yarımca": "Korfez", "yarimca": "Korfez",
    "kirazlıyalı": "Korfez", "kirazliyali": "Korfez",
    "tütünçiftlik": "Korfez", "tutunciftlik": "Korfez",
    "kışladüzü": "Korfez", "kisladuzu": "Korfez",
    # Derince
    "çenedağ": "Derince", "cenedag": "Derince",
    "ibn-i sina": "Derince", "ibni sina": "Derince",
    "deniz harp": "Derince",
    "derince limanı": "Derince", "derince limani": "Derince",
    "sırrıpaşa": "Derince", "sirripasa": "Derince",
    "çavuşlu": "Derince", "cavuslu": "Derince",
    # Kartepe
    "maşukiye": "Kartepe", "masukiye": "Kartepe",
    "suadiye": "Kartepe", "acısu": "Kartepe", "acisu": "Kartepe",
    "nusretiye": "Kartepe",
    "uzuntarla": "Kartepe",
    "sapanca yolu": "Kartepe",
    # Kandıra
    "akçakoca": "Kandira", "akcakoca": "Kandira",
    "kerpe": "Kandira", "cebeci": "Kandira",
    "bağırganlı": "Kandira", "bagirganli": "Kandira",
    # Karamürsel
    "oluklu": "Karamursel",
    "yalakdere": "Karamursel",
    "kaytazdere": "Karamursel",
    "çamçukur": "Karamursel", "camcukur": "Karamursel",
    "akmeşe": "Karamursel", "akmese": "Karamursel",
    # Başiskele
    "yeniköy": "Basiskele", "yenikoy": "Basiskele",
    "kullar": "Basiskele",
    "serdar": "Basiskele",
    "yeşilkent": "Basiskele", "yesilkent": "Basiskele",
    "ovacık": "Basiskele", "ovacik": "Basiskele",
    # Çayırova
    "akse": "Cayirova",
    "şekerpınar": "Cayirova", "sekerpinar": "Cayirova",
    "çayırova osb": "Cayirova", "cayirova osb": "Cayirova",
    # Dilovası
    "diliskelesi": "Dilovasi",
    "dilovası osb": "Dilovasi", "dilovasi osb": "Dilovasi",
    "muallim": "Dilovasi",
    "tuzla sınırı": "Dilovasi",
    # İzmit (merkez) — bunlar gerçekten İzmit'e ait semtler
    "yahya kaptan": "Izmit",
    "kozluk": "Izmit",
    "mehmet ali paşa": "Izmit", "mehmet ali pasa": "Izmit",
    "çukurbağ": "Izmit", "cukurbag": "Izmit",
    "hacıhızır": "Izmit", "hacihizir": "Izmit",
    "yenidoğan": "Izmit", "yenidogan": "Izmit",
    "tavşantepe": "Izmit", "tavsantepe": "Izmit",
    "gündoğdu": "Izmit", "gundogdu": "Izmit",
    "cedit": "Izmit",
    "28 haziran": "Izmit",
    "yenişehir": "Izmit", "yenisehir": "Izmit",
    "kuruçeşme": "Izmit", "kurucesme": "Izmit",
    "topçular": "Izmit", "topcular": "Izmit",
    "sdkm": "Izmit",
    "kent meydanı": "Izmit", "kent meydani": "Izmit",
    "millet bahçe": "Izmit", "millet bahce": "Izmit",
    "seka park": "Izmit",
    "bekirpaşa": "Izmit", "bekirpasa": "Izmit",
    "yuvacık": "Izmit", "yuvacik": "Izmit",
}

_URL_DISTRICT_HINTS = {
    "gebze": "Gebze",
    "darica": "Darica", "darıca": "Darica",
    "golcuk": "Golcuk", "gölcük": "Golcuk",
    "korfez": "Korfez", "körfez": "Korfez",
    "derince": "Derince",
    "kartepe": "Kartepe",
    "kandira": "Kandira", "kandıra": "Kandira",
    "karamursel": "Karamursel", "karamürsel": "Karamursel",
    "basiskele": "Basiskele", "başiskele": "Basiskele",
    "cayirova": "Cayirova", "çayırova": "Cayirova",
    "dilovasi": "Dilovasi", "dilovası": "Dilovasi",
    "izmit": "Izmit",
}


class LocationExtractor:
    def extract(
        self,
        text: str,
        title: str = "",
        *,
        assume_local: bool = False,
        category_hint: Optional[str] = None,
        url: str = "",
    ) -> dict:
        if not text and not title:
            return self._empty()

        result = self._empty()
        full_raw = f"{title} {text}".strip()
        text_lower = tr_lower(text)
        title_lower = tr_lower(title) if title else ""
        full_lower = tr_lower(full_raw)
        url_lower = tr_lower(url) if url else ""

        tr_map = {
            "Izmit": ["izmit", "İzmit"],
            "Gebze": ["gebze"],
            "Darica": ["darıca", "darica"],
            "Cayirova": ["çayırova", "cayirova"],
            "Dilovasi": ["dilovası", "dilovasi"],
            "Golcuk": ["gölcük", "golcuk"],
            "Karamursel": ["karamürsel", "karamursel"],
            "Kandira": ["kandıra", "kandira"],
            "Kartepe": ["kartepe"],
            "Basiskele": ["başiskele", "basiskele"],
            "Derince": ["derince"],
            "Korfez": ["körfez", "korfez"],
        }

        district_scores = {std: 0 for std in tr_map.keys()}
        kocaeli_count = full_lower.count("kocaeli")

        # 1) Ilce adı doğrudan metinde geçiyor mu
        for std, variants in tr_map.items():
            for var in variants:
                if var in title_lower:
                    district_scores[std] += 100
                district_scores[std] += full_lower.count(var)
                loc_pat = rf"(?u)(?<![a-zçğıöşü]){re.escape(var)}(?:'(?:te|ta|de|da|ten|tan|nin|nın|nün|nun)|te|de|da|ten|tan)\b"
                if re.search(loc_pat, full_lower):
                    district_scores[std] += 35
                if re.search(loc_pat, title_lower):
                    district_scores[std] += 40

        # 2) Mahalle / semt adından ilçe çıkar
        for neighborhood, district in NEIGHBORHOOD_TO_DISTRICT.items():
            if neighborhood in title_lower:
                district_scores[district] += 80
            elif neighborhood in full_lower:
                district_scores[district] += 30

        # 3) URL'den ilçe ipucu
        if url_lower:
            for hint, district in _URL_DISTRICT_HINTS.items():
                if hint in url_lower:
                    district_scores[district] += 20

        best_district = None
        best_score = 0
        for std, score in district_scores.items():
            if score > best_score:
                best_score = score
                best_district = std

        if best_score > 0:
            result["district"] = best_district

        # --- Dis sehir kontrolu: category varsayimlarından ONCE ---
        other_cities = [
            "istanbul", "ankara", "izmir", "rize", "antalya", "bursa", "adana",
            "konya", "gaziantep", "mersin", "niğde", "nigde", "muğla", "mugla",
            "van", "diyarbakır", "diyarbakir", "şanlıurfa", "sanliurfa",
            "eskişehir", "eskisehir", "trabzon", "samsun", "malatya",
            "kahramanmaraş", "kahramanmaras", "tekirdağ", "tekirdag",
            "balıkesir", "balikesir", "aydın", "aydin", "denizli", "kayseri",
            "sakarya", "ordu", "polatlı", "polatli", "düzce", "duzce", "bolu",
            "yalova", "çanakkale", "canakkale", "edirne", "kırklareli",
            "kirklareli", "hatay", "tokat", "sivas", "erzurum", "elazığ",
            "elazig", "okmeydanı", "okmeydani", "gayrettepe", "beşiktaş",
            "besiktas", "kadıköy", "kadikoy", "üsküdar", "uskudar", "beyoğlu",
            "beyoglu", "şişli", "sisli", "bakırköy", "bakirkoy", "fatih",
        ]
        if not result["district"] and kocaeli_count == 0:
            for city in other_cities:
                if city in title_lower or full_lower.count(city) >= 2:
                    logger.info("Dis sehir haberi tespit edildi (%s), haritadan eleniyor.", city)
                    return self._empty()

        # --- Yerel ipucu / category varsayimi (dis sehir elendikten sonra) ---
        if assume_local and not result["district"] and kocaeli_count == 0:
            if any(h in full_lower for h in _LOCAL_HINTS):
                kocaeli_count = 1

        if (
            assume_local
            and category_hint
            and not result["district"]
            and kocaeli_count == 0
        ):
            if category_hint == "Elektrik Kesintisi" and re.search(
                r"(?u)kesinti|elektrik|sedas|sedaş|trafo|abone|mahalle|enerji|şebeke|sebeke|arıza|ariza|duyuru",
                full_lower,
            ):
                kocaeli_count = 1
            if category_hint == "Kulturel Etkinlikler" and re.search(
                r"(?u)konser|etkinlik|sergi|tiyatro|festival|kültür|kultur|sanat|müze|muze|"
                r"gösteri|gosteri|şölen|solen|atölye|atolye|dinleti|millet bahçe|millet bahce",
                full_lower,
            ):
                kocaeli_count = 1
            if category_hint == "Suc ve Cinayet" and re.search(
                r"(?u)cinayet|katliam|narkotik|saldırı|saldirı|gözaltı|gozaltı|tutuklandı|"
                r"tutuklandi|emniyet|jandarma|operasyon",
                full_lower,
            ):
                kocaeli_count = 1

        if (
            assume_local
            and category_hint
            and category_hint in getattr(Config, "NEWS_CATEGORIES", ())
            and not result["district"]
            and kocaeli_count == 0
        ):
            kocaeli_count = 1

        address_parts = []

        m_mah = MAHALLE_PATTERN.search(full_raw)
        if m_mah:
            block = (m_mah.group("block") or "").strip()
            mah = m_mah.group(0).strip()
            if len(block) >= 2:
                address_parts.append(f"{block.strip()} Mahallesi")
            else:
                address_parts.append(mah)
            # Mahalle adından ilçe çıkarma (henüz ilçe yoksa)
            if not result["district"] and block:
                block_lower = tr_lower(block)
                for nbr, dist in NEIGHBORHOOD_TO_DISTRICT.items():
                    if nbr in block_lower:
                        result["district"] = dist
                        break

        m_sk = SOKAK_CADRE.search(full_raw)
        if m_sk:
            block = (m_sk.group("block") or "").strip()
            line = m_sk.group(0).strip()
            if line not in " ".join(address_parts):
                address_parts.append(line)

        if not address_parts:
            for lp in LANDMARK_PATTERNS:
                lm = lp.search(full_raw)
                if lm:
                    address_parts.append(lm.group(0).strip())
                    break

        if address_parts:
            result["address"] = ", ".join(address_parts)

        if result["address"] and result["district"]:
            result["location_text"] = f"{result['address']}, {result['district']}, Kocaeli"
        elif result["address"]:
            result["location_text"] = f"{result['address']}, Kocaeli"
        elif result["district"]:
            result["location_text"] = f"{result['district']}, Kocaeli"
        else:
            if kocaeli_count > 0:
                result["location_text"] = "Kocaeli"
                result["geocode_fallback"] = True
            else:
                return self._empty()

        result["geocode_query"] = f"{result['location_text']}, Türkiye"
        logger.debug("Konum: %s", result["location_text"])
        return result

    def _empty(self) -> dict:
        return {
            "location_text": None,
            "district": None,
            "address": None,
            "geocode_query": None,
            "geocode_fallback": False,
        }


extractor = LocationExtractor()
