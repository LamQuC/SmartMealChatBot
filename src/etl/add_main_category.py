import os
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def extract_main_category(filename: str) -> str:
    """
    Trích xuất code danh mục từ tên file JSON.
    Ví dụ: 'thit-tuoi-song--c02.json' -> 'thittuoisong'
    """
   
    name_part = filename.split("--")[0]
    
    return name_part.replace("-", "").lower()

def update_main_category_in_json(data_folder: str):
    """
    Đọc các file JSON, thêm trường main_category và lưu đè lại file.
    """
    base_path = Path(data_folder)
    
    if not base_path.exists():
        logging.error(f"Đường dẫn không tồn tại: {data_folder}")
        return

   
    files = list(base_path.glob("*.json"))
    logging.info(f"Bắt đầu xử lý {len(files)} file tại {data_folder}")

    for file_path in files:
        main_cat_code = extract_main_category(file_path.name)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                products = json.load(f)

            if isinstance(products, list):
                
                for p in products:
                    p["main_category"] = main_cat_code
                
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
                
                logging.info(f"Thành công: {file_path.name} -> {main_cat_code}")
            else:
                logging.warning(f"Bỏ qua {file_path.name}: Định dạng không phải List.")

        except Exception as e:
            logging.error(f"Lỗi khi xử lý file {file_path.name}: {e}")

if __name__ == "__main__":

    TARGET_DIR = os.path.join("data", "raw") 
    
    update_main_category_in_json(TARGET_DIR)
    logging.info("Hoàn tất cập nhật main_category cho toàn bộ dữ liệu thô.")