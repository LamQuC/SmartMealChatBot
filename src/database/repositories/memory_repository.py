from src.database.mongo_client import get_mongo_client
from datetime import datetime, timedelta

class MemoryRepository:
    def __init__(self):
        self.db = get_mongo_client()
        self.collection = self.db["user_memory"]

    def get_user_memory(self, user_id: str) -> dict:
        record = self.collection.find_one({"user_id": user_id})
        if not record:
            return {
                "user_id": user_id,
                "user_profile": { # Thông tin từ Form UI
                    "full_name": None, "height": None, "weight": None,
                    "budget": 200000, "persons": 2, 
                    "preferences": [], "allergies": [], "pantry_items": ["Muối", "Nước mắm"]
                },
                "recent_meals": [],      # Lịch sử 7 bữa đã CHỐT
                "current_session": None, # Bữa ăn đang gợi ý trong vòng 12h
                "short_term_history": [],
            }
        
        # Logic 12h Cooldown: Kiểm tra nếu session cũ đã quá 12h thì reset
        if record.get("current_session"):
            updated_at = record["current_session"].get("timestamp")
            if updated_at and datetime.utcnow() - updated_at > timedelta(hours=12):
                # Đẩy bữa ăn cũ vào history (giữ tối đa 7)
                old_meal = record["current_session"].get("dishes", [])
                self.collection.update_one(
                    {"user_id": user_id},
                    {
                        "$push": {"recent_meals": {"$each": [old_meal], "$slice": -7}},
                        "$set": {"current_session": None}
                    }
                )
                record["current_session"] = None
        
        record.pop("_id", None)
        return record

    def upsert_user_profile(self, user_id: str, profile_updates: dict):
        """Cập nhật riêng phần Profile từ Form UI"""
        now = datetime.utcnow()
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_profile": profile_updates, "updated_at": now}},
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