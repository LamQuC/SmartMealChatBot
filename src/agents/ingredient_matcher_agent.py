import json
from src.core.logger import logger 
from src.tools.product_search_tool import ProductSearchTool

class IngredientMatcherAgent:
    def __init__(self):
        # Tool này kết nối với Vector DB (MongoDB Atlas Search)
        self.product_tool = ProductSearchTool()

    def run(self, ingredients: list, user_profile: dict = None) -> list:
        """
        Nhiệm vụ: Tìm sản phẩm thực tế cho từng nguyên liệu thô CẦN MUA.
        """
        logger.info(f"[IngredientMatcherAgent] Bắt đầu tìm hàng thực tế cho: {ingredients}")
        
        user_profile = user_profile or {}
        allergies = [a.lower().strip() for a in user_profile.get("allergies", []) if a]
        
        final_shopping_list = []
        
        seen_product_ids = set()

        for ingredient in ingredients:
            try:
                # 1. Thực hiện tìm kiếm Semantic Search (Vector)
                products = self.product_tool.search(ingredient)
                
                if not products or not isinstance(products, list):
                    logger.warning(f"Không tìm thấy sản phẩm nào tại WinMart cho: {ingredient}")
                    continue

                valid_products = []
                for p in products:
                    if not isinstance(p, dict): continue
                    
                    p_name = p.get("name", "").lower()
                    
                    # 2. Lọc bỏ sản phẩm chứa thành phần dị ứng
                    if any(allergy in p_name for allergy in allergies):
                        logger.info(f"Loại bỏ SP dị ứng ({p_name}) cho nguyên liệu {ingredient}")
                        continue
                    
                    valid_products.append(p)

                if valid_products:
                    # 3. Ưu tiên sản phẩm có giá tốt nhất
                    valid_products.sort(key=lambda x: x.get("price_final", x.get("price", 999999)))
                    
                    
                    best_match = None
                    for p in valid_products:
                        # Dùng item_no hoặc product_id tùy theo schema của Lâm
                        p_id = p.get("item_no") or p.get("product_id") or p.get("id")
                        if p_id not in seen_product_ids:
                            best_match = p
                            seen_product_ids.add(p_id)
                            break
                    
                    if best_match:
                        best_match["raw_ingredient"] = ingredient 
                        final_shopping_list.append(best_match)

            except Exception as e:
                logger.error(f"Lỗi khi khớp nguyên liệu {ingredient}: {str(e)}")

        return final_shopping_list