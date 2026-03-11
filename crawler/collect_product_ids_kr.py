import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryListAjax.do"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.oliveyoung.co.kr",
    "Referer": "https://www.oliveyoung.co.kr/store/main/main.do",
    "X-Requested-With": "XMLHttpRequest"
}

def collect():

    collected = set()

    for page in range(1, 100):

        payload = {
            "dispCatNo": "90000010001",
            "pageIdx": page,
            "rowsPerPage": "48",
            "prdSort": "01"
        }

        r = requests.post(URL, headers=headers, data=payload)

        print("PAGE:", page, "STATUS:", r.status_code)

        if r.status_code != 200:
            print("BLOCKED:", r.text[:200])
            break

        data = r.json()

        goods_list = data.get("data", {}).get("prdList", [])

        if not goods_list:
            print("NO MORE PRODUCTS")
            break

        print("FOUND:", len(goods_list))

        for g in goods_list:

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
