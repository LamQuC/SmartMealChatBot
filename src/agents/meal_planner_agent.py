import json
from src.llm.llm_client import LLMClient
from src.core.logger import logger

class MealPlannerAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, user_input: str, state: dict) -> dict:
        """
        Nhiệm vụ: Lên thực đơn hoặc điều chỉnh thực đơn dựa trên trạng thái 12h.
        """
        profile = state.get('user_profile', {})
        recent = state.get('recent_meals', [])
        current = state.get('current_session')
        
        # Lấy thông tin bổ sung từ IntentAgent (nếu có)
        # Lưu ý: Trong nodes.py, kết quả của IntentAgent cần được gán vào state trước khi gọi Planner
        change_info = state.get('change_dish_info', "") 
        owned_items = state.get('user_owned_ingredients', [])

        # Xây dựng ngữ cảnh Session (Quyết định hành động của AI)
        if current and current.get('dishes'):
            session_context = f"""
### NGỮ CẢNH BỮA ĂN HIỆN TẠI (TRONG 12H)
- User đang thảo luận về thực đơn này: {current.get('dishes')}
- Yêu cầu điều chỉnh: "{user_input}"
- Món cụ thể cần đổi (nếu có): {change_info}
- Đồ mới báo có sẵn tại nhà: {owned_items}
=> HÀNH ĐỘNG: Hãy giữ nguyên các món user không phàn nàn và chỉ thay thế món được yêu cầu.
"""
        else:
            session_context = f"""
### NGỮ CẢNH BỮA ĂN MỚI
- Yêu cầu: "{user_input}"
=> HÀNH ĐỘNG: Hãy tạo một thực đơn 3 món hoàn toàn mới phù hợp với hồ sơ.
"""

        prompt = f"""
### VAI TRÒ
Bạn là Chuyên gia ẩm thực kỹ thuật số của WinMart. Bạn lập thực đơn thông minh, ngon miệng và tiết kiệm.

### HỒ SƠ NGƯỜI DÙNG
- Số người: {profile.get('persons', 2)}
- Ngân sách: {profile.get('budget', 200000)}đ
- Dị ứng: {profile.get('allergies', [])}
- Sở thích: {profile.get('preferences', [])}
- Gia vị sẵn có (Pantry): {profile.get('pantry_items', [])}
- Đã ăn trong 7 bữa gần nhất (NÉ TRÙNG): {recent}

{session_context}

### QUY TẮC LÊN THỰC ĐƠN
1. Thực đơn luôn gồm 3 món: 1 món mặn (protein), 1 món xào/rau, 1 món canh.
2. KHÔNG liệt kê gia vị đã có trong Pantry vào danh sách 'ingredients'.
3. Nếu user báo đã có sẵn nguyên liệu (ví dụ: "có trứng"), bạn vẫn có thể lên món trứng nhưng KHÔNG được đưa "Trứng" vào danh sách 'ingredients' (vì không cần mua).

### ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC JSON)
{{
  "dishes": ["Tên món 1", "Tên món 2", "Tên món 3"],
  "ingredients": ["Nguyên liệu chính 1", "Nguyên liệu chính 2"]
}}

### TRẢ LỜI (CHỈ JSON):
"""

        try:
            raw_response = self.llm.call(prompt)
            # Làm sạch dữ liệu rác từ LLM
            clean_response = raw_response.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean_response)
            
            logger.info(f"[MealPlannerAgent] Thực đơn: {result.get('dishes')}")
            return result

        except Exception as e:
            logger.error(f"Lỗi MealPlanner: {str(e)}")
            # Fallback nếu LLM lỗi hoặc JSON lỗi
            if current and current.get('dishes'):
                return {"dishes": current['dishes'], "ingredients": []}
            return {
                "dishes": ["Thịt lợn luộc", "Rau muống xào tỏi", "Canh rau muống"], 
                "ingredients": ["Thịt ba chỉ", "Rau muống", "Tỏi"]
            }