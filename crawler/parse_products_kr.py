import os
import re
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def clean_text(text):
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def extract_by_selectors(soup, selectors):
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            value = clean_text(el.get_text(" ", strip=True))
            if value:
                return value
    return None


def extract_price(text):
    if not text:
        return None

    nums = re.findall(r"([0-9][0-9,]*)\s*원", text)
    if not nums:
        return None

    # 마지막 가격을 판매가로 우선 가정
    try:
        return int(nums[-1].replace(",", ""))
    except Exception:
        return None


def extract_labeled_block(full_text, labels):
    if not full_text:
        return None

    for label in labels:
        pattern = rf"{label}\s*[:：]?\s*(.*?)(?=(전성분|사용할 때의 주의사항|사용시의 주의사항|제조국|품질보증기준|소비자상담관련 전화번호|$))"
        match = re.search(pattern, full_text, flags=re.DOTALL)
        if match:
            value = clean_text(match.group(1))
            if value:
                return value

    return None


def extract_goods_info(soup, full_text):
    name = extract_by_selectors(
        soup,
        [
            "p.prd_name",
            ".prd_name",
            "h1.prd_name",
            "h2.prd_name",
            "h3.prd_name",
        ]
    )

    brand = extract_by_selectors(
        soup,
        [
            "p.prd_brand",
            ".prd_brand",
            "a.prd_brand",
        ]
    )

    price_text = extract_by_selectors(
        soup,
        [
            ".price_real",
            ".price-2 strong",
            ".price strong",
            ".prd_price .tx_num",
        ]
    )
    if not price_text:
        price_text = full_text

    price_krw = extract_price(price_text)

    image_url = None
    for selector in [".prd_img img", ".prd_thumb img", "img"]:
        img = soup.select_one(selector)
        if img and img.get("src"):
            image_url = img.get("src")
            break

    ingredients_ko = extract_labeled_block(
        full_text,
        ["전성분", "성분"]
    )

    cautions_ko = extract_labeled_block(
        full_text,
        ["사용시의 주의사항", "사용할 때의 주의사항", "주의사항"]
    )

    country_of_origin = extract_labeled_block(
        full_text,
        ["제조국", "원산지"]
    )

    return {
        "name_ko": name,
        "brand": brand,
        "price_krw": price_krw,
        "ingredients_ko": ingredients_ko,
        "cautions_ko": cautions_ko,
        "country_of_origin": country_of_origin,
        "image_url": image_url,
    }


def main():
    rows = supabase.table("products_kr_raw").select("*").limit(300).execute()

    if not rows.data:
        print("No products_kr_raw found.")
        return

    for row in rows.data:
        goods_no = row.get("goods_no")
        raw_html = row.get("raw_html")
        detail_url = row.get("detail_url")

        if not goods_no or not raw_html:
            continue

        soup = BeautifulSoup(raw_html, "html.parser")
        full_text = clean_text(soup.get_text(" ", strip=True))

        info = extract_goods_info(soup, full_text)

        payload = {
            "product_id": goods_no,
            "name_ko": info["name_ko"],
            "brand": info["brand"],
            "price_krw": info["price_krw"],
            "ingredients_ko": info["ingredients_ko"],
            "cautions_ko": info["cautions_ko"],
            "country_of_origin": info["country_of_origin"],
            "image_url": info["image_url"],
            "oliveyoung_url": detail_url,
        }

        if not payload["name_ko"] or not payload["brand"]:
            print("SKIP EMPTY CORE FIELDS:", goods_no)
            continue

        try:
            supabase.table("products").upsert(
                payload,
                on_conflict="product_id"
            ).execute()
            print("PARSED:", goods_no, payload["name_ko"])
        except Exception as e:
            print("UPSERT FAILED:", goods_no, e)


if __name__ == "__main__":
    main()
