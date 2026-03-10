import os
import json
import re
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE_URL = "https://global.oliveyoung.com/product/detail?prdtNo="


def normalize_text(text: str):
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def extract_ingredients_from_payload(payload):
    """
    Olive Young payload 구조가 일정하지 않을 수 있으므로
    가능한 후보 키를 넓게 본다.
    """
    if not isinstance(payload, dict):
        return None

    # details 블록 안
    details = payload.get("details")
    if isinstance(details, dict):
        candidates = [
            "ingredients",
            "ingredient",
            "ingr",
            "fullIngredients",
            "ingredientsText",
            "allIngredients",
        ]
        for key in candidates:
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return normalize_text(value)

    # 최상위 블록 안
    candidates = [
        "ingredients",
        "ingredient",
        "ingr",
        "fullIngredients",
        "ingredientsText",
        "allIngredients",
    ]
    for key in candidates:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_text(value)

    return None


def extract_prdt_no(payload):
    if not isinstance(payload, dict):
        return None

    product = payload.get("product")
    if isinstance(product, dict) and product.get("prdtNo"):
        return product.get("prdtNo")

    details = payload.get("details")
    if isinstance(details, dict) and details.get("prdtNo"):
        return details.get("prdtNo")

    return None


def extract_ingredients_from_html(html: str):
    """
    JSON에서 못 찾을 경우를 대비한 HTML fallback.
    너무 공격적으로 추출하지 말고, ingredients 섹션 후보만 본다.
    """
    if not html:
        return None

    patterns = [
        r"INGREDIENTS[:\s]*([^<]{20,2000})",
        r"Ingredients[:\s]*([^<]{20,2000})",
        r"전성분[:\s]*([^<]{20,2000})",
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            value = normalize_text(match.group(1))
            if value:
                return value

    return None


def update_product_ingredients(product_id: str, ingredients_raw: str):
    if not product_id or not ingredients_raw:
        return

    supabase.table("products").upsert(
        {
            "product_id": product_id,
            "ingredients_raw": ingredients_raw,
        },
        on_conflict="product_id"
    ).execute()

    print(f"Updated ingredients: {product_id}")


def crawl_one_product(product_id: str):
    url = f"{BASE_URL}{product_id}"
    found_ingredients = None
    final_html = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            nonlocal found_ingredients

            if found_ingredients:
                return

            try:
                content_type = response.headers.get("content-type", "").lower()
                if "application/json" not in content_type:
                    return

                data = response.json()
                prdt_no = extract_prdt_no(data)

                # 해당 상품 응답만 본다
                if prdt_no and prdt_no != product_id:
                    return

                ingredients = extract_ingredients_from_payload(data)
                if ingredients:
                    found_ingredients = ingredients

            except Exception:
                pass

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            print(f"Timed out loading {url}, continuing...")

        page.wait_for_timeout(5000)

        try:
            final_html = page.content()
        except Exception:
            final_html = None

        browser.close()

    if not found_ingredients:
        found_ingredients = extract_ingredients_from_html(final_html)

    if found_ingredients:
        update_product_ingredients(product_id, found_ingredients)
    else:
        print(f"No ingredients found: {product_id}")


def main():
    rows = supabase.table("products").select("product_id, ingredients_raw").limit(200).execute()

    if not rows.data:
        print("No products found.")
        return

    target_ids = []
    for row in rows.data:
        product_id = row.get("product_id")
        ingredients_raw = row.get("ingredients_raw")

        # 아직 성분 없는 상품만 대상
        if product_id and not ingredients_raw:
            target_ids.append(product_id)

    print(f"Target products for ingredient crawl: {len(target_ids)}")

    for product_id in target_ids:
        crawl_one_product(product_id)


if __name__ == "__main__":
    main()
