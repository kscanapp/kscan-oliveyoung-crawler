import requests
from bs4 import BeautifulSoup
import os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://global.oliveyoung.com"

CATEGORY_URL = f"{BASE_URL}/display/category?ctgrNo=1000001001"


def crawl_products():

    response = requests.get(CATEGORY_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    products = []

    for item in soup.select(".prd_info")[:50]:

        name = item.select_one(".prd_name").text.strip()
        price = item.select_one(".price_real").text.strip()
        image = item.select_one("img")["src"]

        product = {
            "brand": "",
            "product_name": name,
            "price_krw": price,
            "image_url": image,
            "oliveyoung_url": BASE_URL
        }

        products.append(product)

    return products


def save_to_db(products):

    for p in products:
        supabase.table("products").upsert(p).execute()


if __name__ == "__main__":

    products = crawl_products()

    print(f"Crawled {len(products)} products")

    save_to_db(products)
