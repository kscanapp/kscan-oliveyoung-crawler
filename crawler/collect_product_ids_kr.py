import os
import re
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# 한국 올리브영에서 실제로 goodsNo가 노출될 가능성이 높은 페이지부터 시작
TARGET_URLS = [
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010001&pageIdx=1",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010001&pageIdx=2",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010001&pageIdx=3",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010009&pageIdx=1",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010009&pageIdx=2",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010009&pageIdx=3",
]

# goods 상세 URL 패턴
REGEXES = [
    re.compile(r"goodsNo=([A-Z0-9]+)", re.IGNORECASE),
    re.compile(r'"goodsNo"\s*:\s*"([A-Z0-9]+)"', re.IGNORECASE),
    re.compile(r"goodsNo['\"]?\s*[:=]\s*['\"]([A-Z0-9]+)['\"]", re.IGNORECASE),
    re.compile(r"\bA\d{12}\b"),  # 예: A000000231894
]


def extract_goods_nos(text: str):
    ids = set()
    if not text:
        return ids

    for regex in REGEXES:
        for match in regex.findall(text):
            if isinstance(match, tuple):
                match = match[0]
            ids.add(match)

    return ids


def save_goods_no(goods_no: str):
    supabase.table("product_ids_kr").upsert(
        {"goods_no": goods_no},
        on_conflict="goods_no"
    ).execute()


def main():
    collected = set()

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

            # 1) HTML 전체에서 추출
            try:
                html = page.content()
                html_ids = extract_goods_nos(html)
                print(f"FOUND IN HTML: {len(html_ids)}")
                collected.update(html_ids)
            except Exception as e:
                print(f"HTML PARSE ERROR: {e}")

            # 2) href에서 추출
            try:
                hrefs = page.locator("a").evaluate_all(
                    "(els) => els.map(e => e.href || '')"
                )
                href_ids = set()
                for href in hrefs:
                    href_ids.update(extract_goods_nos(href))

                print(f"FOUND IN HREFS: {len(href_ids)}")
                collected.update(href_ids)

                print("SAMPLE HREFS:")
                for href in hrefs[:15]:
                    print(href)

            except Exception as e:
                print(f"HREF PARSE ERROR: {e}")

            # 3) 이미지 src에도 goodsNo가 숨어 있을 수 있어서 같이 추출
            try:
                srcs = page.locator("img").evaluate_all(
                    "(els) => els.map(e => e.src || '')"
                )
                src_ids = set()
                for src in srcs:
                    src_ids.update(extract_goods_nos(src))

                print(f"FOUND IN IMG SRCS: {len(src_ids)}")
                collected.update(src_ids)

            except Exception as e:
                print(f"IMG PARSE ERROR: {e}")

            page.close()

        browser.close()

    print("\n====================")
    print(f"TOTAL COLLECTED BEFORE SAVE: {len(collected)}")

    saved = 0
    failed = 0

    for goods_no in sorted(collected):
        try:
            save_goods_no(goods_no)
            saved += 1
            print(f"SAVED: {goods_no}")
        except Exception as e:
            failed += 1
            print(f"FAILED TO SAVE {goods_no}: {e}")

    print("\n====================")
    print("FINAL SUMMARY")
    print(f"Collected: {len(collected)}")
    print(f"Saved: {saved}")
    print(f"Failed: {failed}")
    print("====================")


if __name__ == "__main__":
    main()
