"""
Geocoding API testi
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from services.geocoding import geocoder

test_addresses = [
    "Izmit, Kocaeli",
    "Gebze, Kocaeli",
    "Darıca, Kocaeli",
    "Ataturk Bulvari, Izmit, Kocaeli",
    "Yahya Kaptan Mahallesi, Izmit, Kocaeli",
]

print("=== GEOCODING TEST ===\n")
for addr in test_addresses:
    result = geocoder.geocode(addr)
    if result:
        print(f"OK: '{addr}'")
        print(f"    -> ({result['lat']:.5f}, {result['lng']:.5f})")
        print(f"    -> {result['formatted']}")
    else:
        print(f"FAIL: '{addr}'")
    print()
