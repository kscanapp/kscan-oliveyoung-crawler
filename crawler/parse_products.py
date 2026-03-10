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
        prdt_no = product.get("prdtNo")
        if prdt_no:
            return prdt_no

    details = payload.get("details")
    if isinstance(details, dict):
        prdt_no = details.get("prdtNo")
        if prdt_no:
            return prdt_no

    images = payload.get("images")
    if isinstance(images, list) and len(images) > 0:
        first = images[0]
        if isinstance(first, dict):
            prdt_no = first.get("prdtNo")
            if prdt_no:
                return prdt_no

    return None


def extract_name(product):
    if not isinstance(product, dict):
        return None

    return (
        product.get("prdtName")
        or product.get("prdtNameEn")
        or product.get("korPrdtName")
    )


def extract_brand(product):
    if not isinstance(product, dict):
        return None

    return (
        product.get("brandName")
        or product.get("brandNameEn")
        or product.get("korBrandName")
    )


def extract_price(product):
    if not isinstance(product, dict):
        return None

    return product.get("saleAmt") or product.get("nrmlAmt")


def extract_image(product):
    if not isinstance(product, dict):
        return None

    image_path = product.get("imagePath")
    if image_path:
        if image_path.startswith("http"):
            return image_path
        return f"https://static.global.oliveyoung.com/{image_path}"

    thumbnail_list = product.get("thumbnailList")
    if isinstance(thumbnail_list, list) and len(thumbnail_list) > 0:
        first = thumbnail_list[0]
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
    skipped_missing_prdt = 0

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
            skipped_missing_prdt += 1
            continue

        entry = grouped[prdt_no]

        if "product" in payload:
            entry["product"] = payload["product"]

        if "details" in payload:
            entry["details"] = payload["details"]

        if "images" in payload:
            entry["images"] = payload["images"]

    print(f"Grouped products: {len(grouped)}")
    print(f"Skipped broken JSON: {skipped_json}")
    print(f"Skipped missing prdtNo: {skipped_missing_prdt}")

    upserted = 0
    skipped_empty_name = 0
    skipped_empty_brand = 0

    for prdt_no, data in grouped.items():
        product = data.get("product", {})
        details = data.get("details", {})

        name = extract_name(product)
        brand = extract_brand(product)
        price = extract_price(product)
        image = extract_image(product)
        ingredients = extract_ingredients(details)

        # 품질 안정화: 이름 없는 상품은 저장하지 않음
        if not name:
            skipped_empty_name += 1
            print(f"Skipping product with empty name: {prdt_no}")
            continue

        # 브랜드 없는 상품도 저장하지 않음
        if not brand:
            skipped_empty_brand += 1
            print(f"Skipping product with empty brand: {prdt_no}")
            continue

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
    print(f"Skipped empty name: {skipped_empty_name}")
    print(f"Skipped empty brand: {skipped_empty_brand}")
    print(f"Total raw rows: {len(raw_rows.data)}")
    print("====================")


if __name__ == "__main__":
    main()
