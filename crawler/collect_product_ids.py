:::
import requests
import os
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

urls = [
"https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=1
",
"https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=2
",
"https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=3
",
"https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=4
",
"https://global.oliveyoung.com/display/getBestProductList?dispCatNo=90000010001&page=5
"
]

for url in urls:
 r = requests.get(url)
data = r.json()

for p in data["data"]["prodList"]:

    prdt_no = p["prdtNo"]

    supabase.table("product_ids").insert({
        "prdt_no": prdt_no,
        "collected_at": datetime.utcnow().isoformat()
    }).execute()

    print("Saved:", prdt_no)
  :::
