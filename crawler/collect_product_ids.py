import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

TARGET_URLS = [
    "https://global.oliveyoung.com",
    "https://global.oliveyoung.com/display/page/best-seller",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000008",
    "https://global.oliveyoung.com/display/category?ctgrNo=1000000009",
]

PRDT_REGEX = re.compile(r"prdtNo=([A-Z0-9]+)")
GA_REGEX = re.compile(r"\bGA\d+\b")


def extract_ids_from_text(text: str):
    ids = set()

    for match in PRDT_REGEX.findall(text):
        ids.add(match)

    for match in GA_REGEX.findall(text):
        ids.add(match)

    return ids


def main():
    all_ids = set()

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
                all_ids.update(html_ids)
            except Exception as e:
                print(f"HTML parse error: {e}")

            # 2) 모든 a href 출력 일부 확인
            try:
                anchors = page.locator("a").evaluate_all(
                    "(elements) => elements.map(e => e.href || '')"
                )

                print(f"Anchor count: {len(anchors)}")
                print("Sample hrefs:")
                for href in anchors[:20]:
                    print(href)

                href_ids = set()
                for href in anchors:
                    href_ids.update(extract_ids_from_text(href))

                print(f"IDs found in hrefs: {len(href_ids)}")
                all_ids.update(href_ids)

            except Exception as e:
                print(f"Anchor parse error: {e}")

            page.close()

        browser.close()

    print("\n====================")
    print(f"TOTAL COLLECTED IDS: {len(all_ids)}")
    for x in sorted(list(all_ids))[:50]:
        print(x)


if __name__ == "__main__":
    main()
