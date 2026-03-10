import os
import re
import json
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE_URL = "https://global.oliveyoung.com/product/detail?prdtNo="


def normalize_text(text):
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def update_product_ingredients(product_id, ingredients_raw):
    supabase.table("products").upsert(
        {
            "product_id": product_id,
            "ingredients_raw": ingredients_raw,
        },
        on_conflict="product_id"
    ).execute()
    print(f"UPDATED ingredients_raw: {product_id}")


def extract_ingredients_from_payload(payload):
    if not isinstance(payload, dict):
        return None

    # details 안쪽
    details = payload.get("details")
    if isinstance(details, dict):
        print("DETAILS KEYS:", list(details.keys())[:50])
        for key in [
            "ingredients",
            "ingredient",
            "ingr",
            "fullIngredients",
            "ingredientsText",
            "allIngredients",
            "comp",
            "component",
        ]:
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return normalize_text(value)

    # 최상위
    print("TOP KEYS:", list(payload.keys())[:50])
    for key in [
        "ingredients",
        "ingredient",
        "ingr",
        "fullIngredients",
        "ingredientsText",
        "allIngredients",
        "comp",
        "component",
    ]:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_text(value)

    return None


def extract_ingredients_from_html(html):
    if not html:
        return None

    # 너무 공격적으로 안 하고, label 근처만 시도
    patterns = [
        r"INGREDIENTS[:\s]*([^<]{20,3000})",
        r"Ingredients[:\s]*([^<]{20,3000})",
        r"전성분[:\s]*([^<]{20,3000})",
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            value = normalize_text(match.group(1))
            if value:
                return value

    return None


def crawl_one_product(product_id):
    url = f"{BASE_URL}{product_id}"
    found_ingredients = None
    final_html = None

    print(f"\n==============================")
    print(f"TEST PRODUCT: {product_id}")
    print(f"URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            nonlocal found_ingredients

            if found_ingredients:
                return

            try:
                response_url = response.url
                content_type = response.headers.get("content-type", "").lower()

                if "application/json" not in content_type:
                    return

                lower_url = response_url.lower()
                if (
                    "product" not in lower_url
                    and "detail" not in lower_url
                    and "goods" not in lower_url
                ):
                    return

                data = response.json()

                print("\nJSON RESPONSE URL:", response_url)
                if isinstance(data, dict):
                    print("JSON TOP KEYS:", list(data.keys())[:30])

                ingredients = extract_ingredients_from_payload(data)
                if ingredients:
                    found_ingredients = ingredients
                    print("FOUND INGREDIENTS IN JSON")

            except Exception as e:
                print("JSON parse skipped:", e)

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            print("Timed out on page load, continuing...")

        page.wait_for_timeout(5000)

        try:
            final_html = page.content()
            print("HTML length:", len(final_html))
        except Exception:
            final_html = None

        browser.close()

    if not found_ingredients:
        html_ingredients = extract_ingredients_from_html(final_html)
        if html_ingredients:
            found_ingredients = html_ingredients
            print("FOUND INGREDIENTS IN HTML")

    if found_ingredients:
        update_product_ingredients(product_id, found_ingredients)
    else:
        print("NO INGREDIENTS FOUND:", product_id)


def main():
    # 먼저 5개만 테스트
    rows = supabase.table("products").select("product_id, ingredients_raw").limit(5).execute()

    if not rows.data:
        print("No products found.")
        return

    target_ids = []
    for row in rows.data:
        product_id = row.get("product_id")
        if product_id:
            target_ids.append(product_id)

    print("TARGET IDS:", target_ids)

    for product_id in target_ids:
        crawl_one_product(product_id)


if __name__ == "__main__":
    main()
