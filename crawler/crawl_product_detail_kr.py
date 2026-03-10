import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.oliveyoung.co.kr/",
}

DETAIL_URL = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do"


def main():
    rows = supabase.table("product_ids_kr").select("goods_no, detail_url").limit(300).execute()

    if not rows.data:
        print("No product_ids_kr found.")
        return

    for row in rows.data:
        goods_no = row.get("goods_no")
        detail_url = row.get("detail_url")

        if not goods_no:
            continue

        try:
            params = {"goodsNo": goods_no}
            resp = requests.get(DETAIL_URL, params=params, headers=HEADERS, timeout=30)

            print("CRAWLED:", goods_no, "STATUS:", resp.status_code)

            if resp.status_code != 200 or not resp.text.strip():
                continue

            supabase.table("products_kr_raw").insert(
                {
                    "goods_no": goods_no,
                    "detail_url": detail_url or f"{DETAIL_URL}?goodsNo={goods_no}",
                    "raw_html": resp.text,
                }
            ).execute()

        except Exception as e:
            print("FAILED:", goods_no, e)


if __name__ == "__main__":
    main()
