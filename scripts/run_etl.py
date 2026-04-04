import logging
import os
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.etl.crawl_data import main as run_crawl
from src.etl.add_main_category import update_main_category_in_json
from src.etl.loader import load_all_products
from scripts.build_embeddings import main as run_embedding

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)

def run_daily_pipeline():
    try:
        logging.info("=== BẮT ĐẦU PIPELINE HÀNG NGÀY ===")

        # BƯỚC 1: CRAWL DỮ LIỆU
        logging.info("B1: Đang crawl dữ liệu từ Winmart...")
        run_crawl()

        # BƯỚC 2: GÁN NHÃN CATEGORY TỪ TÊN FILE
        logging.info("B2: Đang gán main_category vào các file JSON...")
        # Lưu ý: Điều chỉnh DATA_FOLDER trong add_main_category.py thành "data/raw" để đồng bộ
        update_main_category_in_json("data/raw")

        # BƯỚC 3: CLEAN VÀ LOAD VÀO MONGODB
        logging.info("B3: Đang clean và load dữ liệu vào MongoDB...")
        load_all_products()

        # BƯỚC 4: BUILD EMBEDDING VÀ VECTOR SEARCH
        logging.info("B4: Đang tạo vector embedding cho sản phẩm...")
        run_embedding()

        logging.info("=== PIPELINE HOÀN THÀNH THÀNH CÔNG ===")
    
    except Exception as e:
        logging.error(f"!!! PIPELINE THẤT BẠI tại bước nào đó: {e}")

if __name__ == "__main__":
    run_daily_pipeline()