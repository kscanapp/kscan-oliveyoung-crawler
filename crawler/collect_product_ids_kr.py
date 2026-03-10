import os
import re
from urllib.parse import urljoin, urlparse, parse_qs

from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE = "https://www.oliveyoung.co.kr"

TARGET_URLS = [
    "https://www.oliveyoung.co.kr/store/main/getBestList.do",
]

DETAIL_PATH_KEYWORD = "/store/goods/getGoodsDetail.do"
GOODS_NO_FALLBACK = re.compile(r"goodsNo=([A-Z0-9]+)", re.IGNORECASE)


def extract_goods_no_from_href(href: str):
    if not href:
        return None

    try:
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        goods_no = qs.get("goodsNo", [None])[0]
        if goods_no:
            return goods_no
    except Exception:
        pass

    match = GOODS_NO_FALLBACK.search(href)
    if match:
        return match.group(1)

    return None


def save_goods(goods_no: str, detail_url: str):
    supabase.table("product_ids_kr").upsert(
        {
            "goods_no": goods_no,
            "detail_url": detail_url,
        },
        on_conflict="goods_no"
    ).execute()


def main():
    collected = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for url in TARGET_URLS:
            page = browser.new_page()

            print(f"\nOPENING: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                print("Timed out on page load, continuing...")

            page.wait_for_timeout(5000)

            hrefs = []
            try:
                hrefs = page.locator("a").evaluate_all(
                    "(els) => els.map(e => e.getAttribute('href') || e.href || '')"
                )
            except Exception as e:
                print("HREF EXTRACT ERROR:", e)

            print("ANCHOR COUNT:", len(hrefs))

            for href in hrefs:
                if not href:
                    continue

                abs_href = urljoin(BASE, href)

                if DETAIL_PATH_KEYWORD not in abs_href:
                    continue

                goods_no = extract_goods_no_from_href(abs_href)
                if not goods_no:
                    continue

                collected[goods_no] = abs_href

            page.close()

        browser.close()

    print("\n====================")
    print("TOTAL COLLECTED BEFORE SAVE:", len(collected))

    saved = 0
    for goods_no, detail_url in collected.items():
        try:
            save_goods(goods_no, detail_url)
            saved += 1
            print("SAVED:", goods_no, detail_url)
        except Exception as e:
            print("FAILED:", goods_no, e)

    print("\n====================")
    print("FINAL SUMMARY")
    print("Collected:", len(collected))
    print("Saved:", saved)
    print("====================")


if __name__ == "__main__":
    main()
