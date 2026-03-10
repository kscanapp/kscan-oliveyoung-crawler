import os
import json
from supabase import create_client, Client
from playwright.sync_api import sync_playwright

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TARGET_URL = "https://global.oliveyoung.com/product/detail?prdtNo=GA230217683"


def save_debug_response(url: str, data):
    try:
        supabase.table("raw_products").insert({
            "source_url": url,
            "raw_payload": json.dumps(data, ensure_ascii=False)[:50000]
        }).execute()
        print(f"Saved raw response from: {url}")
    except Exception as e:
        print(f"Failed to save raw response: {e}")


def crawl_network_data():
    found_json = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            url = response.url.lower()

            interesting_keywords = [
                "product",
                "detail",
                "goods",
                "api",
                "item",
                "prdt",
            ]

            if not any(keyword in url for keyword in interesting_keywords):
                return

            content_type = response.headers.get("content-type", "").lower()

            if "application/json" not in content_type:
                return

            try:
                data = response.json()
                print(f"\n=== JSON RESPONSE FOUND ===")
                print(f"URL: {response.url}")
                print(f"Top-level type: {type(data).__name__}")

                if isinstance(data, dict):
                    print(f"Top-level keys: {list(data.keys())[:20]}")
                elif isinstance(data, list):
                    print(f"List length: {len(data)}")

                found_json.append((response.url, data))
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"Opening page: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

        print("Page title:", page.title())
        print("Final URL:", page.url)

        browser.close()

    print(f"\nTotal JSON responses found: {len(found_json)}")

    for url, data in found_json[:10]:
        save_debug_response(url, data)

    return found_json


if __name__ == "__main__":
    results = crawl_network_data()
    print(f"Captured {len(results)} candidate JSON responses")
