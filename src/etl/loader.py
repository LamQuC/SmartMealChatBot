import os
import json
import logging
from src.etl.cleaner import clean_product
from src.database.repositories.product_repository import ProductRepository
from src.database.mongo_client import get_mongo_client

# Cấu hình logging để theo dõi tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Đường dẫn đến thư mục chứa các file JSON đã crawl và gán nhãn
RAW_FOLDER = os.path.join("data", "raw")

def load_all_products():
    """
    Đọc tất cả các file JSON, làm sạch dữ liệu và đẩy vào MongoDB 
    theo cơ chế Upsert để tránh trùng lặp.
    """
    try:
        db = get_mongo_client()
        product_repo = ProductRepository(db)
        
        if not os.path.exists(RAW_FOLDER):
            logging.error(f"Thư mục dữ liệu không tồn tại: {RAW_FOLDER}")
            return

        json_files = [f for f in os.listdir(RAW_FOLDER) if f.endswith(".json")]
        logging.info(f"Tìm thấy {len(json_files)} file để xử lý.")

        for file_name in json_files:
            file_path = os.path.join(RAW_FOLDER, file_name)
            
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    raw_products = json.load(f)
                except json.JSONDecodeError:
                    logging.error(f"Lỗi định dạng JSON tại file: {file_name}")
                    continue

                if not isinstance(raw_products, list):
                    logging.warning(f"Bỏ qua {file_name}: Dữ liệu không phải là một danh sách.")
                    continue

                # Làm sạch dữ liệu trước khi đưa vào DB
                cleaned_products = [clean_product(p) for p in raw_products]
                
                if cleaned_products:

                    result = product_repo.upsert_many(cleaned_products)
                    
                    if result:
                        logging.info(
                            f"Hoàn thành {file_name}: "
                            f"Đã xử lý {len(cleaned_products)} sản phẩm "
                            f"(Thêm mới/Cập nhật: {result.upserted_count + result.modified_count})"
                        )
                else:
                    logging.info(f"Không có dữ liệu hợp lệ trong {file_name}")

    except Exception as e:
        logging.error(f"Lỗi hệ thống trong quá trình Load: {e}")

if __name__ == "__main__":
    load_all_products()