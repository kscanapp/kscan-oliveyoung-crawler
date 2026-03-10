:::
import requests
import os
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

rows = supabase.table("product_ids").select("*").execute()

for r in rows.data:
  prdt = r["prdt_no"]

url = f"https://global.oliveyoung.com/product/detail?prdtNo={prdt}"

res = requests.get(url)

supabase.table("raw_products").insert({
    "source_url": url,
    "raw_payload": res.text,
    "created_at": datetime.utcnow().isoformat()
}).execute()

print("Saved detail:", prdt)
:::
