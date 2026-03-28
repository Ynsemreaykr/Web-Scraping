import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ─── Anahtar Kelimeler (raporda listelenecek) ──────────────────────────────────
KEYWORDS = {
    "Trafik Kazasi": [
        "kaza", "trafik kazasi", "trafik kazası", "çarptı", "carpti",
        "çarpışma", "carpısma", "zincirleme", "devrildi", "takla",
        "yaralandi", "yaralandı", "hayatini kaybetti", "hayatını kaybetti",
        "ölümlü kaza", "olumlu kaza", "motosiklet", "bisiklet",
        "araç çarpti", "araç carpti", "yayaya çarptı", "yayaya carpti",
        "kırmızı ışık", "kirmizi isik", "makas attı", "makas atti",
        "alkollü sürücü", "alkolu surucu", "kontrolden çıktı",
        "virajda", "kapışma", "kamyon", "tır devrildi", "tir devrildi",
    ],
    "Yangin": [
        "yangın", "yangin", "alev aldı", "alev aldi", "alev topuna döndü",
        "alevler", "itfaiye", "söndürüldü", "sonduruldu",
        "dumanlar", "yanarken", "tutuştu", "tutusdu", "küle döndü",
        "kule dondu", "yandı", "yandi", "çıkan yangın", "cikan yangin",
        "brülör", "brulor", "orman yangını", "orman yangini",
        "araç yandı", "arac yandi", "soba", "baca", "elektrik yangını",
    ],
    "Elektrik Kesintisi": [
        "elektrik kesintisi", "enerji kesintisi", "elektrik kesildi",
        "elektrik yok", "karanlıkta kaldı", "karanlikta kaldi",
        "trafo", "SEDAŞ", "SEDAS", "arıza", "ariza",
        "elektrik bağlantısı", "hat arızası", "hat arizasi",
        "akım kesildi", "akim kesildi", "güç kesintisi", "guc kesintisi",
        "enerji arzı", "elektrik arzı", "elektrik altyapı",
        "kesinti yaşandı", "kesinti yasandi",
    ],
    "Hirsizlik": [
        "hırsızlık", "hirsizlik", "çalındı", "calindi", "soygun",
        "gasp", "kapkaç", "kapkac", "dolandırıcı", "dolandirici",
        "yankesici", "zimmet", "hırsız", "hirsiz",
        "evden çalındı", "evden calindi", "araç çalındı", "arac calindi",
        "kırıp geçti", "kirip gecti", "soyuldu", "dolandırma", "sahte",
        "hırsızlık şüphelisi", "gözaltı",
    ],
    "Kulturel Etkinlikler": [
        "festival", "konser", "sergi", "tiyatro", "etkinlik",
        "kutlama", "şenlik", "senlik", "müzik", "muzik",
        "gösteri", "gosteri", "açılış töreni", "acilis toreni",
        "kültürel", "kulturel", "sanat", "dans", "resital",
        "fuar", "panayır", "panayir", "turnuva", "yarışma", "yarisma",
        "kariyer", "konferans", "seminer", "panel", "söyleşi",
        "kermese", "kermes", "spor etkinliği", "maraton",
    ],
}

# Oncelik sirasi (ilk eslesen kategori kullanilir)
PRIORITY_ORDER = [
    "Trafik Kazasi",
    "Yangin",
    "Elektrik Kesintisi",
    "Hirsizlik",
    "Kulturel Etkinlikler",
]

# Goruntuleme isimleri (TR)
CATEGORY_DISPLAY = {
    "Trafik Kazasi": "Trafik Kazası",
    "Yangin": "Yangın",
    "Elektrik Kesintisi": "Elektrik Kesintisi",
    "Hirsizlik": "Hırsızlık",
    "Kulturel Etkinlikler": "Kültürel Etkinlikler",
}


class NewsClassifier:
    """Anahtar kelime tabanli haber siniflandirici"""

    def classify(self, title: str, content: str) -> Optional[str]:
        """
        Oncelik sirasina gore ilk eslesen kategoriyi dondur.
        Hic eslesmezse None dondurur.
        """
        combined = f"{title} {content}".lower()

        for category in PRIORITY_ORDER:
            for kw in KEYWORDS[category]:
                if kw.lower() in combined:
                    logger.debug(f"Kategori: {category} (anahtar: '{kw}')")
                    return category

        logger.debug("Kategori bulunamadi.")
        return None

    def classify_with_scores(self, title: str, content: str) -> dict:
        """Her kategorideki eslesen anahtar kelime sayisini dondur"""
        combined = f"{title} {content}".lower()
        scores = {}
        for category, keywords in KEYWORDS.items():
            matched = [kw for kw in keywords if kw.lower() in combined]
            scores[category] = {"count": len(matched), "matched": matched}
        return scores


classifier = NewsClassifier()
