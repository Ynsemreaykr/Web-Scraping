"""
Scraper testi - URL listesi ve ilk haberi parse et
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from scraper.cagdas_scraper import CagdasScraper
from scraper.ozgur_scraper import OzgurScraper
from scraper.yeni_scraper import YeniScraper
from scraper.bizimyaka_scraper import BizimyakaScraper
from scraper.ses_scraper import SesScraper

scrapers = [CagdasScraper, OzgurScraper, YeniScraper, BizimyakaScraper, SesScraper]

for ScraperClass in scrapers:
    s = ScraperClass()
    print(f"\n{'='*55}")
    print(f"TEST: {s.source_name}")
    print('='*55)

    urls = s.get_news_urls()
    print(f"URL sayisi: {len(urls)}")

    if urls:
        print(f"Ornek URL: {list(urls)[0]}")
        art = None
        for u in list(urls)[:5]:          # ilk 5 URL dene
            art = s.parse_article(u)
            if art:
                break
        if art:
            print(f"Baslik   : {art['title'][:70]}")
            print(f"Tarih    : {art['published_at']}")
            print(f"Icerik   : {art['content'][:120]}...")
        else:
            print("Parse basarisiz (tum URL'ler denendi)")
    else:
        print("Hic URL bulunamadi.")
