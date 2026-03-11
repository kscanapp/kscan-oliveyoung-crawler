import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}

def collect():

    collected = set()

    for page in range(1, 50):

        data = {
            "dispCatNo": "90000010001",
            "fltDispCatNo": "",
            "prdSort": "01",
            "pageIdx": str(page),
            "rowsPerPage": "48"
        }

        r = requests.post(URL, headers=headers, data=data)

        print("PAGE:", page, "STATUS:", r.status_code)

        html = r.text

        if "goodsNo" not in html:
            print("NO GOODS FOUND")
            break

        parts = html.split("goodsNo=")

        ids = []

        for p in parts[1:]:
            goods = p[:13]
            if goods.startswith("A"):
                ids.append(goods)

        print("FOUND:", len(ids))

        for i in ids:
            collected.add(i)

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
