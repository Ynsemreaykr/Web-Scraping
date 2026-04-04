"""
MongoDB: news + geocoding_cache koleksiyonlarini bosaltir.

Kullanim (backend klasorunden):
  python clear_database.py --yes
"""
import os
import sys

if "--yes" not in sys.argv:
    print("Tum haberler ve geocoding onbellegi silinir.")
    print("Onaylamak icin: python clear_database.py --yes")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from services.db_service import db

r = db.clear_news_and_cache()
print("Tamam:", r)
