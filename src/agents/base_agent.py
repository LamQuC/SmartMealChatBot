from src.llm.llm_client import LLMClient

class BaseAgent:
    def __init__(self, llm: LLMClient):
        """
        Khởi tạo Agent với một instance của LLMClient để dùng chung cấu hình.
        """
        self.llm = llm

    def format_prompt(self, user_input: str, user_info: dict) -> str:
        """
        Hàm hỗ trợ để các subclass format string prompt một cách gọn gàng.
        """
        raise NotImplementedError("Subclasses must implement format_prompt")

    def run(self, user_input: str, user_info: dict = None):
        """
        Phương thức thực thi chính.
        user_info: Dữ liệu từ AgentState['user_info'] bao gồm cả profile và recent_meals.
        """
        if user_info is None:
            user_info = {}
            
        prompt = self.format_prompt(user_input, user_info)
        # Mặc định các Agent trong luồng Daily sẽ trả về JSON để Node xử lý
        return self.llm(prompt, expect_json=True)