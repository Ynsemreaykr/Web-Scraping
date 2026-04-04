"""
Scrape sonrasi: ayni gun + ayni kategoride, embedding (ve gerekirse baslik) ile
benzer haberleri tek kayitta birlestirir; sources[] altinda tum site linkleri kalir.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from processing.duplicate_detector import cosine_similarity
from processing.text_utils import tr_lower
from services.db_service import db

logger = logging.getLogger(__name__)


def _day_key(doc: Dict[str, Any]) -> Optional[str]:
    dt = doc.get("published_at")
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None):
        dt = dt.replace(tzinfo=None)
    try:
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _title_tokens(title: str) -> set:
    t = tr_lower(re.sub(r"[^\w\s]", " ", title or ""))
    return {w for w in t.split() if len(w) > 2}


def _title_jaccard(t1: str, t2: str) -> float:
    a, b = _title_tokens(t1), _title_tokens(t2)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _should_merge_pair(
    di: Dict[str, Any],
    dj: Dict[str, Any],
    *,
    cos_threshold: float,
    cos_loose: float,
    jaccard_min: float,
) -> bool:
    if di.get("category") != dj.get("category"):
        return False
    dki, dkj = _day_key(di), _day_key(dj)
    if dki is None or dki != dkj:
        return False
    sim = cosine_similarity(di["embedding"], dj["embedding"])
    if sim >= cos_threshold:
        return True
    if sim >= cos_loose and _title_jaccard(di.get("title", ""), dj.get("title", "")) >= jaccard_min:
        return True
    return False


def _merge_sources_cluster(cluster: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for d in cluster:
        for s in d.get("sources") or []:
            if not isinstance(s, dict):
                continue
            u = (s.get("url") or "").strip()
            if not u or u in seen:
                continue
            seen.add(u)
            out.append(
                {
                    "source_key": s.get("source_key", ""),
                    "source_name": (s.get("source_name") or "").strip() or "Kaynak",
                    "url": u,
                }
            )
    for d in cluster:
        u = (d.get("url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        sk, sn = "", "Haber"
        ss = d.get("sources") or []
        if ss and isinstance(ss[0], dict):
            sk = ss[0].get("source_key") or sk
            sn = (ss[0].get("source_name") or "").strip() or sn
        out.append({"source_key": sk, "source_name": sn, "url": u})
    return out


def _pick_canonical(cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
    return max(
        cluster,
        key=lambda d: (
            len(d.get("sources") or []),
            len(d.get("content") or ""),
            str(d["_id"]),
        ),
    )


def merge_duplicate_news_in_db() -> int:
    """
    Veritabaninda benzer haberleri birlestir.
    Returns: silinen (birlesen) dokuman sayisi.
    """
    col = db.db["news"]
    cos_threshold = float(getattr(Config, "DEDUPE_MERGE_COSINE", 0.775))
    cos_loose = float(getattr(Config, "DEDUPE_MERGE_COSINE_LOOSE", 0.715))
    jaccard_min = float(getattr(Config, "DEDUPE_MERGE_TITLE_JACCARD", 0.42))

    docs = list(
        col.find(
            {},
            {
                "embedding": 1,
                "title": 1,
                "category": 1,
                "published_at": 1,
                "sources": 1,
                "url": 1,
                "content": 1,
                "category_display": 1,
                "location": 1,
            },
        )
    )
    with_emb = [d for d in docs if d.get("embedding")]
    buckets: Dict[Tuple[str, Any], List[Dict[str, Any]]] = defaultdict(list)
    for d in with_emb:
        dk = _day_key(d)
        if dk is None:
            continue
        buckets[(dk, d.get("category"))].append(d)

    deleted_total = 0

    for (_day, _cat), group in buckets.items():
        n = len(group)
        if n < 2:
            continue
        parent = list(range(n))

        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i in range(n):
            for j in range(i + 1, n):
                if _should_merge_pair(
                    group[i],
                    group[j],
                    cos_threshold=cos_threshold,
                    cos_loose=cos_loose,
                    jaccard_min=jaccard_min,
                ):
                    union(i, j)

        by_root: Dict[int, List[int]] = defaultdict(list)
        for i in range(n):
            by_root[find(i)].append(i)

        for _root, idxs in by_root.items():
            if len(idxs) < 2:
                continue
            cluster = [group[i] for i in idxs]
            canonical = _pick_canonical(cluster)
            merged_sources = _merge_sources_cluster(cluster)
            best_content = max((d.get("content") or "" for d in cluster), key=len)
            best_title = max((d.get("title") or "" for d in cluster), key=len)

            for d in cluster:
                if d["_id"] == canonical["_id"]:
                    continue
                col.delete_one({"_id": d["_id"]})
                deleted_total += 1

            col.update_one(
                {"_id": canonical["_id"]},
                {
                    "$set": {
                        "sources": merged_sources,
                        "content": best_content,
                        "title": best_title,
                    }
                },
            )
            logger.info(
                "DB birlestirme: %s kaynak, tutulan id=%s",
                len(merged_sources),
                canonical["_id"],
            )

    return deleted_total
