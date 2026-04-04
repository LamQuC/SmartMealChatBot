from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["smart_meal_db"]

db.products.create_index("item_no", unique=True)
db.products.create_index("main_category")
db.products.create_index("name")
