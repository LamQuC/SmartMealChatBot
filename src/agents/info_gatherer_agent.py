# from src.llm.llm_client import LLMClient
# from src.graph.state import UserInfo

# class InfoGathererAgent:
#     def __init__(self, llm_client: LLMClient):
#         self.llm = llm_client

#     def run(self, user_info: UserInfo) -> str:
#         """
#         Nhiệm vụ: Đặt câu hỏi khéo léo cho thông tin còn thiếu.
#         Trả về: Văn bản câu hỏi (String).
#         """
#         missing_fields = []
#         if not user_info.get("budget"):
#             missing_fields.append("ngân sách dự kiến")
#         if not user_info.get("persons"):
#             missing_fields.append("số người ăn")

#         if not missing_fields:
#             return "Em đã sẵn sàng, anh/chị muốn ăn gì hôm nay?"

#         # Ưu tiên hỏi cái quan trọng nhất đầu tiên (Ngân sách)
#         field_to_ask = missing_fields[0]
        
#         prompt = f"""
# ### VAI TRÒ
# Bạn là một trợ lý đi chợ WinMart thân thiện và tinh tế.

# ### NHIỆM VỤ
# Dựa vào hồ sơ người dùng, em thấy đang thiếu thông tin về: **{field_to_ask}**.
# Hãy đặt một câu hỏi ngắn gọn, lịch sự, và 'duyên' nhất có thể để xin thông tin này từ người dùng. Tránh hỏi dồn dập nhiều thứ cùng lúc.

# ### OUTPUT (CHỈ TRẢ VỀ CÂU HỎI TRỰC TIẾP, không giải thích)
# """
#         # Với Agent này, ta chỉ cần Gemini trả về văn bản tự nhiên
#         response = self.llm.call(prompt)
#         return response.strip()