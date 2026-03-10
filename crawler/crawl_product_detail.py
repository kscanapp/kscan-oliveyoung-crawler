import os
import json
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE_URL = "https://global.oliveyoung.com/product/detail?prdtNo="


def save_raw_product(source_url: str, payload):
    try:
        payload_str = json.dumps(payload, ensure_ascii=False)
        payload_str = payload_str[:50000]

        supabase.table("raw_products").insert({
            "source_url": source_url,
            "raw_payload": payload_str
        }).execute()

        print(f"Saved raw payload for: {source_url}")

    except Exception as e:
        print(f"Failed to save raw payload for {source_url}: {e}")


def is_useful_payload(response_url: str, data):
    """
    products 테이블 정규화에 실제로 도움이 되는 payload만 저장
    저장 대상:
    - product
    - images
    - details
    제외 대상:
    - reviewList
    - reviewMediaList
    - recommendation/tracking 등
    """

    lower_url = response_url.lower()

    if not isinstance(data, dict):
        return False

    # 저장할 핵심 키
    if "product" in data:
        return True
    if "images" in data:
        return True
    if "details" in data:
        return True

    # 리뷰/미디어는 제외
    if "reviewlist" in lower_url:
        return False
    if "review-media-list" in lower_url:
        return False

    return False


def crawl_one_product(prdt_no: str):
    url = f"{BASE_URL}{prdt_no}"
    found_json = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            try:
                response_url = response.url
                lower_url = response_url.lower()
                content_type = response.headers.get("content-type", "").lower()

                if "application/json" not in content_type:
                    return

                # 상품 관련 응답만
                if (
                    "product" not in lower_url
                    and "goods" not in lower_url
                    and "detail" not in lower_url
                ):
                    return

                data = response.json()

                if is_useful_payload(response_url, data):
                    found_json.append((response_url, data))

            except Exception:
                pass

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            print(f"Timed out loading {url}, continuing...")

        page.wait_for_timeout(5000)
        browser.close()

    saved_count = 0

    for response_url, data in found_json:
        save_raw_product(response_url, data)
        saved_count += 1

    print(f"{prdt_no}: captured {len(found_json)} useful JSON responses, saved {saved_count}")


def main():
    rows = supabase.table("product_ids").select("prdt_no").limit(200).execute()

    if not rows.data:
        print("No product_ids found.")
        return

    print(f"Loaded {len(rows.data)} product ids")

    for row in rows.data:
        prdt_no = row.get("prdt_no")
        if not prdt_no:
            continue

        crawl_one_product(prdt_no)


if __name__ == "__main__":
    main()
