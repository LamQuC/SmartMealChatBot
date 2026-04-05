from src.core.logger import logger
from src.core.catalog_constants import is_excluded_main_category
from src.tools.product_search_tool import ProductSearchTool

class IngredientMatcherAgent:
    def __init__(self):
        # Tool này kết nối với Vector DB thông qua ProductSearchTool
        self.product_tool = ProductSearchTool()

    def run(self, ingredients: list, user_profile: dict = None) -> list:
        """
        Nhiệm vụ: Tìm sản phẩm tươi sống thực tế cho nguyên liệu cần mua.
        Sử dụng main_category từ tầng DB để loại bỏ hàng ăn liền/gia vị.
        """
        logger.info(f"[IngredientMatcherAgent] Khớp hàng thực tế cho: {ingredients}")
        
        user_profile = user_profile or {}
        allergies = [a.lower().strip() for a in user_profile.get("allergies", []) if a]
        
        final_shopping_list = []
        seen_product_ids = set()

        for ingredient in ingredients:
            try:
                # 1. Tìm kiếm (Tool này đã gọi Repo có lọc main_category)
                products = self.product_tool.search(ingredient)
                
                if not products or not isinstance(products, list):
                    continue

                valid_products = []
                for p in products:
                    if not isinstance(p, dict):
                        continue
                    if is_excluded_main_category(p.get("main_category") or p.get("category")):
                        continue

                    p_name = p.get("name", "").lower()
                    
                    # 2. Lọc bỏ sản phẩm chứa thành phần dị ứng
                    if any(allergy in p_name for allergy in allergies):
                        continue
                    
                    valid_products.append(p)

                if valid_products:
                    # 3. Ưu tiên sản phẩm có giá tốt nhất (Sử dụng price_final)
                    valid_products.sort(key=lambda x: x.get("price_final", 999999))
                    
                    best_match = None
                    for p in valid_products:
                        # Thống nhất dùng item_no để tránh KeyError ở UI
                        p_id = p.get("item_no")
                        if p_id and p_id not in seen_product_ids:
                            best_match = p
                            seen_product_ids.add(p_id)
                            break
                    
                    if best_match:
                        best_match["raw_ingredient"] = ingredient 
                        final_shopping_list.append(best_match)
                        logger.info(f"✅ Khớp thành công: {ingredient} -> {best_match['name']}")

            except Exception as e:
                logger.error(f"❌ Lỗi khi khớp nguyên liệu {ingredient}: {str(e)}")

        return final_shopping_list