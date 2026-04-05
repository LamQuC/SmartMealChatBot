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
1. Thực đơn luôn gồm 3 món: 1 món mặn (protein), 1 món xào/rau, 1 món canh (tuỳ số người nhưng đủ 3 loại).
2. Với TỪNG món: viết **công thức các bước nấu** rõ ràng (ước lượng theo số người trong hồ sơ).
3. **Ngân sách & giỏ hàng chỉ tính nguyên liệu chính** (thịt, cá, rau, củ, đậu, trứng...). 
   **KHÔNG** tính tiền mua gia vị (mắm, muối, đường, dầu, nước mắm...).
4. Gia vị: mỗi món có trường `spices_note` — mô tả gia vị cần có và lượng ước chừng để đúng với công thức (ghi chú, không tính vào giỏ tiền).
5. 'ingredients': CHỈ nguyên liệu chính cần **MUA** tại siêu thị (không gồm gia vị; không gồm thứ user đã có sẵn / đã nêu trong Pantry hoặc owned_items).

### ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC JSON)
{{
  "dishes": [
    {{
      "name": "Tên món",
      "recipe": "Bước 1: ...\\nBước 2: ...",
      "spices_note": "Gia vị cần có: nước mắm, đường, tiêu, dầu ăn (ước lượng cho X người)"
    }}
  ],
  "ingredients": ["Chỉ nguyên liệu chính cần mua 1", "..."],
  "spices": []
}}
(Lưu ý: giữ mảng "spices" rỗng [] hoặc bỏ qua; ưu tiên spices_note trong từng món.)

### TRẢ LỜI (CHỈ JSON):
"""

        try:
            raw_response = self.llm.call(prompt)
            # Làm sạch dữ liệu rác từ LLM
            clean_response = raw_response.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean_response)
            if "spices" not in result:
                result["spices"] = []
            logger.info(f"[MealPlannerAgent] Thực đơn: {result.get('dishes')}")
            return result

        except Exception as e:
            logger.error(f"Lỗi MealPlanner: {str(e)}")
            # Fallback nếu LLM lỗi hoặc JSON lỗi
            if current and current.get("dishes"):
                return {"dishes": current["dishes"], "ingredients": [], "spices": []}
            return {
                "dishes": [
                    {
                        "name": "Thịt kho tàu",
                        "recipe": "Bước 1: Ướp thịt với nước mắm, đường. Bước 2: Kho nhỏ lửa đến khi mềm.",
                        "spices_note": "Gia vị cần có: nước mắm, đường, tiêu, dầu ăn (không tính vào ngân sách mua sắm).",
                    },
                    {
                        "name": "Rau muống xào tỏi",
                        "recipe": "Bước 1: Phi tỏi. Bước 2: Xào rau trên lửa lớn.",
                        "spices_note": "Gia vị: tỏi, nước mắm, dầu ăn.",
                    },
                    {
                        "name": "Canh rau muống",
                        "recipe": "Đun sôi nước, cho rau vào, nêm vừa ăn.",
                        "spices_note": "Gia vị: muối, hạt nêm (nếu có).",
                    },
                ],
                "ingredients": ["Thịt ba chỉ", "Rau muống"],
                "spices": [],
            }