import json
from src.core.logger import logger
from src.llm.llm_client import LLMClient

class IntentAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, user_input: str, user_profile: dict) -> dict:
        """
        Nhiệm vụ: Phân loại ý định người dùng.
        Đầu ra JSON: 
        {
            "intent": "meal_planning" | "general_inquiry" | "product_search",
            "entities": {"change_dish": "tên món cần đổi", "owned_items": ["món đã có"]}
        }
        """
        
        # System Prompt định nghĩa các tình huống cụ thể cho luồng 12h
        prompt = f"""
        ### VAI TRÒ
        Bạn là Bộ não điều hướng (Intent Classifier) của hệ thống Trợ lý WinMart. 
        Nhiệm vụ: Phân tích câu chat để xác định chính xác Ý ĐỊNH của người dùng.

        ### CÁC LOẠI Ý ĐỊNH (INTENT) - QUAN TRỌNG:
        1. `meal_planning`: 
        - Lên thực đơn mới (Ví dụ: "Ăn gì bây giờ?", "Gợi ý 3 món 200k").
        - Đổi món (Ví dụ: "Đổi thịt thành cá", "Không ăn rau muống nữa").
        - Báo đồ có sẵn (Ví dụ: "Nhà còn trứng", "Có sẵn nước mắm rồi").
        2. `product_browsing`: 
        - Khi người dùng muốn xem danh sách, danh mục, hoặc hỏi WinMart có bán gì không.
        - Ví dụ: "Xem danh mục bánh kẹo", "WinMart có bán thịt heo không?", "Check giá sữa".
        3. `general_inquiry`: 
        - Hỏi đáp sức khỏe, mẹo nấu ăn, dinh dưỡng hoặc tán gẫu.
        - Ví dụ: "Nấu canh chua thế nào?", "Bị đau dạ dày nên ăn gì?", "Chào bạn".

        ### YÊU CẦU ĐẦU RA (JSON CHUẨN)
        {{
        "intent": "meal_planning" | "product_browsing" | "general_inquiry",
        "entities": {{
            "change_dish": "tên món muốn thay thế (nếu có)",
            "owned_items": ["danh sách nguyên liệu user báo đã có sẵn trong câu chat này"],
            "search_keyword": "từ khóa sản phẩm nếu user hỏi đích danh (ví dụ: 'sữa bột')"
        }},
        "reasoning": "Giải thích ngắn gọn lý do chọn intent này"
        }}

        ### USER INPUT
        "{user_input}"

        ### OUTPUT (CHỈ TRẢ VỀ JSON):
        """
        try:
            raw_response = self.llm.call(prompt)
            # Làm sạch response để parse JSON
            clean_json = raw_response.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean_json)
            
            logger.info(f"[IntentAgent] Detected: {result.get('intent')} | Entities: {result.get('entities')}")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi phân loại Intent: {e}")
            # Fallback an toàn
            return {
                "intent": "general_inquiry",
                "entities": {"change_dish": None, "owned_items": []}
            }