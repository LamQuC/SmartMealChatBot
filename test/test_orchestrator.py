from src.llm.llm_client import LLMClient
from src.agents.orchestrator import AgentOrchestrator

def main():
    llm = LLMClient()
    orchestrator = AgentOrchestrator(llm)
    user_input = "hello"
    result = orchestrator.process_input(user_input)
    print(result)
if __name__ == "__main__":
    main()