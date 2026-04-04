from src.core.logger import logger
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
load_dotenv()

class LLMClient:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def __call__(self, prompt: str, expect_json: bool = True):
        logger.info(f"LLM Prompt: {prompt}")
        try:
            generation_config = {}
            if expect_json:
                generation_config = {"response_mime_type": "application/json"}
            response = self.model.generate_content(prompt, generation_config=generation_config)
            text_out = response.text.strip()
            logger.info(f"LLM Response: {text_out[:200]}...")

            if expect_json:
                clean_text = text_out.replace("```json", "").replace("```", "").strip()
                try:
                    return json.loads(clean_text)
                except Exception:
                    # Fallback nếu JSON không parse được - trả về dict an toàn
                    return {"intent": "general_inquiry", "entities": {}}

            return text_out

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # CRITICAL: Always return valid response structure, never a bare error dict
            if expect_json:
                # Return safe default JSON structure that nodes expect
                return {"intent": "general_inquiry", "entities": {}, "error": f"API Error: {str(e)[:100]}"}
            else:
                # Return user-friendly error message as string
                return "Xin lỗi, hệ thống đang gặp sự cố kỹ thuật. Vui lòng thử lại sau."
    def extract_entities(self, user_input: str, current_info: dict) -> dict:
        prompt = f"""
        Dựa vào câu chat của người dùng và thông tin đã có, hãy trích xuất dữ liệu mới.
        
        THÔNG TIN ĐÃ CÓ:
        - Ngân sách: {current_info.get('budget', 'Chưa có')}
        - Số người: {current_info.get('persons', 'Chưa có')}
        - Sở thích: {current_info.get('preferences', [])}

        USER INPUT: "{user_input}"

        YÊU CẦU:
        1. Trích xuất: 'budget' (Số), 'persons' (Số), 'preferences' (Mảng chuỗi).
        2. Nếu thông tin đã có trong "THÔNG TIN ĐÃ CÓ" và User không thay đổi, hãy giữ nguyên.
        3. Nếu User nói "khoảng 200k", hãy trả về budget là 200000.
        4. Chỉ trả về JSON duy nhất.
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Parse kết quả từ JSON string sang Dictionary
            clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            # Return empty entities on error instead of crashing
            return {}
    def call(self, prompt: str, expect_json: bool = False):
        # alias method for backward compatibility
        return self.__call__(prompt, expect_json=expect_json)
