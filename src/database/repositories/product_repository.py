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

    # --- SỬA TẠI ĐÂY: Trả về category tổng quát, không chỉ mỗi Gia vị ---
    def get_unique_categories(self, main_category=None):
        """Lấy danh sách category_level_5. Nếu có main_category thì lọc theo đó."""
        try:
            query_filter = {"category_level_5": {"$ne": None, "$ne": ""}}
            if main_category:
                query_filter["main_category"] = main_category
                
            categories = self.collection.distinct("category_level_5", query_filter)
            return sorted([str(c).strip() for c in categories if c])
        except Exception as e:
            logging.error(f"❌ Lỗi truy vấn MongoDB: {e}")
            return []

    def find_cheaper_alternative(self, category_level_5, current_price, original_name=""):
        """
        Tìm sản phẩm rẻ hơn cùng loại và cùng từ khóa chính.
        """
        # Tách keyword thông minh hơn: Bỏ qua các từ định lượng/quảng cáo
        words = original_name.split()
        stopwords = ["combo", "gói", "túi", "hộp", "khay", "bịch", "vỉ", "set", "siêu", "rẻ"]
        
        keyword = ""
        for w in words:
            if w.lower() not in stopwords:
                keyword = w
                break
        
        query = {
            "category_level_5": category_level_5,
            "price_final": {"$lt": current_price},
            "price_final": {"$gt": 0} # Đảm bảo không lấy hàng hết giá hoặc lỗi
        }
        
        if keyword:
            query["name"] = {"$regex": keyword, "$options": "i"}

        return self.collection.find_one(
            query, 
            sort=[("price_final", 1)] # Lấy thằng rẻ nhất đứng đầu
        )

    def get_products_by_main_category(self, main_category: str):
        projection = {
            "item_no": 1, "name": 1, "price_final": 1, "price_original": 1,
            "image_url": 1, "images": 1, "main_category": 1, "brand": 1,
            "short_description": 1, "thumbnail": 1,
        }
        return list(self.collection.find({"main_category": main_category}, projection))

    def find_by_item_no(self, item_no: str):
        if not item_no: return None
        return self.collection.find_one({"item_no": item_no})

    def get_all_main_categories(self):
        cats = self.collection.distinct("main_category")
        return sorted([c for c in cats if c])

    def search_products(self, query: str, limit: int = 5):
        """Tìm kiếm hàng hóa để AI match nguyên liệu"""
        excluded_cats = list(MAIN_CATEGORY_EXCLUDE_FROM_MEAL_SHOPPING)

        # Ưu tiên tìm hàng có giá và không nằm trong danh sách loại trừ (như gia vị lẻ)
        search_filter = {
            "name": {"$regex": query, "$options": "i"},
            "main_category": {"$nin": excluded_cats},
            "price_final": {"$gt": 0},
        }
        
        return list(self.collection.find(search_filter).limit(limit))