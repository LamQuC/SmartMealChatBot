from src.llm.llm_client import LLMClient
from src.agents.base_agent import BaseAgent
class GeneralAgent(BaseAgent):
    def run(self, user_input: str, user_info: dict = None):
        # Lọc các thông tin liên quan đến sức khỏe/mua sắm để làm context
        context = {k: v for k, v in (user_info or {}).items() if v and k in ["budget", "preferences", "allergies"]}
        history = user_info.get("history", [])
        prompt = f"""
ROLE: Bạn là chuyên gia tư vấn mua sắm WinMart & Dinh dưỡng.
hãy dựa vào lịch sử chat và context để trả lời câu hỏi của người dùng.
HISTORY: {history}
CONTEXT: {context}

TASK: Trả lời yêu cầu của người dùng về sản phẩm, sức khỏe hoặc nấu ăn. 
LƯU Ý: 
- Nếu user muốn xem danh mục / hàng hoá / giá sản phẩm tại cửa hàng: nhắc họ dùng nút sidebar **"Xem hàng hoá WinMart"** (trang chỉ để xem sản phẩm, có dropdown danh mục).
- Nếu câu hỏi không liên quan đến WinMart/Nấu ăn/Sức khỏe, hãy từ chối lịch sự.
- Câu trả lời ngắn gọn, tập trung vào giải pháp.

USER REQUEST: {user_input}
OUTPUT: Plain text.
"""
        return self.llm(prompt)