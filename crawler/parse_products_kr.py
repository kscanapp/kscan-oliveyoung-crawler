import os
import re
from supabase import create_client
from bs4 import BeautifulSoup

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def extract_text(soup, selector):

    el = soup.select_one(selector)

    if not el:
        return None

    return el.text.strip()


def parse():

    rows = supabase.table("products_kr_raw").select("*").limit(500).execute()

    for r in rows.data:

        goods_no = r["goods_no"]
        html = r["raw_payload"]

        soup = BeautifulSoup(html, "html.parser")

        name = extract_text(soup, ".prd_name")
        brand = extract_text(soup, ".prd_brand")
        price = extract_text(soup, ".price_real")
        ingredients = extract_text(soup, "#artcInfo .detail_cont")

        img = soup.select_one(".prd_img img")
        img_url = img["src"] if img else None

        olive_url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"

        supabase.table("products").upsert(
            {
                "product_id": goods_no,
                "name_ko": name,
                "brand": brand,
                "price_krw": int(re.sub("[^0-9]", "", price)) if price else None,
                "ingredients_ko": ingredients,
                "image_url": img_url,
                "oliveyoung_url": olive_url
            },
            on_conflict="product_id"
        ).execute()

        print("PARSED:", goods_no)


if __name__ == "__main__":
    parse()
