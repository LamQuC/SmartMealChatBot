from pymongo import UpdateOne
import logging

from src.core.catalog_constants import MAIN_CATEGORY_EXCLUDE_FROM_MEAL_SHOPPING

class ProductRepository:
    def __init__(self, db):
        self.collection = db["products"]

    def upsert_many(self, products):
        operations = [
            UpdateOne(
                {"item_no": p["item_no"]}, 
                {"$set": p}, 
                upsert=True
            ) for p in products
        ]
        if operations:
            return self.collection.bulk_write(operations)
        return None

    def find_by_name(self, name):
        return self.collection.find_one({"name": name})

    def get_unique_categories(self):
        try:
            query_filter = {
                "main_category": "Gia vị",
                "category_level_5": {"$ne": None, "$ne": ""}
            }
            categories = self.collection.distinct("category_level_5", query_filter)
            clean_categories = sorted([str(c).strip() for c in categories if c])
            return clean_categories
        except Exception as e:
            logging.error(f"❌ Lỗi truy vấn MongoDB: {e}")
            return ["Nước mắm", "Nước tương", "Dầu ăn", "Đường", "Hạt nêm"]

    def find_cheaper_alternative(self, category_level_5, current_price, original_name=""):
        """
        Tìm sản phẩm cùng loại nhưng giá thấp hơn.
        SỬA TẠI ĐÂY: Thêm lọc theo tên để tránh đổi Thịt thành Cháo gói.
        """
        # 1. Tách từ khóa quan trọng nhất từ tên gốc (ví dụ: "Thịt", "Trứng", "Cần tây")
        # Đơn giản nhất là lấy từ đầu tiên hoặc từ quan trọng
        keyword = original_name.split()[0] if original_name else ""

        query = {
            "category_level_5": category_level_5,
            "price_final": {"$lt": current_price}
        }
        
        
        if keyword:
            query["name"] = {"$regex": keyword, "$options": "i"}

        return self.collection.find_one(
            query, 
            sort=[("price_final", 1)]
        )
    def get_products_by_main_category(self, main_category: str):
        """Lấy toàn bộ sản phẩm thuộc một danh mục chính (trường đã chuẩn hoá từ cleaner)."""
        projection = {
            "item_no": 1,
            "name": 1,
            "price_final": 1,
            "price_original": 1,
            "image_url": 1,
            "images": 1,
            "main_category": 1,
            "brand": 1,
            "short_description": 1,
            "thumbnail": 1,
        }
        return list(self.collection.find({"main_category": main_category}, projection))

    def find_by_item_no(self, item_no: str):
        """Một sản phẩm đầy đủ trường để hiển thị chi tiết."""
        if not item_no:
            return None
        return self.collection.find_one({"item_no": item_no})

    def get_all_main_categories(self):
        """Lấy danh sách các main_category hiện có trong DB (sắp xếp để dùng dropdown)."""
        cats = self.collection.distinct("main_category")
        return sorted([c for c in cats if c])
    def search_products(self, query: str, limit: int = 5):
        excluded_cats = list(MAIN_CATEGORY_EXCLUDE_FROM_MEAL_SHOPPING)

        search_filter = {
            "$and": [
                {"name": {"$regex": query, "$options": "i"}},
                {"main_category": {"$nin": excluded_cats}},
                {"price_final": {"$gt": 0}},
            ]
        }
        
        # Thực hiện truy vấn
        return list(self.collection.find(search_filter).limit(limit))