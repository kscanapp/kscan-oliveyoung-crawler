import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"


def collect():

    page = 1

    while page < 200:

        params = {
            "pageIdx": page,
            "rowsPerPage": 50
        }

        r = requests.get(BASE, params=params)
        data = r.json()

        goods = data.get("goodsList", [])

        if not goods:
            break

        for g in goods:

            goods_no = g.get("goodsNo")

            if not goods_no:
                continue

            supabase.table("product_ids_kr").upsert(
                {"goods_no": goods_no},
                on_conflict="goods_no"
            ).execute()

            print("ID:", goods_no)

        page += 1


if __name__ == "__main__":
    collect()
