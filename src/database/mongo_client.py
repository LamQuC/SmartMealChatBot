from pymongo import MongoClient

from src.core.settings import get_settings


def get_mongo_client():
    """Khởi tạo kết nối tới MongoDB dựa trên configs/app.json và biến môi trường."""
    s = get_settings()
    mongo_uri = s.mongo_uri
    db_name = s.mongo_db_name
    client = MongoClient(mongo_uri)
    return client[db_name]

