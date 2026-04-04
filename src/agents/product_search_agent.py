from src.tools.product_search_tool import ProductSearchTool


class ProductSearchAgent:
    def __init__(self):
        self.tool = ProductSearchTool()

    def run(self, user_input: str, user_info: dict = None):
        results = self.tool.search(user_input)
        
        # Logic lọc tương tự Matcher
        if user_info:
            allergies = [a.lower() for a in user_info.get("allergies", [])]
            results = [
                p for p in results 
                if not any(a in p.get("name", "").lower() for a in allergies)
            ]

        # Trả về kết quả đã lọc kèm theo query gốc
        return {
            "query": user_input,
            "results": results[:5] # Lấy top 5 sản phẩm
        }
    