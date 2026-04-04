from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def get_mongo_client():
    """Khởi tạo kết nối tới MongoDB dựa trên biến môi trường"""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("MONGO_DB_NAME", "smart_meal_db")
    client = MongoClient(mongo_uri)
    return client[db_name]

