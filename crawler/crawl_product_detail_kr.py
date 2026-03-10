import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

DETAIL_URL = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do"


def crawl():

    rows = supabase.table("product_ids_kr").select("goods_no").limit(500).execute()

    for r in rows.data:

        goods_no = r["goods_no"]

        params = {
            "goodsNo": goods_no
        }

        res = requests.get(DETAIL_URL, params=params)

        supabase.table("products_kr_raw").insert({
            "goods_no": goods_no,
            "raw_payload": res.text
        }).execute()

        print("CRAWLED:", goods_no)


if __name__ == "__main__":
    crawl()
