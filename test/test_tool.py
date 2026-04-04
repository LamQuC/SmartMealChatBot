from src.tools.product_search_tool import ProductSearchTool

def main():

    tool = ProductSearchTool()

    results = tool.search("socola")

    for r in results:
        print(r)


if __name__ == "__main__":
    main()