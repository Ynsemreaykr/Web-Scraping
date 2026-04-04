"""Mevcut haberlerin ozetlerini yeniden olustur."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from pymongo import MongoClient
from pipeline import _make_summary

client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=30000)
coll = client[Config.MONGODB_DB_NAME]["news"]

docs = list(coll.find({}, {"title": 1, "content": 1, "summary": 1}))
print(f"Toplam {len(docs)} haber")

updated = 0
empty = 0
for doc in docs:
    title = doc.get("title", "")
    content = doc.get("content", "")

    new_summary = _make_summary(title, content)
    coll.update_one({"_id": doc["_id"]}, {"$set": {"summary": new_summary}})

    if new_summary:
        updated += 1
    else:
        empty += 1

print(f"Sonuc: {updated} ozetli, {empty} ozetsiz (icerik yok)")

# Ornekler
print("\n--- ORNEK OZETLER ---")
i = 0
for doc in coll.find({}, {"title": 1, "summary": 1}):
    s = doc.get("summary", "")
    if not s:
        continue
    if i >= 5:
        break
    i += 1
    print(f"\nTITLE: {doc['title'][:60]}")
    print(f"OZET:  {s}")

client.close()
