from src.llm.llm_client import LLMClient
from src.agents.orchestrator import AgentOrchestrator


def main():

    llm = LLMClient()

    orchestrator = AgentOrchestrator(llm)

    result = orchestrator.run("gợi ý bữa tối đơn giản")

    print(result)


if __name__ == "__main__":
    main()