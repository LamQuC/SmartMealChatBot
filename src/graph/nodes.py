import json
from datetime import datetime
from src.core.logger import logger
from langgraph.types import Command
from src.graph.state import AgentState
from src.agents.intent_agent import IntentAgent
from src.agents.meal_planner_agent import MealPlannerAgent
from src.agents.ingredient_matcher_agent import IngredientMatcherAgent
from src.agents.general_agent import GeneralAgent
from src.llm.llm_client import LLMClient
from src.database.repositories.memory_repository import MemoryRepository

llm = LLMClient()
memory_repo = MemoryRepository()

def intent_node(state: AgentState):
    """
    Node điều hướng: 
    1. Kiểm tra 12h Cooldown để xác định Session hiện tại.
    2. Nhận diện Intent (Meal Planning, Change Dish, General).
    """
    user_id = state.get("user_id", "lam_ai_eng")
    user_input = state["user_input"]
    
    # Lấy dữ liệu từ DB (Đã có logic 12h bên trong Repository)
    db_memory = memory_repo.get_user_memory(user_id)
    user_profile = db_memory.get("user_profile", {})
    current_session = db_memory.get("current_session")
    recent_meals = db_memory.get("recent_meals", [])

    intent_agent = IntentAgent(llm)
    result = intent_agent.run(user_input, user_profile)
    detected_intent = result.get("intent", "general_inquiry")

    # Nếu đang trong 12h và user muốn đổi món, ta giữ nguyên Context cũ
    return {
        "user_profile": user_profile,
        "recent_meals": recent_meals,
        "current_session": current_session,
        "current_intent": detected_intent,
        "messages": [("system", f"Intent: {detected_intent} | Session Active: {current_session is not None}")],
        "meal_plan": current_session.get("dishes", []) if current_session else [],
        "matched_products": [],
        "final_response": ""
    }

def meal_planner_node(state: AgentState):
    """Lên thực đơn mới hoặc điều chỉnh thực đơn hiện tại"""
    try:
        agent = MealPlannerAgent(llm)
        # Truyền cả state để Agent biết Profile và Current Session (12h logic)
        result = agent.run(state["user_input"], state) 
        
        return {
            "meal_plan": result.get("dishes", []),
            "raw_ingredients": result.get("ingredients", []),
            "final_response": ""
        }
    except Exception as e:
        logger.error(f"Lỗi Meal Planner: {e}")
        return {"final_response": "Xin lỗi, mình gặp trục trặc khi lên món. Thử lại nhé!"}

def ingredient_matching_node(state: AgentState):
    """Kết nối thực đơn với hàng WinMart + Lọc đồ có sẵn/Gia vị"""
    raw_ingredients = state.get("raw_ingredients", [])
    profile = state.get("user_profile", {})
    
    # Danh sách đồ ĐÃ CÓ (Gia vị trong Pantry + Đồ user báo sẵn)
    pantry_items = [i.lower() for i in profile.get("pantry_items", [])]
    owned_items = [i.lower() for i in state.get("user_owned_ingredients", [])]
    all_owned = pantry_items + owned_items

    # Chỉ tìm hàng cho những thứ KHÔNG có trong bếp
    ingredients_to_buy = []
    for ing in raw_ingredients:
        if any(owned in ing.lower() for owned in all_owned):
            logger.info(f"Đã có sẵn, không tìm hàng: {ing}")
            continue
        ingredients_to_buy.append(ing)

    agent = IngredientMatcherAgent()
    matched_list = agent.run(ingredients_to_buy, profile)

    return {
        "matched_products": matched_list,
        "messages": [("system", f"Đã khớp {len(matched_list)} sản phẩm WinMart.")],
    }

def budget_optimizer_node(state: AgentState):
    """Kiểm tra ngân sách và tổng hợp phản hồi"""
    products = state.get("matched_products", [])
    budget = state.get("user_profile", {}).get("budget", 0)
    
    total_cost = sum(int(p.get('price_final', p.get('price', 0))) for p in products)
    
    # Lưu bữa ăn này vào Session 12h của DB
    user_id = state.get("user_id", "lam_ai_eng")
    memory_repo.update_current_session(user_id, {
        "dishes": state.get("meal_plan", []),
        "total_cost": total_cost
    })

    if total_cost > budget:
        response = f"Tổng chi phí {total_cost:,}đ vượt ngân sách {budget:,}đ của anh một chút. Anh có muốn đổi món nào rẻ hơn không?"
    else:
        response = f"Thực đơn đã sẵn sàng! Tổng cộng: {total_cost:,}đ (Dưới ngân sách {budget:,}đ)."

    return {"total_cost": total_cost, "final_response": response}

def general_inquiry_node(state: AgentState):
    """Xử lý chat tổng quát/tư vấn"""
    agent = GeneralAgent(llm)
    response = agent.run(state["user_input"], state.get("user_profile", {}))
    
    return Command(
        update={"final_response": str(response)},
        goto="final_response_node"
    )

def final_response_node(state: AgentState):
    """Format kết quả cuối cùng để hiển thị lên UI"""
    res = state.get("final_response", "")
    products = state.get("matched_products", [])
    
    if products:
        res += "\n\n**🛒 Danh sách cần mua tại WinMart:**\n"
        for p in products:
            res += f"- {p.get('name')}: {int(p.get('price_final', 0)):,}đ\n"
            
    return {"messages": [("assistant", res)]}