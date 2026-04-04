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
        Đầu vào: 
            - ingredients: List các nguyên liệu ĐÃ LỌC bỏ đồ có sẵn.
            - user_profile: Thông tin dị ứng để loại bỏ sản phẩm không phù hợp.
        """
        logger.info(f"[IngredientMatcherAgent] Bắt đầu tìm hàng thực tế cho: {ingredients}")
        
        user_profile = user_profile or {}
        # Chuẩn hóa danh sách dị ứng để so khớp
        allergies = [a.lower().strip() for a in user_profile.get("allergies", []) if a]
        
        final_shopping_list = []

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
                    # 3. Ưu tiên sản phẩm có giá tốt nhất (price_final)
                    valid_products.sort(key=lambda x: x.get("price_final", x.get("price", 999999)))
                    
                    # 4. Lấy 1 kết quả tốt nhất để đưa vào giỏ hàng
                    best_match = valid_products[0]
                    best_match["raw_ingredient"] = ingredient # Lưu lại tag để check đối chiếu
                    final_shopping_list.append(best_match)

            except Exception as e:
                logger.error(f"Lỗi khi khớp nguyên liệu {ingredient}: {str(e)}")

        return final_shopping_list