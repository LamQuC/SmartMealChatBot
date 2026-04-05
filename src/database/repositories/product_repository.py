from pymongo import UpdateOne
import logging

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
            return ["Nước mắm", "Nước tương", "Dầu ăn", "Muối", "Đường", "Hạt nêm"]

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