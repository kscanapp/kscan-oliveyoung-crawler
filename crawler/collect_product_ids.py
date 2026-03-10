import os
import re
import requests
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PRDT_PATTERN = re.compile(r'"prdtNo"\s*:\s*"([A-Z0-9]+)"')

CATEGORY_URLS = [
    "https://global.oliveyoung.com/display/page/best-seller",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000008",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000009",
]


def extract_prdt_ids(html):
    ids = set()
    matches = PRDT_PATTERN.findall(html)

    for m in matches:
        ids.add(m)

    return ids


def main():
    collected = set()

    for url in CATEGORY_URLS:
        print("Fetching:", url)

        r = requests.get(url, timeout=30)
        html = r.text

        ids = extract_prdt_ids(html)

        print("Found IDs:", len(ids))

        for pid in ids:
            try:
                supabase.table("product_ids").insert({
                    "prdt_no": pid
                }).execute()

                collected.add(pid)

            except Exception:
                pass

    print("TOTAL COLLECTED:", len(collected))


if __name__ == "__main__":
    main()
