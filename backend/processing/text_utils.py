"""Turkce metin normalizasyonu (siniflandirma ve konum icin ortak)."""


def tr_lower(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("I", "ı")
        .replace("İ", "i")
        .replace("Ğ", "ğ")
        .replace("Ü", "ü")
        .replace("Ş", "ş")
        .replace("Ö", "ö")
        .replace("Ç", "ç")
        .lower()
    )
