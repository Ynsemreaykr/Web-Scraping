"""
Kategori prototipleri: paraphrase-multilingual-MiniLM-L12-v2 ile çok dilli
çapa cümleleri kodlanır; haber metnine kosinüs benzerliği ek puan üretir.

Neden sadece gömme değil?
- Etiketli Türkçe haber veri seti yok; saf vektör sınıflandırıcı eğitmek güvenilir olmaz.
- Çapa + anahtar kelime birleşimi, yanlış pozitifleri (ör. SEDAŞ geçen her metin)
  azaltırken modelin anlamsal yakınlığından yararlanır.
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np

from processing.duplicate_detector import get_model

logger = logging.getLogger(__name__)

# Her kategori: 3-4 kısa Türkçe tanım (gerçek olay tipi)
_CATEGORY_ANCHORS: Dict[str, list] = {
    "Trafik Kazasi": [
        "Karayolunda trafik kazası oldu, araçlar çarpıştı, yaralı ve ölü var.",
        "Otoyolda zincirleme kaza meydana geldi, yol trafiğe kapandı.",
        "Motosiklet veya otomobil kaza yaptı, sürücü hastaneye kaldırıldı.",
        "TEM otoyolunda kamyon devrildi, araçlar birbirine çarptı.",
    ],
    "Yangin": [
        "Bina veya işyerinde yangın çıktı, itfaiye alevlere müdahale etti.",
        "Elektrik kontağından yangın çıktı, duman yükseldi, söndürme çalışması.",
        "Orman veya araç yandı, yangın ihbarı verildi.",
    ],
    "Elektrik Kesintisi": [
        "Elektrik kesintisi programı açıklandı, mahallelerde enerji verilmeyecek.",
        "Trafo arızası nedeniyle elektrik kesildi, abonelerin dikkatine duyuru.",
        "Planlı veya plansız elektrik kesintisi, şebekede bakım çalışması.",
    ],
    "Hirsizlik": [
        "Ev veya işyerinden hırsızlık yapıldı, para ve eşya çalındı.",
        "Soygun veya kapkaç olayı, hırsız polis tarafından yakalandı.",
        "Çalıntı motosiklet veya kablo hırsızlığı soruşturması.",
    ],
    "Suc ve Cinayet": [
        "Cinayet soruşturması, silahlı saldırı veya bıçaklı kavga, tutuklama.",
        "Dolandırıcılık veya narkotik operasyonu, mahkeme davası, hapis cezası.",
        "Öldürme olayı, şüpheli gözaltına alındı, adliye kararı.",
    ],
    "Kulturel Etkinlikler": [
        "Şehirde konser, tiyatro oyunu veya festival düzenlendi.",
        "Müzede sergi açıldı, kültür merkezinde sanat etkinliği var.",
        "Kitap fuarı, müzik dinletisi veya geleneksel şenlik yapıldı.",
    ],
}

_emb_cache: Dict[str, np.ndarray] = {}


def _ensure_embeddings() -> None:
    global _emb_cache
    if _emb_cache:
        return
    model = get_model()
    for cat, phrases in _CATEGORY_ANCHORS.items():
        mat = model.encode(phrases, normalize_embeddings=True)
        _emb_cache[cat] = np.asarray(mat, dtype=np.float32)
    logger.info("Kategori çapa gömmeleri hazır (%s kategori).", len(_emb_cache))


def semantic_category_similarities(text: str) -> Dict[str, float]:
    """
    Metin (başlık + gövde özü) için her kategorinin [0,1] aralığında
    en yüksek çapa benzerliği.
    """
    t = (text or "").strip()
    if len(t) < 8:
        return {c: 0.0 for c in _CATEGORY_ANCHORS}
    _ensure_embeddings()
    model = get_model()
    # Uzun metinlerde ilk ~2000 karakter yeterli, hız için
    snippet = t[:2000]
    doc = model.encode(snippet, normalize_embeddings=True)
    doc = np.asarray(doc, dtype=np.float32).reshape(-1)
    out: Dict[str, float] = {}
    for cat, mat in _emb_cache.items():
        sims = np.dot(mat, doc)
        out[cat] = float(np.clip(np.max(sims), 0.0, 1.0))
    return out
