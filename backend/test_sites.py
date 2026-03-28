import requests
import re
import sys

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'}
sites = [
    ('Cagdas', 'https://www.cagdaskocaeli.com.tr'),
    ('Ozgur', 'https://www.ozgurkocaeli.com.tr'),
    ('Ses', 'https://www.seskocaeli.com'),
    ('Yeni', 'https://www.yenikocaeli.com'),
    ('Biz', 'https://www.bizimyaka.com'),
]

for name, url in sites:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        hrefs = re.findall(r'href=["\']([^"\']*)["\']', r.text)
        # Haber URL'leri: 5+ segment
        news_links = [h for h in hrefs if h.startswith('http') and len(h.split('/')) >= 6]
        # Ya da kendi domain'inden olan 4+ segment
        domain = url.replace('https://www.', '').replace('http://www.', '')
        news_links2 = [h for h in hrefs if domain in h and len(h.split('/')) >= 6]
        all_news = list(set(news_links + news_links2))
        print(f"{name}: HTTP {r.status_code} | {len(r.text)} chr | potansiyel_haber_url: {len(all_news)}")
        if all_news:
            print(f"  Ornek: {all_news[0]}")
    except Exception as e:
        print(f"{name}: HATA -> {type(e).__name__}: {str(e)[:80]}")
