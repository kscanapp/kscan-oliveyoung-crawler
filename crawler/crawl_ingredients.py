import os
import re
import html
from supabase import create_client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

BASE_URL = "https://global.oliveyoung.com/product/detail?prdtNo="


def normalize_text(text):
    if not text:
        return None

    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) < 8:
        return None

    return text


def extract_featured_ingredients_from_details(details):
    if not isinstance(details, dict):
        return None

    # 현재 로그에서 실제로 확인된 필드
    candidates = [
        "ftrdIngrdText",
        "featuredIngredientText",
        "featuredIngredients",
    ]

    for key in candidates:
        value = details.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_text(value)

    return None


def extract_full_ingredients_from_details(details):
    if not isinstance(details, dict):
        return None

    # 혹시 full ingredient 관련 키가 있을 수 있으므로 폭넓게 시도
    direct_candidates = [
        "ingredients",
        "ingredient",
        "ingr",
        "fullIngredients",
        "allIngredients",
        "ingredientsText",
        "fullIngredientText",
        "prdtIngrdText",
    ]

    for key in direct_candidates:
        value = details.get(key)
        if isinstance(value, str) and value.strip():
            cleaned = normalize_text(value)
            if cleaned:
                return cleaned

    # HTML/설명 텍스트 안에서 full ingredients 구간 찾기
    html_candidates = [
        details.get("dtlDesc"),
        details.get("dtlAddDesc"),
        details.get("whyWeLoveItText"),
        details.get("howToUseText"),
        details.get("sellingPointText"),
    ]

    for raw_html in html_candidates:
        if not isinstance(raw_html, str) or not raw_html.strip():
            continue

        full = extract_ingredients_from_html_blob(raw_html)
        if full:
            return full

    return None


def extract_ingredients_from_html_blob(raw_html):
    if not raw_html:
        return None

    text = html.unescape(raw_html)

    # 줄바꿈/태그 정리 전, 라벨 기반으로 먼저 추출
    patterns = [
        r"(?:Full Ingredients|Ingredients|INGREDIENTS|전성분)\s*[:：]?\s*(.{20,5000})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidate = match.group(1)

            # 다음 섹션 제목이 나오기 전까지만 자르기
            candidate = re.split(
                r"(How to Use|HOW TO USE|Why We Love It|WHY WE LOVE IT|Caution|CAUTION|사용법|주의사항)",
                candidate,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0]

            cleaned = normalize_text(candidate)
            if cleaned and len(cleaned) >= 20:
                return cleaned

    # fallback: 태그 제거 후 다시 시도
    plain = normalize_text(raw_html)
    if not plain:
        return None

    plain_patterns = [
        r"(?:Full Ingredients|Ingredients|INGREDIENTS|전성분)\s*[:：]?\s*(.{20,3000})",
    ]

    for pattern in plain_patterns:
        match = re.search(pattern, plain, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidate = match.group(1)
            candidate = re.split(
                r"(How to Use|WHY WE LOVE IT|Why We Love It|사용법|주의사항)",
                candidate,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0]
            cleaned = normalize_text(candidate)
            if cleaned and len(cleaned) >= 20:
                return cleaned

    return None


def update_product_ingredients(product_id, featured_raw, full_raw, source):
    # ingredients_raw는 앱이 바로 쓰는 대표값
    # full_raw가 있으면 full 우선, 없으면 featured fallback
    final_raw = full_raw or featured_raw

    supabase.table("products").upsert(
        {
            "product_id": product_id,
            "ingredients_raw": final_raw,
            "ingredients_featured_raw": featured_raw,
            "ingredients_full_raw": full_raw,
            "ingredients_source": source,
        },
        on_conflict="product_id"
    ).execute()

    print(f"UPDATED: {product_id} / source={source}")


def crawl_one_product(product_id):
    url = f"{BASE_URL}{product_id}"

    print("\n==============================")
    print("CRAWLING:", product_id)
    print("URL:", url)

    featured_found = None
    full_found = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            nonlocal featured_found, full_found

            try:
                content_type = response.headers.get("content-type", "").lower()
                if "application/json" not in content_type:
                    return

                response_url = response.url.lower()

                # details-info가 핵심
                if "details-info" not in response_url and "product" not in response_url:
                    return

                data = response.json()

                if not isinstance(data, dict):
                    return

                details = data.get("details")
                if not isinstance(details, dict):
                    return

                if not featured_found:
                    featured_found = extract_featured_ingredients_from_details(details)

                if not full_found:
                    full_found = extract_full_ingredients_from_details(details)

                if featured_found:
                    print("FOUND FEATURED INGREDIENTS")
                if full_found:
                    print("FOUND FULL INGREDIENTS")

            except Exception:
                pass

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            print("Timed out on page load, continuing...")

        page.wait_for_timeout(5000)
        browser.close()

    if full_found:
        update_product_ingredients(
            product_id=product_id,
            featured_raw=featured_found,
            full_raw=full_found,
            source="full_from_details"
        )
    elif featured_found:
        update_product_ingredients(
            product_id=product_id,
            featured_raw=featured_found,
            full_raw=None,
            source="featured_fallback"
        )
    else:
        print("NO INGREDIENTS FOUND:", product_id)


def main():
    # 아직 ingredients_source가 없는 상품 위주로 돌림
    rows = supabase.table("products").select(
        "product_id, ingredients_raw, ingredients_source"
    ).limit(200).execute()

    if not rows.data:
        print("No products found.")
        return

    targets = []
    for row in rows.data:
        product_id = row.get("product_id")
        ingredients_source = row.get("ingredients_source")

        if product_id and not ingredients_source:
            targets.append(product_id)

    print("TARGET COUNT:", len(targets))

    for product_id in targets:
        crawl_one_product(product_id)


if __name__ == "__main__":
    main()
