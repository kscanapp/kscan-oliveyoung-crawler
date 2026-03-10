import os
from supabase import create_client, Client
from playwright.sync_api import sync_playwright

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://global.oliveyoung.com"
CATEGORY_URL = f"{BASE_URL}/display/category?ctgrNo=1000001001"


def crawl_products():
    products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CATEGORY_URL, wait_until="networkidle", timeout=60000)

        print("Page loaded:", page.title())

        # 전체 HTML 먼저 확인용
        html = page.content()
        print("HTML length:", len(html))

        # 상품 카드 후보 탐색
        candidate_selectors = [
            ".prd_info",
            ".product-item",
            ".prdList li",
            ".product-list li",
            "[data-product-no]"
        ]

        items = []
        matched_selector = None

        for selector in candidate_selectors:
            found = page.locator(selector).count()
            print(f"Selector {selector}: {found}")
            if found > 0:
                items = page.locator(selector)
                matched_selector = selector
                break

        if not matched_selector:
            print("No product selector matched.")
            browser.close()
            return products

        print("Using selector:", matched_selector)

        count = min(items.count(), 50)

        for i in range(count):
            item = items.nth(i)

            name = ""
            price = ""
            image = ""
            product_url = BASE_URL

            # 여러 후보 셀렉터로 안전하게 추출
            for sel in [".prd_name", ".name", ".product-name", "img[alt]"]:
                try:
                    loc = item.locator(sel).first
                    if loc.count() > 0:
                        text = loc.inner_text().strip() if sel != "img[alt]" else loc.get_attribute("alt")
                        if text:
                            name = text.strip()
                            break
                except:
                    pass

            for sel in [".price_real", ".price", ".sale-price", ".product-price"]:
                try:
                    loc = item.locator(sel).first
                    if loc.count() > 0:
                        text = loc.inner_text().strip()
                        if text:
                            price = text
                            break
                except:
                    pass

            try:
                img = item.locator("img").first
                if img.count() > 0:
                    image = img.get_attribute("src") or ""
            except:
                pass

            try:
                link = item.locator("a").first
                if link.count() > 0:
                    href = link.get_attribute("href")
                    if href:
                        product_url = href if href.startswith("http") else BASE_URL + href
            except:
                pass

            if not name:
                continue

            products.append({
                "brand": "",
                "product_name": name,
                "price_krw": price,
                "image_url": image,
                "oliveyoung_url": product_url
            })

        browser.close()

    print(f"Crawled {len(products)} products")
    return products


def save_to_db(products):
    if not products:
        print("No products found to save.")
        return

    result = supabase.table("products").upsert(products).execute()
    print(f"Saved {len(products)} products")
    print(result)


if __name__ == "__main__":
    products = crawl_products()
    save_to_db(products)
