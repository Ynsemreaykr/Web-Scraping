"""
Haber sitelerinin gercek HTML yapisini analiz et.
Her siteden haber URL pattern'lerini bul.
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
}

sites = [
    ('Cagdas', 'https://www.cagdaskocaeli.com.tr'),
    ('Ozgur', 'https://www.ozgurkocaeli.com.tr'),
    ('Ses', 'https://www.seskocaeli.com'),
    ('Yeni', 'https://www.yenikocaeli.com'),
    ('Biz', 'https://www.bizimyaka.com'),
]

for name, base_url in sites:
    print(f"\n{'='*60}")
    print(f"Site: {name} - {base_url}")
    print('='*60)
    try:
        r = requests.get(base_url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'lxml')

        # Tum a etiketleri
        all_hrefs = [a.get('href','') for a in soup.find_all('a', href=True)]

        # Sadece bu domain'e ait ve 4+ segment olanlar
        domain = base_url.replace('https://www.','').replace('http://www.','').rstrip('/')
        candidates = []
        for href in all_hrefs:
            if href.startswith('/'):
                href = base_url.rstrip('/') + href
            if domain in href:
                parts = href.rstrip('/').split('/')
                if len(parts) >= 5:  # https: '' '' domain segment1 segment2
                    candidates.append(href.rstrip('/'))

        candidates = list(set(candidates))
        print(f"Potansiyel haber URL: {len(candidates)}")
        for c in candidates[:8]:
            print(f"  {c}")

        # CSS class'lari - haber kutulari icin
        divs = soup.find_all(['div','article','li'], class_=True)
        classes = {}
        for d in divs:
            for cls in d.get('class', []):
                classes[cls] = classes.get(cls, 0) + 1
        top_classes = sorted(classes.items(), key=lambda x: -x[1])[:10]
        print(f"En cok kullanilan class'lar: {top_classes}")

    except Exception as e:
        print(f"HATA: {e}")
