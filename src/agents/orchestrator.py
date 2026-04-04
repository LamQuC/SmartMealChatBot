from src.agents.intent_agent import IntentAgent
from src.agents.general_agent import GeneralAgent
from src.agents.product_search_agent import ProductSearchAgent
from src.core.logger import logger
from src.agents.meal_planner_agent import MealPlannerAgent
from src.agents.ingredient_matcher_agent import IngredientMatcherAgent
from src.core.memory import MemoryService

class AgentOrchestrator:

    def __init__(self, llm):
        self.intent_agent = IntentAgent(llm)
        self.general_agent = GeneralAgent(llm)
        self.meal_agent = MealPlannerAgent(llm)
        self.product_search_agent = ProductSearchAgent()
        self.matcher_agent = IngredientMatcherAgent()
        self.memory_service = MemoryService()

    def run(self, user_input, user_id="default_user"):
        logger.info(f"[Orchestrator] Received user input: {user_input}")

        user_memory = self.memory_service.get(user_id)
        intent = self.intent_agent.run(user_input, user_memory)
        logger.info(f"[Orchestrator] Intent detected: {intent}")

        response = None
        if intent == "product_search":
            response = self.handle_product_search(user_input, user_memory)

        elif intent == "meal_planning":
            response = self.handle_meal_planning(user_input, user_memory)

        elif intent == "shopping_list_creation":
            response = self.handle_shopping_list(user_input, user_memory)

        elif intent == "general_inquiry":
            response = self.handle_general_inquiry(user_input, user_memory)

        else:
            response = {"error": "Unknown intent"}

        # persist conversation turn
        self.memory_service.append_session_turn(user_id, {
            "user_input": user_input,
            "intent": intent,
            "response": response,
            "timestamp": str(__import__("datetime").datetime.utcnow()),
        })

        return response

    def handle_product_search(self, user_input, user_memory):
        logger.info(f"[Orchestrator] Handling product search for input: {user_input}")
        return self.product_search_agent.run(user_input, user_memory)

    def handle_meal_planning(self, user_input, user_memory):
        logger.info("Routing to MealPlannerAgent")
        meal_output = self.meal_agent.run(user_input, user_memory)

        # optionally: match ingredients to products
        matched = self.matcher_agent.run(meal_output.get("ingredients", []), user_memory)
        return {**meal_output, **{"matched_products": matched}}

    def handle_shopping_list(self, user_input, user_memory):
        logger.info(f"[Orchestrator] Handling shopping list creation for input: {user_input}")
        return {"intent": "shopping_list_creation", "input": user_input}

    def handle_general_inquiry(self, user_input, user_memory):
        logger.info(f"[Orchestrator] Handling general inquiry for input: {user_input}")
        return self.general_agent.run(user_input, user_memory)

        logger.info(f"[Orchestrator] Received user input: {user_input}")
        intent = self.intent_agent.run(user_input)
        logger.info(f"[Orchestrator] Intent detected: {intent}")
        if intent == "product_search":
            return self.handle_product_search(user_input)

        elif intent == "meal_planning":
            return self.handle_meal_planning(user_input)

        elif intent == "shopping_list_creation":
            return self.handle_shopping_list(user_input)

        elif intent == "general_inquiry":
            return self.handle_general_inquiry(user_input)

        else:
            return {"error": "Unknown intent"}

    # Handlers for each intent
    def handle_product_search(self, user_input):
        logger.info(f"[Orchestrator] Handling product search for input: {user_input}")
        return self.product_search_agent.run(user_input)
    
    # Return the input for meal planning and shopping list. In a real implementation, you would call the respective agents/tools.
    def handle_meal_planning(self, user_input):

        logger.info("Routing to MealPlannerAgent")

        return self.meal_agent.run(user_input)

    # Return the input for meal planning and shopping list. In a real implementation, you would call the respective agents/tools.
    def handle_shopping_list(self, user_input):
        logger.info(f"[Orchestrator] Handling shopping list creation for input: {user_input}")
        return {"intent": "shopping_list_creation", "input": user_input}

    # Use the GeneralAgent to provide a response.
    def handle_general_inquiry(self, user_input):
        logger.info(f"[Orchestrator] Handling general inquiry for input: {user_input}")
        return self.general_agent.run(user_input)
    
    