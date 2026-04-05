from src.database.repositories.memory_repository import MemoryRepository
from datetime import datetime
# src/core/memory.py

class MemoryService:
    def __init__(self):
        self.repo = MemoryRepository()

    def get(self, user_id: str) -> dict:
        """Lấy toàn bộ hồ sơ người dùng"""
        return self.repo.get_user_memory(user_id) or {}

    def save_full_profile(self, user_id: str, user_info_state: dict):
        """
        Lưu toàn bộ cục user_info từ AgentState xuống DB.
        Đây là hàm quan trọng nhất cho update_memory_node.
        """
        # Tránh ghi đè nếu state rỗng (safety check)
        if not user_info_state:
            return
            
        current = self.get(user_id)
        
        # Merge sâu để đảm bảo không mất các field khác trong DB nếu có
        merged = {**current, **user_info_state}
        
        # Giới hạn recent_meals ngay tại đây cho chắc chắn
        if "recent_meals" in merged:
            merged["recent_meals"] = merged["recent_meals"][-7:]
            
        return self.repo.upsert_user_profile(user_id, merged)

    # --- Các hàm bổ trợ (Dùng khi cần update lẻ tẻ bên ngoài Graph) ---

    def update_personal_info(self, user_id: str, updates: dict):
        # Giữ nguyên logic của bạn nhưng gom vào key 'personal_info' 
        # hoặc map trực tiếp vào root tùy theo cấu trúc state.py của bạn
        current = self.get(user_id)
        new_data = {**current, **updates}
        return self.repo.upsert_user_profile(user_id, new_data)

    def add_recent_meal(self, user_id: str, meal_summary: list, max_len: int = 7):
        current = self.get(user_id)
        recent = list(current.get("recent_meals", []))
        # Thêm vào cuối (hoặc đầu tùy bạn chọn)
        recent.append(meal_summary) 
        recent = recent[-max_len:]
        return self.update_personal_info(user_id, {"recent_meals": recent})

    def reset_short_term(self, user_id: str):
        """Reset short-term history"""
        return self.update_personal_info(user_id, {"short_term_history": []})

    def append_session_turn(self, user_id: str, turn_data: dict):
        """
        Lưu một lượt chat vào session history.
        turn_data: {"user_input": ..., "intent": ..., "response": ..., "timestamp": ...}
        """
        current = self.get(user_id)
        short_term = current.get("short_term_history", [])
        short_term.append({**turn_data, "timestamp": turn_data.get("timestamp", str(datetime.utcnow()))})
        # Giới hạn short_term history để tránh quá tải
        short_term = short_term[-50:]  # Giữ 50 lượt gần nhất
        return self.update_personal_info(user_id, {"short_term_history": short_term})
