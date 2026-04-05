from src.retrieval.vector_search import VectorSearch
from src.core.logger import logger

class ProductSearchTool:
    def __init__(self):
        # Khởi tạo search engine từ Vector DB (Milvus/MongoDB Vector Search...)
        self.vector_search = VectorSearch()

    def search(self, query: str, top_k: int = 5):
        """
        Thực hiện tìm kiếm vector dựa trên truy vấn người dùng.
        Trả về danh sách sản phẩm đã được format chuẩn.
        """
        try:
            # results từ vector_search phải là một list các dict từ MongoDB
            results = self.vector_search.search(query, top_k)
            
            if not results:
                return []

            formatted = []
            for r in results:
                # Kiểm tra r có phải dict không để tránh lỗi 'str' object has no attribute 'get'
                if not isinstance(r, dict):
                    continue

                img = r.get("thumbnail")
                if not img and r.get("image_url"):
                    iu = r.get("image_url")
                    img = iu[0] if isinstance(iu, list) and iu else iu
                formatted.append(
                    {
                        "name": r.get("name", "Không tên"),
                        "price_final": r.get("price_final", 0),
                        "main_category": r.get("main_category", "Chưa phân loại"),
                        "category": r.get("main_category", "Chưa phân loại"),
                        "category_level_5": r.get("category_level_5"),
                        "description": r.get("short_description", ""),
                        "brand": r.get("brand", "N/A"),
                        "thumbnail": img,
                        "image_url": r.get("image_url"),
                        "item_no": r.get("item_no"),
                    }
                )
            
            return formatted

        except Exception as e:
            logger.error(f"Lỗi trong ProductSearchTool khi tìm kiếm '{query}': {e}")
            return []