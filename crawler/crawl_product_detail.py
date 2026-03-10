import os
import json
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://global.oliveyoung.com/product/detail?prdtNo="


def save_raw_product(source_url: str, payload):
    try:
        payload_str = json.dumps(payload, ensure_ascii=False)[:50000]

        supabase.table("raw_products").insert({
            "source_url": source_url,
            "raw_payload": payload_str
        }).execute()

        print(f"Saved raw payload for: {source_url}")

    except Exception as e:
        print(f"Failed to save raw payload for {source_url}: {e}")


def crawl_one_product(prdt_no: str):
    url = f"{BASE_URL}{prdt_no}"
    found_json = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            try:
                response_url = response.url.lower()
                content_type = response.headers.get("content-type", "").lower()

                if "application/json" not in content_type:
                    return

                if prdt_no.lower() not in response_url and "product" not in response_url and "review" not in response_url:
                    return

                data = response.json()
                found_json.append((response.url, data))

            except Exception:
                pass

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            print(f"Timed out loading {url}, continuing...")

        page.wait_for_timeout(5000)
        browser.close()

    for response_url, data in found_json:
        save_raw_product(response_url, data)

    print(f"{prdt_no}: captured {len(found_json)} JSON responses")


def main():
    rows = supabase.table("product_ids").select("prdt_no").limit(50).execute()

    if not rows.data:
        print("No product_ids found.")
        return

    for row in rows.data:
        prdt_no = row.get("prdt_no")
        if not prdt_no:
            continue

        crawl_one_product(prdt_no)


if __name__ == "__main__":
    main()
