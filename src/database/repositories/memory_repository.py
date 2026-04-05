from src.database.mongo_client import get_mongo_client
from datetime import datetime, timedelta

class MemoryRepository:
    def __init__(self):
        self.db = get_mongo_client()
        self.collection = self.db["user_memory"]

    def get_user_memory(self, user_id: str) -> dict:
        """Lấy hồ sơ user từ DB, tự động xử lý session hết hạn 12h"""
        # 1. Thực hiện reset session quá hạn trực tiếp trong DB trước
        twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)
        
        # Tìm xem có session nào hết hạn không
        expired_session = self.collection.find_one({
            "user_id": user_id,
            "current_session.timestamp": {"$lt": twelve_hours_ago}
        })

        if expired_session and expired_session.get("current_session"):
            old_meal = expired_session["current_session"].get("dishes", [])
            self.collection.update_one(
                {"user_id": user_id},
                {
                    "$push": {"recent_meals": {"$each": [old_meal], "$slice": -7}},
                    "$set": {"current_session": None}
                }
            )

        # 2. Bây giờ mới lấy record mới nhất
        record = self.collection.find_one({"user_id": user_id})
        
        if not record:
            return {
                "user_id": user_id,
                "user_profile": {
                    "full_name": None, "budget": 200000, "persons": 2, 
                    "preferences": [], "allergies": [], "pantry_items": ["Nước mắm"]
                },
                "recent_meals": [],
                "current_session": None,
                "short_term_history": [],
            }
        
        record.pop("_id", None)
        return record

    def upsert_user_profile(self, user_id: str, profile_updates: dict):
        """Cập nhật toàn bộ memory data cho user"""
        now = datetime.utcnow()
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {**profile_updates, "updated_at": now}},
            upsert=True
        )

    def update_current_session(self, user_id: str, meal_data: dict):
        """Lưu bữa ăn đang thảo luận (trong vòng 12h)"""
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "current_session": {
                    **meal_data,
                    "timestamp": datetime.utcnow()
                }
            }},
            upsert=True
        )