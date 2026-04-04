from src.retrieval.vector_search import VectorSearch

def main():
    searcher = VectorSearch()
    results = searcher.search("socola ferrero")

    for r in results:
        print(r["name"], r["price_final"])

if __name__ == "__main__":
    main()