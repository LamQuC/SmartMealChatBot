
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# =========================
# CONFIG
# =========================
BASE_CATEGORY_API = "https://api-crownx.winmart.vn/mt/api/web/v1/category"
BASE_PRODUCT_API = "https://api-crownx.winmart.vn/it/api/web/v3/item/category"
BASE_ATTRIBUTE_API = "https://api-crownx.winmart.vn/it/api/web/v3/item/attribute"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://winmart.vn/"
}

STORE_CODE = 1665
STORE_GROUP_CODE = 1998
PAGE_SIZE = 50
MAX_WORKERS = 10
REQUEST_TIMEOUT = 15
RETRY_COUNT = 3

OUTPUT_DIR = os.path.join("data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Food category codes from Winmart
FOOD_CODES = {
    "02", "03", "04", "05", "06",
    "07", "08", "09", "31", "33",
    "34", "35"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# HELPERS
# =========================
def safe_get(url, params=None):
    """HTTP GET with retry."""
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                return response.json()

            logging.warning(
                f"Status {response.status_code} for {url} | Attempt {attempt}/{RETRY_COUNT}"
            )

        except Exception as e:
            logging.warning(
                f"Request failed: {e} | Attempt {attempt}/{RETRY_COUNT}"
            )

        time.sleep(1)

    return None


def clean_html(text):
    if not text:
        return ""

    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


# =========================
# CATEGORY
# =========================
def get_food_category_slugs():
    """Get only food category slugs from Winmart category API."""
    data = safe_get(BASE_CATEGORY_API)

    if not data or "data" not in data:
        raise RuntimeError("Cannot load category data")

    slugs = []

    for item in data["data"]:
        parent = item.get("parent") or {}
        slug = parent.get("seoName")

        if not slug:
            continue

        try:
            category_code = slug.split("--c")[-1]
        except Exception:
            continue

        if category_code in FOOD_CODES:
            slugs.append(slug)

    slugs = sorted(list(set(slugs)))

    logging.info(f"Found {len(slugs)} food category slugs")
    return slugs


# =========================
# PRODUCT CRAWLING
# =========================
def crawl_slug_products(slug):
    """Crawl all products for one slug."""
    products = []
    page = 1

    while True:
        params = {
            "pageNumber": page,
            "pageSize": PAGE_SIZE,
            "slug": slug,
            "storeCode": STORE_CODE,
            "storeGroupCode": STORE_GROUP_CODE,
        }

        data = safe_get(BASE_PRODUCT_API, params=params)

        if not data or "data" not in data:
            logging.warning(f"[{slug}] Failed to fetch page {page}")
            break

        items = data["data"].get("items", [])

        if not items:
            logging.info(f"[{slug}] No more products at page {page}")
            break

        logging.info(f"[{slug}] Crawling page {page} - {len(items)} products")
        for p in items:
            raw_images = p.get("mediaUrl", [])

            if isinstance(raw_images, str):
                try:
                    decoded = json.loads(raw_images)
                    raw_images = decoded if isinstance(decoded, list) else [decoded]
                except Exception:
                    raw_images = [{"url": raw_images}] if raw_images else []
            elif isinstance(raw_images, dict):
                raw_images = [raw_images]
            elif not isinstance(raw_images, list):
                raw_images = []

            image_urls = []
            for img in raw_images:
                if isinstance(img, dict) and img.get("url"):
                    image_urls.append(img.get("url"))
                elif isinstance(img, str):
                    image_urls.append(img)

            product = {
                "id": p.get("id"),
                "itemNo": p.get("itemNo"),
                "name": p.get("name"),
                "seoName": p.get("seoName"),
                "brandName": p.get("brandName"),
                "price": p.get("price"),
                "salePrice": p.get("salePrice"),
                "quantity": p.get("quantity"),
                "images": image_urls,
                "mch1": p.get("mch1Name"),
                "mch2": p.get("mch2Name"),
                "mch3": p.get("mch3Name"),
                "mch4": p.get("mch4Name"),
                "mch5": p.get("mch5Name"),
                "shortDescription": p.get("shortDescription"),
                "longDescription": clean_html(p.get("longDescription")),
            }
            products.append(product)

        page += 1
        time.sleep(0.5)

    return products


# =========================
# ATTRIBUTE CRAWLING
# =========================
def get_item_attributes(item_no):
    params = {"itemNo": item_no}
    data = safe_get(BASE_ATTRIBUTE_API, params=params)

    attributes = {}

    if data and data.get("data"):
        for attr in data["data"]:
            label = attr.get("label")
            value = attr.get("value")

            if label:
                attributes[label] = value

    return item_no, attributes


def batch_get_attributes(item_nos):
    """Fetch attributes concurrently."""
    results = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(get_item_attributes, item_no): item_no
            for item_no in item_nos
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="Attributes"):
            try:
                item_no, attributes = future.result()
                results[item_no] = attributes
            except Exception as e:
                logging.warning(f"Attribute fetch failed: {e}")

    return results


# =========================
# SAVE
# =========================
def save_slug_json(slug, products):
    safe_slug = slug.replace("/", "_").replace("\\", "_")
    filepath = os.path.join(OUTPUT_DIR, f"{safe_slug}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    logging.info(f"Saved {len(products)} products -> {filepath}")


# =========================
# MAIN
# =========================
def main():
    slugs = get_food_category_slugs()

    logging.info("=" * 60)
    logging.info(f"Starting crawl for {len(slugs)} categories")
    logging.info("=" * 60)

    for idx, slug in enumerate(slugs, start=1):
        logging.info(f"\n[{idx}/{len(slugs)}] Crawling slug: {slug}")

        raw_products = crawl_slug_products(slug)

        if not raw_products:
            logging.warning(f"No products found for {slug}")
            continue

        item_nos = [p["itemNo"] for p in raw_products if p.get("itemNo")]
        attribute_map = batch_get_attributes(item_nos)

        for product in raw_products:
            product["attributes"] = attribute_map.get(product.get("itemNo"), {})

        save_slug_json(slug, raw_products)

        logging.info(
            f"Finished {slug} | Products: {len(raw_products)}"
        )

    logging.info("\nDone crawling all food categories")


if __name__ == "__main__":
    main()

