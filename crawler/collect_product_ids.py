import os
import re
from datetime import datetime
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 먼저 TOP 페이지 후보들만 넣고 테스트
TARGET_URLS = [
    "https://global.oliveyoung.com",
    "https://global.oliveyoung.com/display/page/best-seller",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000008",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000009",
]

PRDT_REGEX = re.compile(r"prdtNo=([A-Z0-9]+)")
GA_REGEX = re.compile(r"\bGA\d+\b")


def save_product_id(prdt_no: str):
    try:
        supabase.table("product_ids").upsert(
            {
                "prdt_no": prdt_no,
                "collected_at": datetime.utcnow().isoformat()
            },
            on_conflict="prdt_no"
        ).execute()
        print("Saved:", prdt_no)
    except Exception as e:
        print(f"Failed to save {prdt_no}: {e}")


def extract_ids_from_text(text: str):
    ids = set()

    for match in PRDT_REGEX.findall(text):
        ids.add(match)

    for match in GA_REGEX.findall(text):
        ids.add(match)

    return ids


def collect_from_pages():
    collected_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for url in TARGET_URLS:
            page = browser.new_page()

            def handle_response(response):
                try:
                    response_url = response.url
                    lower_url = response_url.lower()

                    if "product" not in lower_url and "review" not in lower_url and "goods" not in lower_url:
                        return

                    content_type = response.headers.get("content-type", "").lower()

                    if "application/json" in content_type or "text" in content_type:
                        try:
                            body = response.text()
                            ids = extract_ids_from_text(body)
                            for prdt_no in ids:
                                collected_ids.add(prdt_no)
                        except Exception:
                            pass
                except Exception:
                    pass

            page.on("response", handle_response)

            print(f"Opening: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                print(f"Timed out on {url}, continuing...")

            page.wait_for_timeout(5000)

            # HTML에서도 추출
            try:
                html = page.content()
                ids = extract_ids_from_text(html)
                for prdt_no in ids:
                    collected_ids.add(prdt_no)
            except Exception:
                pass

            # href에서도 추출
            try:
                anchors = page.locator("a").evaluate_all(
                    "(elements) => elements.map(e => e.href || '')"
                )
                for href in anchors:
                    ids = extract_ids_from_text(href)
                    for prdt_no in ids:
                        collected_ids.add(prdt_no)
            except Exception:
                pass

            page.close()

        browser.close()

    print(f"Collected {len(collected_ids)} candidate product ids")

    for prdt_no in collected_ids:
        save_product_id(prdt_no)


if __name__ == "__main__":
    collect_from_pages()
