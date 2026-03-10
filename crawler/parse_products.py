import os
import json
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_products():

    raw = supabase.table("raw_products").select("*").execute()

    for row in raw.data:

        payload = json.loads(row["raw_payload"])

        if "product" not in payload:
            continue

        product = payload["product"]

        product_id = product.get("prdtNo")
        name = product.get("prdtNm")
        brand = product.get("brandNm")
        price = product.get("salePrc")

        image = None
        ingredients = None

        if "images" in payload:
            imgs = payload["images"]
            if len(imgs) > 0:
                image = imgs[0].get("imgUrl")

        if "details" in payload:
            ingredients = payload["details"].get("ingredients")

        supabase.table("products").insert({

            "product_id": product_id,
            "name": name,
            "brand": brand,
            "price": price,
            "image": image,
            "ingredients": ingredients

        }).execute()

        print("Inserted:", name)


if __name__ == "__main__":
    parse_products()
