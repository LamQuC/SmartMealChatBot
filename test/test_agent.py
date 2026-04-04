from src.llm.llm_client import LLMClient
from src.agents.intent_agent import IntentAgent


def main():
    llm = LLMClient()
    agent = IntentAgent(llm)
    intent = agent.run("tìm socola ferrero")
    print(intent)
if __name__ == "__main__":
    main()
    