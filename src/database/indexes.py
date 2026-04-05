"""
MongoDB Indexes Setup Script
============================

Tạo các index cần thiết để tối ưu hiệu suất tìm kiếm trong MongoDB.

Cách sử dụng:
  1. Chạy thủ công (lần đầu setup):
     $ python src/database/indexes.py
  
  2. Tự động (hàng ngày qua run_etl.py):
     $ python scripts/run_etl.py
     # sẽ tự động gọi setup_mongodb_indexes()

Indexes tạo:
  - item_no (UNIQUE): Định danh sản phẩm duy nhất
  - main_category: Tìm kiếm theo danh mục chính
  - name: Tìm kiếm theo tên sản phẩm
"""

from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient("mongodb://localhost:27017/")
db = client["smart_meal_db"]

try:
    logger.info("Đang tạo MongoDB indexes...")
    
    # Index duy nhất trên item_no để tránh trùng lặp
    db.products.create_index("item_no", unique=True)
    logger.info("✅ Index 'item_no' (UNIQUE) tạo thành công")
    
    # Index trên main_category để tìm kiếm nhanh theo danh mục
    db.products.create_index("main_category")
    logger.info("✅ Index 'main_category' tạo thành công")
    
    # Index trên name để tìm kiếm nhanh theo tên
    db.products.create_index("name")
    logger.info("✅ Index 'name' tạo thành công")
    
    logger.info("✅ Tất cả indexes đã sẵn sàng")
    
except Exception as e:
    logger.error(f"❌ Lỗi tạo indexes: {e}")
    raise
finally:
    client.close()
