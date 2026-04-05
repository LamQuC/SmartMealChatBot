import json
from datetime import datetime
from src.core.logger import logger
from langgraph.types import Command
from langgraph.graph import END
from src.graph.state import AgentState
from src.agents.intent_agent import IntentAgent
from src.agents.meal_planner_agent import MealPlannerAgent
from src.agents.ingredient_matcher_agent import IngredientMatcherAgent
from src.agents.general_agent import GeneralAgent
from src.llm.llm_client import LLMClient
from src.database.repositories.memory_repository import MemoryRepository
from src.database.repositories.product_repository import ProductRepository
from src.database.mongo_client import get_mongo_client

# Khởi tạo repo dùng chung
repo = ProductRepository(get_mongo_client())
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
    # Truyền full context để agent hiểu context 12h
    result = intent_agent.run(user_input, user_profile)
    detected_intent = result.get("intent", "general_inquiry")
    entities = result.get("entities", {})

    # Trích xuất danh sách đồ sẵn có từ intent
    owned_items = entities.get("owned_items", [])
    change_dish = entities.get("change_dish", None)

    # Nếu đang trong 12h và user muốn đổi món, ta giữ nguyên Context cũ
    return {
        "user_id": user_id,
        "user_profile": user_profile,
        "recent_meals": recent_meals,
        "current_session": current_session,
        "current_intent": detected_intent,
        "user_owned_ingredients": owned_items,
        "change_dish_info": change_dish or "",
        "messages": [("system", f"Intent: {detected_intent} | Session Active: {current_session is not None}")],
        "meal_plan": current_session.get("dishes", []) if current_session else [],
        "matched_products": [],
        "total_cost": 0.0,
        "final_response": "",
        "optimization_log": [],
        "raw_ingredients": []
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
            "final_response": "",
            "matched_products": [],
            "total_cost": 0.0,
            "optimization_log": []
        }
    except Exception as e:
        logger.error(f"Lỗi Meal Planner: {e}")
        return {
            "final_response": "Xin lỗi, mình gặp trục trặc khi lên món. Thử lại nhé!",
            "meal_plan": [],
            "raw_ingredients": [],
            "matched_products": [],
            "total_cost": 0.0,
            "optimization_log": []
        }

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
        "total_cost": 0.0,
        "optimization_log": []
    }

def budget_optimizer_node(state: AgentState):
    """
    Thuật toán Tối ưu Ngân sách:
    Sử dụng chiến lược thay thế sản phẩm đắt nhất bằng phương án rẻ hơn cùng Category.
    """
    products = state.get("matched_products", [])
    budget = state.get("user_profile", {}).get("budget", 0)
    user_id = state.get("user_id", "lam_ai_eng")
    
    def calculate_total(prod_list):
        return sum(int(p.get('price_final', 0)) for p in prod_list)

    total_cost = calculate_total(products)
    optimization_log = []

    # --- THUẬT TOÁN TỐI ƯU ---
    if total_cost > budget:
        # 1. Sắp xếp các sản phẩm đã chọn theo giá giảm dần (thằng nào đắt xử trước)
        sorted_products = sorted(products, key=lambda x: x.get('price_final', 0), reverse=True)
        optimized_products = sorted_products.copy()

        for i, p in enumerate(sorted_products):
            if calculate_total(optimized_products) <= budget:
                break
            
            # 2. Tìm hàng thay thế rẻ hơn cùng loại (category_level_5)
            alternative = repo.find_cheaper_alternative(
                p.get("category_level_5"), 
                p.get("price_final")
            )
            
            if alternative:
                optimization_log.append(f"Thay {p['name']} -> {alternative['name']}")
                optimized_products[i] = alternative # Thay thế bằng món rẻ hơn
        
        products = optimized_products
        total_cost = calculate_total(products)

    # --- KẾT QUẢ ---
    # Cập nhật Session 12h
    memory_repo.update_current_session(user_id, {
        "dishes": state.get("meal_plan", []),
        "total_cost": total_cost,
        "products": products
    })

    if total_cost > budget:
        status = "vẫn vượt ngân sách (đã cố gắng tối ưu hết mức)"
    else:
        status = "đã được tối ưu về dưới mức ngân sách"
        if optimization_log:
            status += f" (Đã thay thế {len(optimization_log)} món đắt tiền)"

    response = f"Thực đơn {status}. Tổng chi phí dự kiến: {total_cost:,}đ / Ngân sách: {budget:,}đ."
    
    return {
        "matched_products": products, 
        "total_cost": total_cost, 
        "final_response": response,
        "optimization_log": optimization_log 
    }

def general_inquiry_node(state: AgentState):
    """Xử lý chat tổng quát/tư vấn"""
    agent = GeneralAgent(llm)
    response = agent.run(state["user_input"], state.get("user_profile", {}))
    
    return {
        "final_response": str(response),
        "messages": [("assistant", str(response))],
        "matched_products": [],
        "total_cost": 0.0,
        "optimization_log": []
    }

def final_response_node(state: AgentState):
    """Node cuối cùng: Format và trả lời cho user"""
    res = state.get("final_response", "")
    products = state.get("matched_products", [])
    logs = state.get("optimization_log", [])
    
    # 1. Thêm log tối ưu để user biết AI đã giúp họ tiết kiệm tiền
    if logs:
        res += "\n\n**💡 Tối ưu ngân sách:**\n"
        for log in logs:
            res += f"- {log}\n"
    
    # 2. Hiển thị danh sách hàng WinMart
    if products:
        res += "\n\n**🛒 Giỏ hàng WinMart dự kiến:**\n"
        for p in products:
            res += f"- {p.get('name')}: {int(p.get('price_final', 0)):,}đ\n"
            
    return {
        "final_response": res,
        "messages": [("assistant", res)]
    }