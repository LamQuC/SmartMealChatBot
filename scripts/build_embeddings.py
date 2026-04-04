from src.database.mongo_client import get_mongo_client
from src.embeddings.embedding_service import EmbeddingService

def main():
    db = get_mongo_client()
    collection = db["products"]
    embedder = EmbeddingService()
    
    
    query = {"embedding": {"$exists": False}}
    new_products = list(collection.find(query))
    
    print(f"Found {len(new_products)} new products needing embeddings.")

    for product in new_products:
        search_text = embedder.build_search_text(product)
        vector = embedder.embed(search_text)
        
        collection.update_one(
            {"_id": product["_id"]},
            {"$set": {
                "search_text": search_text,
                "embedding": vector
            }}
        )
    print("Embedding update completed.")

if __name__ == "__main__":
    main()