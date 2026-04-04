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
Bạn là Bộ não điều hướng của hệ thống Trợ lý đi chợ WinMart. Nhiệm vụ của bạn là phân tích câu chat của người dùng để xác định họ muốn làm gì.

### HỒ SƠ NGƯỜI DÙNG HIỆN TẠI
- Tên: {user_profile.get('full_name', 'Khách')}
- Sở thích: {user_profile.get('preferences', [])}
- Dị ứng: {user_profile.get('allergies', [])}

### CÁC LOẠI Ý ĐỊNH (INTENT)
1. `meal_planning`: Khi người dùng muốn lên thực đơn mới, ĐỔI MÓN trong thực đơn hiện tại, hoặc báo đã có sẵn nguyên liệu gì đó (ví dụ: "nhà còn trứng", "đổi món cá thành thịt").
2. `product_search`: Khi người dùng chỉ muốn tìm đích danh một mặt hàng tại WinMart (ví dụ: "tìm giá sữa bột", "bim bim bao nhiêu tiền").
3. `general_inquiry`: Hỏi đáp về sức khỏe, nấu ăn hoặc tán gẫu (ví dụ: "cách nấu canh chua", "tôi bị đau dạ dày ăn gì").

### YÊU CẦU ĐẦU RA (JSON CHUẨN)
{{
  "intent": "tên_intent",
  "entities": {{
    "change_dish": "tên món muốn thay thế nếu có",
    "owned_items": ["danh sách đồ dùng user báo đã có sẵn tại nhà trong câu chat"]
  }}
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