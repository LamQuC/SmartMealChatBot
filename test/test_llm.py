from src.llm.llm_client import LLMClient


def main():

    llm = LLMClient()

    response = llm("Hãy liệt kê 3 loại rau phổ biến")

    print(response)


if __name__ == "__main__":
    main()