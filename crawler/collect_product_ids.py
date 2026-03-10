import os
import requests
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

urls = [
    "https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=1",
    "https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=2",
    "https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=3",
    "https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=4",
    "https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=5",
]

for url in urls:
    print(f"Fetching: {url}")

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    response.raise_for_status()

    data = response.json()

    prod_list = (
        data.get("data", {}).get("prodList", [])
        if isinstance(data, dict)
        else []
    )

    print(f"Found {len(prod_list)} products")

    for p in prod_list:
        prdt_no = p.get("prdtNo")
        if not prdt_no:
            continue

        supabase.table("product_ids").upsert(
            {
                "prdt_no": prdt_no,
                "collected_at": datetime.utcnow().isoformat()
            },
            on_conflict="prdt_no"
        ).execute()

        print("Saved:", prdt_no)
