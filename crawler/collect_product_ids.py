import os
import re
from datetime import datetime
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TARGET_URLS = [
    "https://global.oliveyoung.com",
    "https://global.oliveyoung.com/display/page/best-seller",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000008",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000009",
]

# prdtNo=GA230217683 형태
PRDT_QUERY_REGEX = re.compile(r"prdtNo=([A-Z0-9]+)", re.IGNORECASE)

# "prdtNo":"GA230217683" 형태
PRDT_JSON_REGEX = re.compile(r'"prdtNo"\s*:\s*"([A-Z0-9]+)"', re.IGNORECASE)


def extract_ids_from_text(text: str):
    ids = set()

    for match in PRDT_QUERY_REGEX.findall(text or ""):
        ids.add(match)

    for match in PRDT_JSON_REGEX.findall(text or ""):
        ids.add(match)

    return ids


def save_product_id(prdt_no: str):
    result = supabase.table("product_ids").upsert(
        {
            "prdt_no": prdt_no,
            "collected_at": datetime.utcnow().isoformat()
        },
        on_conflict="prdt_no"
    ).execute()

    return result


def collect_from_pages():
    collected_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for url in TARGET_URLS:
            page = browser.new_page()

            print(f"\nOpening: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                print(f"Timed out on {url}, continuing...")

            page.wait_for_timeout(5000)

            # 1) HTML 전체에서 추출
            try:
                html = page.content()
                html_ids = extract_ids_from_text(html)
                print(f"IDs found in HTML: {len(html_ids)}")
                collected_ids.update(html_ids)
            except Exception as e:
                print(f"HTML parse error: {e}")

            # 2) href에서 추출
            try:
                anchors = page.locator("a").evaluate_all(
                    "(elements) => elements.map(e => e.href || '')"
                )

                print(f"Anchor count: {len(anchors)}")

                href_ids = set()
                for href in anchors:
                    href_ids.update(extract_ids_from_text(href))

                print(f"IDs found in hrefs: {len(href_ids)}")
                collected_ids.update(href_ids)
            except Exception as e:
                print(f"Anchor parse error: {e}")

            page.close()

        browser.close()

    print("\n====================")
    print(f"TOTAL COLLECTED IDS BEFORE SAVE: {len(collected_ids)}")

    saved_count = 0
    failed_count = 0

    for prdt_no in sorted(collected_ids):
        try:
            save_product_id(prdt_no)
            saved_count += 1
            print(f"Saved: {prdt_no}")
        except Exception as e:
            failed_count += 1
            print(f"FAILED TO SAVE {prdt_no}: {e}")

    print("\n====================")
    print(f"FINAL SUMMARY")
    print(f"Collected IDs: {len(collected_ids)}")
    print(f"Saved IDs: {saved_count}")
    print(f"Failed IDs: {failed_count}")


if __name__ == "__main__":
    collect_from_pages()
