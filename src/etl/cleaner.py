from datetime   import datetime
from src.etl.category_mapper import normalize_category

def clean_product(raw: dict) -> dict:
    final_price = raw.get("salePrice") or raw.get("price")

    return {
        "product_id": raw.get("id"),
        "item_no": raw.get("itemNo"),
        "name": raw.get("name"),
        "brand": raw.get("brandName"),
        "price_original": int(raw.get("price") or 0),
        "price_sale": int(raw.get("salePrice")) if raw.get("salePrice") else None,
        "price_final": int(final_price) if final_price else 0,
        "stock_quantity": raw.get("quantity"),
        "category_level_1": normalize_category(raw.get("mch1")),
        "category_level_2": normalize_category(raw.get("mch2")),
        "category_level_3": normalize_category(raw.get("mch3")),
        "category_level_4": normalize_category(raw.get("mch4")),
        "category_level_5": normalize_category(raw.get("mch5")),
        "short_description": raw.get("shortDescription"),
        "long_description": raw.get("longDescription"),
        "attributes": raw.get("attributes") or {},
        "created_at": datetime.utcnow(),
        "main_category": normalize_category(raw.get("main_category")),
    }
    
