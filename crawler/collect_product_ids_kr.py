import os
import re
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.oliveyoung.co.kr/"
}

# 먼저 안정적으로 goodsNo가 많이 노출되는 페이지 위주로 시작
TARGET_URLS = [
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010001&pageIdx=1",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010001&pageIdx=2",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010001&pageIdx=3",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010009&pageIdx=1",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010009&pageIdx=2",
    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=90000010009&pageIdx=3",
]

GOODS_NO_REGEX_1 = re.compile(r"goodsNo=([A-Z0-9]+)")
GOODS_NO_REGEX_2 = re.compile(r'"goodsNo"\s*:\s*"([A-Z0-9]+)"')
GOODS_NO_REGEX_3 = re.compile(r"goodsNo['\"]?\s*[:=]\s*['\"]([A-Z0-9]+)['\"]")


def extract_goods_nos(text: str):
    ids = set()

    for regex in [GOODS_NO_REGEX_1, GOODS_NO_REGEX_2, GOODS_NO_REGEX_3]:
        for match in regex.findall(text or ""):
            ids.add(match)

    return ids


def save_goods_no(goods_no: str):
    try:
        supabase.table("product_ids_kr").upsert(
            {"goods_no": goods_no},
            on_conflict="goods_no"
        ).execute()
        print("SAVED:", goods_no)
    except Exception as e:
        print(f"FAILED TO SAVE {goods_no}: {e}")


def collect():
    collected = set()

    for url in TARGET_URLS:
        print(f"\nFETCHING: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            print("STATUS:", r.status_code)

            text = r.text
            print("HTML LENGTH:", len(text))

            ids = extract_goods_nos(text)
            print("FOUND IDs:", len(ids))

            for goods_no in ids:
                collected.add(goods_no)

        except Exception as e:
            print("REQUEST FAILED:", e)

    print("\n====================")
    print("TOTAL COLLECTED BEFORE SAVE:", len(collected))

    saved = 0
    failed = 0

    for goods_no in sorted(collected):
        try:
            save_goods_no(goods_no)
            saved += 1
        except Exception:
            failed += 1

    print("\n====================")
    print("FINAL SUMMARY")
    print("Collected:", len(collected))
    print("Saved:", saved)
    print("Failed:", failed)
    print("====================")


if __name__ == "__main__":
    collect()
