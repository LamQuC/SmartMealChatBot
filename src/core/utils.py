import re

def get_core_ingredient(product_name: str) -> str:
    """
    Trích xuất thực thể gốc từ tên sản phẩm.
    Ví dụ: 'Nước mắm Cát Hải 500ml' -> 'Nước mắm'
    """
    product_name = product_name.lower()
    
    keywords = [
        "nước mắm", "nước tương", "xì dầu", "đường", "mì chính", 
        "bột ngọt", "hạt nêm", "tương ớt", "tương cà", "dầu ăn", "mù tạt", 
        "tiêu", "giấm", "mắm tôm", "mắm tép", "dầu hào", "ngũ vị hương"
    ]
    
    for k in keywords:
        if k in product_name:
            return k.capitalize()
    return None

def get_unique_pantry_list(crawled_products: list):
    """
    Duyệt qua toàn bộ DB sản phẩm đã crawl để lấy ra danh sách 
    các loại gia vị duy nhất (Unique Entities).
    """
    pantry_set = set()
    for p in crawled_products:
        # Giả sử p là dict có key 'name' hoặc 'product_name'
        name = p.get('name') or p.get('product_name', "")
        core = get_core_ingredient(name)
        if core:
            pantry_set.add(core)
    return sorted(list(pantry_set))