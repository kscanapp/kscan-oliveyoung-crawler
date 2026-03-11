import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryListAjax.do"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}


def collect():

    collected = set()

    for page in range(1, 100):

        data = {
            "dispCatNo": "90000010001",
            "pageIdx": str(page),
            "rowsPerPage": "48"
        }

        r = requests.post(URL, headers=headers, data=data)

        print("PAGE:", page, "STATUS:", r.status_code)

        data_json = r.json()

        goods = data_json.get("data", {}).get("prdList", [])

        if not goods:
            print("NO MORE PRODUCTS")
            break

        print("FOUND:", len(goods))

        for g in goods:
            goods_no = g.get("goodsNo")
            if goods_no:
                collected.add(goods_no)

    print("TOTAL:", len(collected))

    for goods_no in collected:

        supabase.table("product_ids_kr").upsert(
            {
                "goods_no": goods_no,
                "detail_url": f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"
            },
            on_conflict="goods_no"
        ).execute()

        print("SAVED:", goods_no)


if __name__ == "__main__":
    collect()
