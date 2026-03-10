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
    if not isinstance(payload, dict):
        return None

    product = payload.get("product")
    if isinstance(product, dict):
        return product.get("prdtNo")

    details = payload.get("details")
    if isinstance(details, dict):
        return details.get("prdtNo")

    return None


def extract_image(product):
    # 1순위: imagePath
    image_path = product.get("imagePath")
    if image_path:
        if image_path.startswith("http"):
            return image_path
        return f"https://static.global.oliveyoung.com/{image_path}"

    # 2순위: thumbnailList
    thumb_list = product.get("thumbnailList")
    if isinstance(thumb_list, list) and len(thumb_list) > 0:
        first = thumb_list[0]
        if isinstance(first, dict):
            thumb_path = first.get("imagePath")
            if thumb_path:
                if thumb_path.startswith("http"):
                    return thumb_path
                return f"https://static.global.oliveyoung.com/{thumb_path}"

    return None


def extract_ingredients(details):
    if not isinstance(details, dict):
        return None

    # Olive Young details payload 구조가 다를 수 있어서 유연하게 처리
    return (
        details.get("ingredients")
        or details.get("ingr")
        or details.get("ingredient")
        or details.get("fullIngredients")
    )


def main():
    print("Loading raw_products...")
    raw_rows = supabase.table("raw_products").select("*").execute()

    grouped = defaultdict(dict)
    skipped_json = 0

    for row in raw_rows.data:
        raw_payload = row.get("raw_payload")
        if not raw_payload:
            continue

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

        if "details" in payload:
            entry["details"] = payload["details"]

    print("Grouped products:", len(grouped))
    print("Skipped broken JSON:", skipped_json)

    upserted = 0

    for prdt_no, data in grouped.items():
        product = data.get("product", {})
        details = data.get("details", {})

        if not isinstance(product, dict):
            continue

        # 실제 Olive Young Global payload 기준
        name = (
            product.get("prdtName")
            or product.get("prdtNameEn")
            or product.get("korPrdtName")
        )

        brand = (
            product.get("brandName")
            or product.get("brandNameEn")
            or product.get("korBrandName")
        )

        price = product.get("saleAmt") or product.get("nrmlAmt")

        image = extract_image(product)
        ingredients = extract_ingredients(details)

        payload = {
            "product_id": prdt_no,
            "name": name,
            "brand": brand,
            "price": price,
            "image": image,
            "ingredients": ingredients,
        }

        try:
            supabase.table("products").upsert(
                payload,
                on_conflict="product_id"
            ).execute()

            upserted += 1
            print(f"Upserted: {prdt_no} / {name}")

        except Exception as e:
            print(f"Insert failed: {prdt_no} / {e}")

    print("\n====================")
    print(f"Products upserted: {upserted}")
    print(f"Total raw rows: {len(raw_rows.data)}")
    print("====================")


if __name__ == "__main__":
    main()
