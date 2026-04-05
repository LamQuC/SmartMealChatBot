import numpy as np
from src.embeddings.embedding_service import EmbeddingService
from src.database.mongo_client import get_mongo_client
from src.core.logger import logger
from src.core.catalog_constants import is_excluded_main_category

class VectorSearch:
    def __init__(self):
        self.embedder = EmbeddingService()
        self.db = get_mongo_client()
        self.collection = self.db["products"]

    def search(self, query: str, top_k: int = 5):
        """
        Tìm kiếm sản phẩm bằng Vector Similarity sử dụng Numpy để tăng tốc.
        """
        try:
            # 1. Chuyển query sang vector
            query_vector = np.array(self.embedder.embed(query))
            
            # 2. Lấy tất cả sản phẩm có embedding từ DB
            # Lưu ý: Với quy mô vừa phải, lấy về RAM xử lý bằng Numpy sẽ nhanh hơn loop từng cái
            cursor = self.collection.find(
                {"embedding": {"$exists": True}},
                {
                    "name": 1,
                    "price_final": 1,
                    "main_category": 1,
                    "category_level_5": 1,
                    "thumbnail": 1,
                    "images": 1,
                    "image_url": 1,
                    "brand": 1,
                    "item_no": 1,
                    "embedding": 1,
                },
            )
            
            products = [p for p in cursor if not is_excluded_main_category(p.get("main_category"))]
            if not products:
                return []

            # 3. Trích xuất ma trận embedding
            # Chuyển list các list thành ma trận Numpy (N x Dimension)
            product_vectors = np.array([p["embedding"] for p in products])
            
            # 4. Tính Cosine Similarity bằng Vectorization (Cực nhanh trên CPU)
            # Công thức: (A . B) / (||A|| * ||B||)
            dot_product = np.dot(product_vectors, query_vector)
            matrix_norms = np.linalg.norm(product_vectors, axis=1)
            query_norm = np.linalg.norm(query_vector)
            
            # Tránh chia cho 0
            similarities = dot_product / (matrix_norms * query_norm + 1e-9)

            # 5. Lấy top K index có độ tương đồng cao nhất
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                product = products[idx]
                # Xóa embedding khỏi kết quả trả về để giảm tải memory/network
                product.pop("embedding", None)
                results.append(product)
                
            return results

        except Exception as e:
            logger.error(f"Lỗi Vector Search cho query '{query}': {e}")
            return []