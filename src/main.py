import argparse
import json
from src.llm.llm_client import LLMClient
from src.agents.orchestrator import AgentOrchestrator
from src.core.logger import logger

def interactive_mode(orchestrator, user_id="default_user"):
    logger.info("Entering interactive mode. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                logger.info("Exiting interactive mode.")
                break
            if not user_input:
                continue
            response = orchestrator.run(user_input, user_id)
            print("Response:")
            print(json.dumps(response, ensure_ascii=False, indent=2))
        except KeyboardInterrupt:
            logger.info("Interrupted by user. Bye.")
            break


def main():
    parser = argparse.ArgumentParser(description="SmartMealChatBot command line interface")
    parser.add_argument("--question", "-q", type=str, default=None, help="Ask a question directly and exit")
    parser.add_argument("--user-id", type=str, default="default_user", help="User identifier for memory context")
    args = parser.parse_args()

    llm = LLMClient()
    orchestrator = AgentOrchestrator(llm)

    if args.question:
        result = orchestrator.run(args.question, args.user_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    interactive_mode(orchestrator, args.user_id)


if __name__ == "__main__":
    main()
