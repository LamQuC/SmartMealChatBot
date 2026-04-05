from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.graph.state import AgentState

# Import các node đã refactor
from src.graph.nodes import (
    intent_node,
    meal_planner_node,
    ingredient_matching_node,
    budget_optimizer_node,
    general_inquiry_node,
    final_response_node
    # Tạm thời bỏ info_gatherer_node vì mình đã dùng FORM UI để lấy info rồi
)

class GraphWorker:
    def __init__(self):
        # 1. Khởi tạo Graph với State mới
        workflow = StateGraph(AgentState)

        # 2. Thêm Nodes
        workflow.add_node("intent_node", intent_node)
        workflow.add_node("meal_planner_node", meal_planner_node)
        workflow.add_node("general_inquiry_node", general_inquiry_node)
        workflow.add_node("ingredient_matching_node", ingredient_matching_node)
        workflow.add_node("budget_optimizer_node", budget_optimizer_node)
        workflow.add_node("final_response_node", final_response_node)

        # 3. Entry Point
        workflow.set_entry_point("intent_node")

        # 4. Điều hướng có điều kiện
        # Chú ý: 'get_more_info' giờ ít dùng vì đã có Form, nhưng có thể giữ làm fallback
        workflow.add_conditional_edges(
            "intent_node",
            lambda state: state["current_intent"],
            {
                "meal_planning": "meal_planner_node",
                "general_inquiry": "general_inquiry_node",
                "product_search": "meal_planner_node", # Có thể dẫn về planner để tư vấn món
            }
        )

        # Luồng thực đơn: Planner -> Matcher (Lọc đồ có sẵn) -> Budget (Lưu session 12h)
        workflow.add_edge("meal_planner_node", "ingredient_matching_node")
        workflow.add_edge("ingredient_matching_node", "budget_optimizer_node")
        workflow.add_edge("budget_optimizer_node", "final_response_node")

        # Luồng hỏi đáp
        workflow.add_edge("general_inquiry_node", "final_response_node")

        # Kết thúc
        workflow.add_edge("final_response_node", END)

        # 5. Compile
        self.checkpointer = MemorySaver()
        self.app = workflow.compile(checkpointer=self.checkpointer)

    def run(self, user_id: str, user_input: str, user_profile_from_ui: dict = None) -> dict:
        """
        user_profile_from_ui: Đây là dữ liệu lấy trực tiếp từ Form Streamlit của Lam
        """
        config = {"configurable": {"thread_id": user_id}}
        
        # Khởi tạo state khớp với src/graph/state.py mới - TẤT CẢ các fields cần thiết
        initial_state = {
            "user_id": user_id,
            "user_input": user_input,
            "messages": [],
            "user_profile": user_profile_from_ui or {}, # Ưu tiên profile mới nhất từ UI
            "recent_meals": [],  # Sẽ được populate từ intent_node
            "current_session": None,  # Sẽ check 12h logic trong intent_node
            "user_owned_ingredients": [], # Sẽ được populate từ IntentAgent entities
            "change_dish_info": "",  # Sẽ được populate từ IntentAgent entities
            "current_intent": "general_inquiry",  # Default, sẽ được update từ intent_node
            "meal_plan": [],
            "raw_ingredients": [],
            "matched_products": [],
            "total_cost": 0.0,
            "final_response": "",
            "optimization_log": []
        }
        
        return self.app.invoke(initial_state, config=config)