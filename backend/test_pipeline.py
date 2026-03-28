"""
Tam pipeline mini testi:
1. Cagdas'tan 3 haber cek
2. Temizle
3. Siniflandir
4. Konum cikar
5. Sonuclari yazdir
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from scraper.cagdas_scraper import CagdasScraper
from scraper.ozgur_scraper import OzgurScraper
from processing.cleaner import cleaner
from processing.classifier import classifier, CATEGORY_DISPLAY
from processing.location_extractor import extractor

print("=== MINI PIPELINE TEST ===\n")

results = []
for ScraperClass in [CagdasScraper, OzgurScraper]:
    s = ScraperClass()
    urls = s.get_news_urls()
    for url in list(urls)[:15]:
        art = s.parse_article(url)
        if not art:
            continue
        title_c = cleaner.clean(art['title'])
        content_c = cleaner.clean(art['content'])
        cat = classifier.classify(title_c, content_c)
        if not cat:
            continue
        loc = extractor.extract(content_c + ' ' + title_c)
        results.append({
            'source': art['source_name'],
            'title': title_c[:65],
            'category': CATEGORY_DISPLAY.get(cat, cat),
            'district': loc.get('district') or '-',
            'location': loc.get('location_text') or '-',
        })
        if len(results) >= 10:
            break
    if len(results) >= 10:
        break

print(f"Kategori eslesen haber sayisi: {len(results)}\n")
for i, r in enumerate(results, 1):
    print(f"{i}. [{r['category']}] {r['title']}")
    print(f"   Kaynak: {r['source']} | Ilce: {r['district']} | Konum: {r['location']}")
    print()
