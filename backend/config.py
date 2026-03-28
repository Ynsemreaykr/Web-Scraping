import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "kocaeli_haberler")

    # Google API
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Scraping
    SCRAPE_DAYS = 3
    REQUEST_TIMEOUT = 15
    REQUEST_DELAY = 1.0

    # Benzerlik esigi
    SIMILARITY_THRESHOLD = 0.90

    # Kocaeli merkez koordinatlari
    KOCAELI_CENTER_LAT = 40.7654
    KOCAELI_CENTER_LNG = 29.9408

    # Haber turleri (oncelik sirasi)
    NEWS_CATEGORIES = [
        "Trafik Kazasi",
        "Yangin",
        "Elektrik Kesintisi",
        "Hirsizlik",
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
