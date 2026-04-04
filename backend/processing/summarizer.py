"""
Embedding tabanlı akıllı extractive özetleyici.

Sentence-transformers modelini kullanarak her cümleyi başlıkla
karşılaştırır, en alakalı 2-3 cümleyi seçer.
"""

import re
import logging
import numpy as np
from typing import List, Optional

logger = logging.getLogger(__name__)

_SENT_RE = re.compile(r'(?<=[.!?…])\s+')

_JUNK = re.compile(
    r'(?i)^(?:A\s*A|paylaş|tweet|whatsapp|facebook|instagram|yazdir|font|'
    r'büyüt|küçült|reklam|banner|cookie|çerez|devamını oku|haberin devamı|'
    r'kaynak:\s*$|fotoğraf\s*:\s*$|video\s*:\s*$|editör\s*:\s*$)$'
)

_FILLER = re.compile(
    r'^(?:Edinilen\s+bilgi\w*\s+(?:ve\s+\w+\s+)?göre[,;:\s]*|'
    r'Al[ıi]nan\s+bilgi\w*\s+göre[,;:\s]*|'
    r'(?:Gazetemize|Bize)\s+ulaşan\s+bilgilere\s+göre[,;:\s]*|'
    r'AA\s+muhabirinin?\s+.*?göre[,;:\s]*|'
    r'İlgili\s+habere\s+göre[,;:\s]*)',
    re.IGNORECASE,
)

_BOILERPLATE = re.compile(
    r'(?i)(?:yorum\s+yaz|topluluk\s+kurallar|bu\s+içeriğe\s+yorum|'
    r'©\s*\d{4}|tüm\s+hakları\s+saklıdır)',
)

_BOILER_POLICE_OPEN = re.compile(
    r"(?i)^(?:Kocaeli\s+(?:İl\s+)?Emniyet\s+Müdürlüğü|"
    r"Kocaeli\s+İl\s+Jandarma\s+Komutanlığı|"
    r"İl\s+Emniyet\s+Müdürlüğü)\s+",
)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def _is_header(text: str) -> bool:
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return False
    upper_ratio = sum(1 for c in alpha if c.isupper()) / len(alpha)
    return upper_ratio > 0.65 and len(text) < 120


def _clean_sentences(content: str) -> List[str]:
    """İçeriği temizlenmiş cümle listesine dönüştür."""
    lines = content.split("\n")
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 12:
            continue
        if _JUNK.match(line):
            continue
        if _BOILERPLATE.search(line) and len(line) < 120:
            continue
        clean_lines.append(line)

    text = " ".join(clean_lines)
    if len(text) < 25:
        return []

    raw_sents = _SENT_RE.split(text)
    sentences = []
    for s in raw_sents:
        s = s.strip()
        if len(s) < 20:
            continue
        if _JUNK.match(s):
            continue
        if _is_header(s):
            continue
        s = _FILLER.sub("", s).strip()
        s = re.sub(
            r'^[A-ZÇĞİÖŞÜ0-9\s,;:\'\"]{8,60}?\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü])',
            '', s,
        ).strip()
        if len(s) < 20:
            continue
        if s and s[0].islower():
            s = s[0].upper() + s[1:]
        sentences.append(s)

    return sentences


def smart_summary(title: str, content: str, max_chars: int = 400) -> str:
    """
    Embedding-based akıllı özet: başlığa en benzer cümleleri seçer.
    Fallback olarak ilk cümleleri alır.
    """
    if not content or len(content.strip()) < 25:
        return ""
    if content.strip() in ("A A", "AA", "A  A"):
        return ""

    sentences = _clean_sentences(content)
    if not sentences:
        return ""

    if len(sentences) <= 2:
        result = " ".join(sentences)
        if len(result) > max_chars:
            result = _truncate(result, max_chars)
        return _finalize(result)

    try:
        model = _get_model()
        title_emb = model.encode(title, normalize_embeddings=True)
        sent_embs = model.encode(sentences, normalize_embeddings=True)

        sim_scores = np.dot(sent_embs, title_emb)

        position_bonus = np.array([
            1.0 / (1 + i * 0.25) for i in range(len(sentences))
        ])

        length_bonus = np.array([
            min(len(s) / 150, 1.0) for s in sentences
        ])

        final_scores = sim_scores * 0.55 + position_bonus * 0.30 + length_bonus * 0.15

        for i, s in enumerate(sentences):
            if _BOILER_POLICE_OPEN.match(s.strip()):
                final_scores[i] *= 0.22

        n_pick = 3
        ranked = sorted(
            range(len(sentences)),
            key=lambda i: final_scores[i],
            reverse=True,
        )
        picked = sorted(ranked[:n_pick])

        result = ""
        for idx in picked:
            candidate = f"{result} {sentences[idx]}".strip() if result else sentences[idx]
            if len(candidate) > max_chars:
                if not result:
                    result = _truncate(sentences[idx], max_chars)
                break
            result = candidate

    except Exception as e:
        logger.warning("Embedding özet hatası, fallback: %s", e)
        result = ""
        for s in sentences[:3]:
            candidate = f"{result} {s}".strip() if result else s
            if len(candidate) > max_chars:
                if not result:
                    result = _truncate(s, max_chars)
                break
            result = candidate

    return _finalize(result)


def _truncate(text: str, max_chars: int) -> str:
    words = text.split()
    truncated = ""
    for w in words:
        test = f"{truncated} {w}".strip() if truncated else w
        if len(test) > max_chars - 4:
            break
        truncated = test
    return (truncated or text[:max_chars - 4]).rstrip(",;: ") + "..."


def _finalize(text: str) -> str:
    result = text.strip()
    if not result:
        return ""
    result = re.sub(r'\s+[A-ZÇĞİÖŞÜ]\.\s*$', '...', result)
    result = re.sub(r'\s+[A-ZÇĞİÖŞÜ]\.[A-ZÇĞİÖŞÜ]\.\s*$', '...', result)
    if result and result[-1] not in ".!?…":
        result = result.rstrip(",;: ") + "..."
    return result
