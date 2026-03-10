import os
import re
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE = "https://www.oliveyoung.co.kr"

URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.oliveyoung.co.kr/"
}

goods_pattern = re.compile(r"goodsNo=([A-Z0-9]+)")


def collect():

    collected = set()

    for page in range(1, 50):

        params = {
            "dispCatNo": "90000010001",
            "pageIdx": page
        }

        r = requests.get(URL, params=params, headers=HEADERS)

        print("PAGE:", page, "STATUS:", r.status_code)

        html = r.text

        goods = goods_pattern.findall(html)

        print("FOUND:", len(goods))

        if not goods:
            break

        for g in goods:
            collected.add(g)

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
