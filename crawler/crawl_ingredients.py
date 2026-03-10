import os
import re
import json
from supabase import create_client
from playwright.sync_api import sync_playwright

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE_URL = "https://global.oliveyoung.com/product/detail?prdtNo="


def normalize_text(text):
    if not text:
        return None

    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    if len(text) < 10:
        return None

    return text


def extract_ingredients(payload):

    if not isinstance(payload, dict):
        return None

    details = payload.get("details")

    if not isinstance(details, dict):
        return None

    # ⭐ 올리브영 실제 성분 필드
    ingredients = details.get("ftrdIngrdText")

    if ingredients:
        return normalize_text(ingredients)

    return None


def update_ingredients(product_id, ingredients):

    supabase.table("products").upsert(
        {
            "product_id": product_id,
            "ingredients_raw": ingredients
        },
        on_conflict="product_id"
    ).execute()

    print("UPDATED:", product_id)


def crawl_one(product_id):

    url = BASE_URL + product_id

    print("CRAWLING:", product_id)

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        ingredients_found = None

        def handle_response(response):

            nonlocal ingredients_found

            try:

                content_type = response.headers.get("content-type", "")

                if "application/json" not in content_type:
                    return

                data = response.json()

                if not isinstance(data, dict):
                    return

                if "details" not in data:
                    return

                ingredients = extract_ingredients(data)

                if ingredients:
                    ingredients_found = ingredients

            except:
                pass

        page.on("response", handle_response)

        page.goto(url)

        page.wait_for_timeout(5000)

        browser.close()

        if ingredients_found:
            update_ingredients(product_id, ingredients_found)
        else:
            print("NO INGREDIENTS:", product_id)


def main():

    rows = supabase.table("products").select(
        "product_id, ingredients_raw"
    ).limit(200).execute()

    targets = []

    for r in rows.data:

        if not r["ingredients_raw"]:
            targets.append(r["product_id"])

    print("TARGET COUNT:", len(targets))

    for pid in targets:
        crawl_one(pid)


if __name__ == "__main__":
    main()
