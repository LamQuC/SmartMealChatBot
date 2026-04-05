"""Danh mục không đưa vào giỏ tính ngân sách / khớp nguyên liệu chính (gia vị, đồ uống, mì ăn liền...)."""

# Giá trị sau normalize_category() trong DB (cleaner.py + category_mapper)
MAIN_CATEGORY_EXCLUDE_FROM_MEAL_SHOPPING = frozenset(
    {
        "Gia vị",
        "Mì & Thực phẩm ăn liền",
        "Đồ uống có cồn",
        "Đồ uống giải khát",
        # Một số bản ghi cũ có thể còn mã slug thay vì tên đã chuẩn hoá
        "giavi",
        "mithucphamanlien",
        "douongcocon",
        "douonggiaikhat",
    }
)


def is_excluded_main_category(main_category: str | None) -> bool:
    if not main_category:
        return False
    key = str(main_category).strip()
    return key in MAIN_CATEGORY_EXCLUDE_FROM_MEAL_SHOPPING or key.lower() in MAIN_CATEGORY_EXCLUDE_FROM_MEAL_SHOPPING
