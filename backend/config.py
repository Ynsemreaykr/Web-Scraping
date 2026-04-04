import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "kocaeli_haberler")

    # Google API
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Scraping (cok yuksek degerler = saatler suren tarama; UI takilir)
    SCRAPE_DAYS = 3
    REQUEST_TIMEOUT = 15
    REQUEST_DELAY = 0.35

    # Benzerlik esigi: cok yuksek = farkli sitelerdeki ayni haber birlesmez
    SIMILARITY_THRESHOLD = 0.88
    # Ayni kategoride biraz daha gevsek (baslik/metin farkli yazilmis ajans haberi)
    SIMILARITY_THRESHOLD_SAME_CATEGORY = 0.805

    # Scrape sonrasi DB birlestirme (aynı gün + kategori; coklu kaynak kartlari)
    DEDUPE_MERGE_COSINE = 0.775
    DEDUPE_MERGE_COSINE_LOOSE = 0.71
    DEDUPE_MERGE_TITLE_JACCARD = 0.4

    # Kaynak basina toplanacak benzersiz haber URL sayisi
    MAX_ARTICLE_URLS_PER_SOURCE = 120

    # Liste ek sayfa: 2 = sadece ?page=2 (1 = ek sayfa yok)
    LISTING_PAGINATION_MAX = 3

    # Bir kaynakta en fazla kac liste HTML'i indirilecek (sonsuz / tekrar sayfa onlemi)
    MAX_LISTING_PAGE_FETCHES = 48

    # Geocode zincirinde en fazla kac farkli adres dizesi (sonra pipeline merkez fallback)
    GEOCODE_MAX_QUERIES = 4

    # Kocaeli merkez koordinatlari
    KOCAELI_CENTER_LAT = 40.7654
    KOCAELI_CENTER_LNG = 29.9408

    # Geocoding tum adaylar basarisizsa merkeze dus (haritada pin garantisi)
    GEOCODE_CENTER_FALLBACK = True

    # Gömme çapa katkısı (0 = kapalı). Tüm kategorilere aynı anda puan eklediği için
    # yüksek değer: anahtar kelime 0 iken bile eşik altını aşıp her haberi içeri aldırır.
    SEMANTIC_CLASSIFIER_WEIGHT = 0

    # Zorunlu haber turleri (proje tanimi ile ayni)
    NEWS_CATEGORIES = [
        "Trafik Kazasi",
        "Yangin",
        "Elektrik Kesintisi",
        "Hirsizlik",
        "Suc ve Cinayet",
        "Kulturel Etkinlikler",
    ]

    # Kocaeli ilceleri
    KOCAELI_DISTRICTS = [
        "Izmit", "Gebze", "Darica", "Cayirova", "Dilovasi",
        "Golcuk", "Karamursel", "Kandira", "Kartepe", "Basiskele",
        "Derince", "Korfez"
    ]

    # Haber kaynagi adlari
    NEWS_SOURCES = {
        "cagdaskocaeli": "Çağdaş Kocaeli",
        "ozgurkocaeli": "Özgür Kocaeli",
        "seskocaeli": "Ses Kocaeli",
        "yenikocaeli": "Yeni Kocaeli",
        "bizimyaka": "Bizim Yaka",
    }
