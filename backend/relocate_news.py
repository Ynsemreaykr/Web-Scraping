"""Mevcut haberlerin lokasyonunu yeniden hesapla ve geocode et."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from pymongo import MongoClient
from processing.location_extractor import extractor
from services.geocoding import geocoder

client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=30000)
coll = client[Config.MONGODB_DB_NAME]["news"]

docs = list(coll.find({}))
print(f"Toplam {len(docs)} haber")

updated = 0
removed = 0
for doc in docs:
    title = doc.get("title", "")
    content = doc.get("content", "")
    url = doc.get("url", "")
    if not url and doc.get("sources"):
        url = doc["sources"][0].get("url", "")
    cat = doc.get("category", "")

    loc = extractor.extract(
        text=content, title=title,
        assume_local=True, category_hint=cat, url=url,
    )

    if not loc.get("geocode_query"):
        coll.delete_one({"_id": doc["_id"]})
        removed += 1
        continue

    old_district = (doc.get("location") or {}).get("district")
    new_district = loc.get("district")
    old_text = (doc.get("location") or {}).get("text")
    new_text = loc.get("location_text")

    if old_district != new_district or old_text != new_text:
        queries = []
        gq = loc.get("geocode_query")
        lt = loc.get("location_text")
        if gq:
            queries.append(gq)
        if lt and lt != gq:
            queries.append(f"{lt}, Türkiye")
            queries.append(lt)
        d = loc.get("district")
        if d:
            queries.append(f"{d}, Kocaeli, Türkiye")
        queries.append("Kocaeli, Türkiye")

        geo = geocoder.geocode_chain(queries)
        if geo:
            new_loc = {
                "text": new_text,
                "district": new_district,
                "lat": geo["lat"],
                "lng": geo["lng"],
                "geocode_fallback": loc.get("geocode_fallback", False),
            }
            coll.update_one({"_id": doc["_id"]}, {"$set": {"location": new_loc}})
            updated += 1
            print(f"  UPDATED: {title[:55]:55s} | {str(old_district):12s} -> {str(new_district):12s}")

print(f"\nSonuc: {updated} guncellendi, {removed} silindi")
client.close()
