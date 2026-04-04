from pymongo import UpdateOne
import logging

class ProductRepository:
    def __init__(self, db):
        # db là đối tượng database lấy từ get_mongo_client()
        self.collection = db["products"]

    def upsert_many(self, products):
        """Sử dụng bulk_write để update hoặc insert hàng loạt dựa trên item_no."""
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

    def get_unique_categories(self): # <--- Đã thêm 'self' vào đây
        """
        Truy vấn danh sách Gia vị duy nhất từ category_level_5.
        Điều kiện: main_category == "Gia vị"
        """
        try:
            # 1. Định nghĩa điều kiện lọc
            query_filter = {
                "main_category": "Gia vị",
                "category_level_5": {"$ne": None, "$ne": ""}
            }
            
            # 2. Sử dụng distinct thông qua self.collection
            categories = self.collection.distinct("category_level_5", query_filter)
            
            # 3. Làm sạch dữ liệu đầu ra
            clean_categories = sorted([str(c).strip() for c in categories if c])
            
            return clean_categories
        
        except Exception as e:
            logging.error(f"❌ Lỗi truy vấn MongoDB: {e}")
            # Trả về danh sách mặc định để UI không crash
            return ["Nước mắm", "Nước tương", "Dầu ăn", "Muối", "Đường", "Hạt nêm"]