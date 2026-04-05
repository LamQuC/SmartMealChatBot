# 📑 MongoDB Indexes - Hướng Dẫn

## 📊 Tình Trạng

**File**: `src/database/indexes.py`  
**Status**: ✅ Đã tích hợp vào `scripts/run_etl.py`

---

## 🚀 Cách Chạy Indexes

### **Option 1: Tự Động (Recommended) ✅**
Indexes sẽ tự động chạy khi bạn chạy pipeline chính:

```bash
cd e:\Code\PythonWork\Chat_Bot\SmartMealChatBot
python scripts/run_etl.py
```

**Khi nào chạy**: 
- Lần đầu tiên setup project
- Hàng ngày khi cập nhật dữ liệu

**Pipeline steps**:
1. **B0**: ⚙️ Setup MongoDB indexes (TỰ ĐỘNG) ← NEW
2. **B1**: Crawl dữ liệu từ WinMart
3. **B2**: Gán nhãn category
4. **B3**: Load vào MongoDB
5. **B4**: Build vector embeddings

---

### **Option 2: Chạy Thủ Công**
Nếu bạn chỉ muốn setup indexes mà không crawl data:

```bash
python src/database/indexes.py
```

**Khi nào cần chạy thủ công**:
- Lần đầu setup MongoDB
- Reset indexes
- Troubleshoot database issues

---

## 📋 Indexes Chi Tiết

| Index | Loại | Tác Dụng |
|-------|------|---------|
| **item_no** | UNIQUE | Định danh sản phẩm, tránh trùng lặp |
| **main_category** | Regular | Tìm kiếm theo danh mục (Gia vị, Rau cu, etc.) |
| **name** | Regular | Tìm kiếm theo tên sản phẩm |

---

## ⚡ Tại Sao Cần Indexes?

**Hiệu suất**:
- ❌ Không có index: Query full collection (chậm)
- ✅ Có index: Tra cứu trực tiếp (nhanh 100x)

**Tính toàn vẹn dữ liệu**:
- `item_no` UNIQUE: Đảm bảo không có sản phẩm nào bị trùng

---

## 📊 Status Après Tích Hợp

| Aspect | Trước | Sau |
|--------|-------|-----|
| **Integration** | ❌ Standalone | ✅ Tích hợp run_etl.py |
| **Automation** | ❌ Thủ công | ✅ Tự động + thủ công |
| **Pipeline Step** | ❌ Không có | ✅ B0 (Setup) |
| **Documentation** | ❌ Thiếu | ✅ Đầy đủ |
| **Error Handling** | ❌ None | ✅ Try-catch + logging |

---

## 🔍 Kiểm Tra Indexes Đã Tạo

Để xem các indexes đã tạo:

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["smart_meal_db"]

# Xem tất cả indexes trên products collection
indexes = db.products.list_indexes()
for index in indexes:
    print(f"Index: {index['name']}")
    print(f"  Keys: {index['key']}")
    print(f"  Unique: {index.get('unique', False)}\n")
```

---

## 📝 Changelog

### Update 2025-04-05
- ✅ Tích hợp `setup_mongodb_indexes()` vào `run_etl.py`
- ✅ Thêm documentation vào `indexes.py`
- ✅ Thêm proper logging và error handling
- ✅ Tạo B0 (Setup) step trong pipeline
