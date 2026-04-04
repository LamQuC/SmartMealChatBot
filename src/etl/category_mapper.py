import re
import unicodedata


CATEGORY_MAP = {
    "thucphamkho": "Thực phẩm khô",
    "thucphamdonglanh": "Thực phẩm đông lạnh",
    "banhkeo": "Bánh kẹo",
    "douongcocon": "Đồ uống có cồn",
    "giavi": "Gia vị",
    "suacacloai": "Sữa các loại",
    "raucotraicay": "Rau củ trái cây",
    "mithucphamanlien": "Mì & Thực phẩm ăn liền",
    "thithaisantuoi": "Thịt & Hải sản tươi",
    "douonggiaikhat": "Đồ uống giải khát",
    "trungdauhu": "Trứng & Đậu hũ",
    "thucphamchebien": "Thực phẩm chế biến",
}

def slugify(text):
    """Chuyển đổi văn bản thành dạng slug không dấu, viết thường."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text)
    text = text.lower()
    text = re.sub(r"\s+", "_", text)
    return text

def normalize_category(raw_category):
    """
    Trả về tên Tiếng Việt chuẩn từ CATEGORY_MAP.
    Nếu không tìm thấy, trả về dạng slug đã làm sạch.
    """
    if not raw_category:
        return None
    
    
    clean_key = raw_category.strip().lower()
    normalized = CATEGORY_MAP.get(clean_key)
    
    if normalized:
        return normalized
    
    
    return slugify(raw_category)