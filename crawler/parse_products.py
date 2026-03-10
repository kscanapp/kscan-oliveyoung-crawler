import os
import json
from collections import defaultdict
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def extract_prdt_no(payload):
    """
    raw_payload 안에서 prdtNo를 찾아낸다.
    payload 구조가 여러 가지라서 유연하게 찾는다.
    """

    if not isinstance(payload, dict):
        return None

    # product block
    product = payload.get("product")
    if isinstance(product, dict):
        if product.get("prdtNo"):
            return product.get("prdtNo")

    # details
    details = payload.get("details")
    if isinstance(details, dict):
        if details.get("prdtNo"):
            return details.get("prdtNo")

    # images
    images = payload.get("images")
    if isinstance(images, list) and len(images) > 0:
        if isinstance(images[0], dict):
            if images[0].get("prdtNo"):
                return images[0].get("prdtNo")

    # reviews
    reviews = payload.get("reviewList")
    if isinstance(reviews, list) and len(reviews) > 0:
        if isinstance(reviews[0], dict):
            if reviews[0].get("prdtNo"):
                return reviews[0].get("prdtNo")

    return None


def main():

    print("Loading raw_products...")

    raw_rows = supabase.table("raw_products").select("*").execute()

    grouped = defaultdict(dict)

    skipped_json = 0

    for row in raw_rows.data:

        raw_payload = row.get("raw_payload")

        if not raw_payload:
            continue

        # JSON decode
        try:
            payload = json.loads(raw_payload)
        except Exception:
            skipped_json += 1
            continue

        prdt_no = extract_prdt_no(payload)

        if not prdt_no:
            continue

        entry = grouped[prdt_no]

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

    print("Grouped products:", len(grouped))
    print("Skipped broken JSON:", skipped_json)

    inserted = 0

    for prdt_no, data in grouped.items():

        product = data.get("product", {})
        images = data.get("images", [])
        details = data.get("details", {})
        reviews = data.get("reviewList", [])

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

        rating = product.get("avgScore") or product.get("rating")

        review_count = product.get("reviewCnt") or product.get("reviewCount")

        if review_count is None and isinstance(reviews, list):
            review_count = len(reviews)

        payload = {
            "product_id": prdt_no,
            "name": name,
            "brand": brand,
            "price": price,
            "image": image,
            "ingredients": ingredients,
            "rating": rating,
            "review_count": review_count,
            "updated_at": datetime.utcnow().isoformat()
        }

        try:

            supabase.table("products").upsert(
                payload,
                on_conflict="product_id"
            ).execute()

            inserted += 1

            print("Inserted:", prdt_no, name)

        except Exception as e:

            print("Insert failed:", prdt_no, e)

    print("\n====================")
    print("Products inserted:", inserted)
    print("Total raw rows:", len(raw_rows.data))
    print("====================")


if __name__ == "__main__":
    main()
