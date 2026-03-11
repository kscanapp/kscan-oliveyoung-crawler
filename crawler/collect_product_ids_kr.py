import os
import re
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

URLS = [
    "https://www.oliveyoung.co.kr/store/main/getBestList.do",
    "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=90000010001&pageIdx=1",
    "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=90000010009&pageIdx=1",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.oliveyoung.co.kr/",
}

PATTERNS = [
    re.compile(r"goodsNo=([A-Z0-9]+)", re.IGNORECASE),
    re.compile(r'"goodsNo"\s*:\s*"([A-Z0-9]+)"', re.IGNORECASE),
    re.compile(r"\bA\d{12}\b"),
]


def extract_goods_nos(text: str):
    ids = set()
    for pattern in PATTERNS:
        for match in pattern.findall(text or ""):
            if isinstance(match, tuple):
                match = match[0]
            ids.add(match)
    return ids


def main():
    collected = set()

    os.makedirs("debug_output", exist_ok=True)

    for i, url in enumerate(URLS, start=1):
        print(f"\nFETCHING: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            print("STATUS:", r.status_code)
            print("CONTENT-TYPE:", r.headers.get("content-type"))

            html = r.text
            print("HTML LENGTH:", len(html))

            debug_path = f"debug_output/kr_page_{i}.html"
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(html)

            print("SAVED HTML:", debug_path)

            ids = extract_goods_nos(html)
            print("FOUND IDS:", len(ids))

            sample = list(sorted(ids))[:20]
            print("SAMPLE IDS:", sample)

            collected.update(ids)

        except Exception as e:
            print("REQUEST FAILED:", e)

    print("\n====================")
    print("TOTAL COLLECTED:", len(collected))

    for goods_no in sorted(collected):
        try:
            supabase.table("product_ids_kr").upsert(
                {
                    "goods_no": goods_no,
                    "detail_url": f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"
                },
                on_conflict="goods_no"
            ).execute()
            print("SAVED:", goods_no)
        except Exception as e:
            print("FAILED TO SAVE:", goods_no, e)

    print("====================")


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    collect()
