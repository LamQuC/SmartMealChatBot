# This is a placeholder implementation of the EmbeddingService.

from sentence_transformers import SentenceTransformer

from src.core.settings import get_settings


class EmbeddingService:
    def __init__(self):
        s = get_settings()
        self.models = SentenceTransformer(s.embedding_model)

    def build_search_text(self, product):
        fields = [
            product.get("name", ""),
            product.get("brand", ""),
            product.get("main_category", ""),
            product.get("category_level_1", ""),
            product.get("category_level_2", ""),
            product.get("category_level_3", ""),
            product.get("category_level_4", ""),
            product.get("category_level_5", ""),
            product.get("short_description", ""),
            product.get("long_description", "")
        ]

        return " | ".join(str(x).strip() for x in fields if x)

    def embed(self, text: str) -> list:
        return self.models.encode(text).tolist()
        