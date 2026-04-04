import numpy as np
import logging
from typing import Optional, List, Any
from config import Config

logger = logging.getLogger(__name__)

_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("SentenceTransformer modeli yukleniyor...")
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("Model yuklendi.")
    return _model


def cosine_similarity(a, b) -> float:
    a = np.array(a)
    b = np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class DuplicateDetector:
    """
    Embedding tabanli haber tekrar kontrolu.
    %90+ benzerlik -> ayni haber kabul edilir.
    """

    def get_embedding(self, text: str) -> list:
        model = get_model()
        emb = model.encode(text, normalize_embeddings=True)
        return emb.tolist()

    def find_duplicate(
        self,
        new_embedding: list,
        existing_docs: List[Any],
        *,
        category: Optional[str] = None,
    ) -> Optional[dict]:
        """
        En yuksek kosinus benzerligi; genel esik veya ayni kategoride biraz daha dusuk esik.
        """
        strict = float(Config.SIMILARITY_THRESHOLD)
        relaxed = float(
            getattr(Config, "SIMILARITY_THRESHOLD_SAME_CATEGORY", strict)
        )
        best_score = -1.0
        best_doc = None

        for doc in existing_docs:
            if "embedding" not in doc or not doc["embedding"]:
                continue
            score = cosine_similarity(new_embedding, doc["embedding"])
            if score > best_score:
                best_score = score
                best_doc = doc

        if best_doc is None:
            return None

        if best_score >= strict:
            logger.info("Duplicate bulundu: benzerlik=%.3f (genel esik)", best_score)
            return best_doc

        if (
            category
            and best_doc.get("category") == category
            and best_score >= relaxed
        ):
            logger.info(
                "Duplicate bulundu: benzerlik=%.3f (aynı kategori gevsek esik)",
                best_score,
            )
            return best_doc

        return None


detector = DuplicateDetector()
