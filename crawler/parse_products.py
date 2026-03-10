import os
import json
from collections import defaultdict
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def extract_prdt_no(payload):
    # 1) product block
    if isinstance(payload, dict) and "product" in payload and isinstance(payload["product"], dict):
        return payload["product"].get("prdtNo")

    # 2) images/details/reviews 안쪽에 prdtNo가 있을 수도 있음
    if isinstance(payload, dict):
        for key in ["details", "reviewList", "reviewMediaList", "images"]:
            value = payload.get(key)

            if isinstance(value, dict):
                if "prdtNo" in value:
                    return value.get("prdtNo")

            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                if "prdtNo" in value[0]:
                    return value[0].get("prdtNo")

    return None


def main():
    raw_rows = supabase.table("raw_products").select("*").execute()

    grouped = defaultdict(dict)

    for row in raw_rows.data:
        raw_payload = row.get("raw_payload")
        if not raw_payload:
            continue

        try:
            payload = json.loads(raw_payload)
        except Exception:
            continue

        prdt_no = extract_prdt_no(payload)
        if not prdt_no:
            continue

        entry = grouped[prdt_no]

        if isinstance(payload, dict):
            if "product" in payload:
                entry["product"] = payload["product"]
            if "images" in payload:
                entry["images"] = payload["images"]
            if "details" in payload:
                entry["details"] = payload["details"]
            if "reviewList" in payload:
                entry["reviewList"] = payload["reviewList"]
            if "reviewMediaList" in payload:
                entry["reviewMediaList"] = payload["reviewMediaList"]

    upserted = 0

    for prdt_no, data in grouped.items():
        product = data.get("product", {})
        images = data.get("images", [])
        details = data.get("details", {})
        review_list = data.get("reviewList", [])

        name = product.get("prdtNm") or product.get("prdtName")
        brand = product.get("brandNm") or product.get("brandName")
        price = product.get("salePrc") or product.get("price")

        image = None
        if isinstance(images, list) and len(images) > 0:
            first = images[0]
            if isinstance(first, dict):
                image = first.get("imgUrl") or first.get("imageUrl")

        ingredients = None
        if isinstance(details, dict):
            ingredients = details.get("ingredients") or details.get("ingr")

        rating = None
        review_count = None

        if isinstance(product, dict):
            rating = product.get("avgScore") or product.get("rating")
            review_count = product.get("reviewCnt") or product.get("reviewCount")

        if review_count is None and isinstance(review_list, list):
            review_count = len(review_list)

        payload = {
            "product_id": prdt_no,
            "name": name,
            "brand": brand,
            "price": price,
            "image": image,
            "ingredients": ingredients,
            "rating": rating,
            "review_count": review_count,
        }

        supabase.table("products").upsert(
            payload,
            on_conflict="product_id"
        ).execute()

        upserted += 1
        print(f"Upserted: {prdt_no} / {name}")

    print(f"Finished. Upserted {upserted} products.")


if __name__ == "__main__":
    main()
