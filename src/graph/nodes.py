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
from src.core.catalog_constants import is_excluded_main_category

# Nhãn nút sidebar — giữ đồng bộ với app.py
CATALOG_SIDEBAR_BUTTON_LABEL = "Xem hàng hoá WinMart"

# Khởi tạo repo dùng chung
repo = ProductRepository(get_mongo_client())
llm = LLMClient()
memory_repo = MemoryRepository()

def intent_node(state: AgentState):
    """Node điều hướng: Nhận diện Intent & loại bỏ logic Pantry"""
    user_id = state.get("user_id", "lam_ai_eng")
    user_input = state["user_input"]
    
    db_memory = memory_repo.get_user_memory(user_id)
    user_profile = db_memory.get("user_profile", {})
    current_session = db_memory.get("current_session")
    recent_meals = db_memory.get("recent_meals", [])

    intent_agent = IntentAgent(llm)
    result = intent_agent.run(user_input, user_profile)
    detected_intent = result.get("intent", "general_inquiry")
    entities = result.get("entities", {})

    # BỎ owned_items từ entities (vì không quan tâm đồ sẵn có nữa)
    change_dish = entities.get("change_dish", None)

    if detected_intent == "product_browsing":
        return {
            "current_intent": "general_inquiry",
            "user_input": f"Hướng dẫn nhấn sidebar «{CATALOG_SIDEBAR_BUTTON_LABEL}» (gợi ý: {entities.get('search_keyword', 'sản phẩm')}).",
            "meal_plan": [], "matched_products": [], "raw_ingredients": [], "final_response": ""
        }

    return {
        "user_id": user_id,
        "user_profile": user_profile,
        "recent_meals": recent_meals,
        "current_session": current_session,
        "current_intent": detected_intent,
        "user_owned_ingredients": [], # Luôn để rỗng
        "change_dish_info": change_dish or "",
        "meal_plan": [], "matched_products": [], "raw_ingredients": [], 
        "optimization_log": [], "total_cost": 0.0, "final_response": "",
        "messages": [("system", f"Intent: {detected_intent}")]
    }

def _normalize_meal_dishes(raw_dishes: list, fallback_spices: list | None) -> list:
    """Chuẩn hoá món ăn và ghi chú gia vị (chỉ để hiển thị, không lọc hàng)"""
    out = []
    spices_line = ", ".join(str(s) for s in (fallback_spices or []))
    for d in raw_dishes or []:
        if isinstance(d, str):
            out.append({"name": d.strip(), "recipe": "", "spices_note": spices_line})
            continue
        sn = d.get("spices_note") or d.get("spices_needed")
        if isinstance(sn, list): sn = ", ".join(str(x) for x in sn)
        out.append({
            "name": str(d.get("name", "Món")).strip(),
            "recipe": str(d.get("recipe", "")).strip(),
            "spices_note": str(sn or spices_line or "").strip(),
        })
    return out

def meal_planner_node(state: AgentState):
    """Lên thực đơn: Thông minh hơn khi nhận tín hiệu từ kho hàng"""
    try:
        agent = MealPlannerAgent(llm)
        is_rethink = state.get("is_rethink", False)
        
        # Tạo chỉ thị ép AI thay đổi nếu thực đơn cũ không có hàng
        instruction = " (Lưu ý: Mua mới 100%. "
        if is_rethink:
            instruction += "QUAN TRỌNG: Các món trước đó không tìm thấy nguyên liệu tại WinMart, hãy gợi ý 3 món khác dùng nguyên liệu phổ biến hơn. "
        instruction += "Trả về công thức nấu ăn chi tiết từng bước)."

        custom_input = state["user_input"] + instruction
        result = agent.run(custom_input, state)
        
        # Giữ nguyên cấu trúc dishes bao gồm recipe và spices_note
        dishes = _normalize_meal_dishes(result.get("dishes", []), result.get("spices"))

        return {
            "meal_plan": dishes,
            "raw_ingredients": result.get("ingredients", []),
            "is_rethink": False, # Reset flag sau khi lập kế hoạch mới
            "final_response": "", 
            "matched_products": [], 
            "total_cost": 0.0, 
            "optimization_log": [] # Khởi tạo log trống
        }
    except Exception as e:
        logger.error(f"Lỗi Meal Planner: {e}")
        return {
            "final_response": "Trục trặc khi lên món. Thử lại nhé!", 
            "meal_plan": [], 
            "raw_ingredients": [],
            "optimization_log": []
        }

def ingredient_matching_node(state: AgentState):
    """Match hàng WinMart: Kiểm tra tính khả thi và Reset log tối ưu"""
    ingredients_to_buy = state.get("raw_ingredients", [])
    profile = state.get("user_profile", {})

    agent = IngredientMatcherAgent()
    matched_list = agent.run(ingredients_to_buy, profile)

    # --- LOGIC RETHINK (Bảo vệ tính nhất quán) ---
    # Nếu số lượng món khớp < 60% tổng số nguyên liệu chính cần mua
    # và chưa vượt quá số lần thử (ví dụ: tối đa 1 lần tự sửa)
    threshold = 0.6
    if len(ingredients_to_buy) > 0:
        match_rate = len(matched_list) / len(ingredients_to_buy)
        if match_rate < threshold and state.get("rethink_count", 0) < 1:
            logger.warning(f"Rethink: Chỉ khớp {len(matched_list)}/{len(ingredients_to_buy)}. Quay lại Planner.")
            return Command(
                goto="meal_planner_node",
                update={
                    "is_rethink": True,
                    "rethink_count": state.get("rethink_count", 0) + 1,
                    "optimization_log": [] 
                }
            )

    # Nếu ổn, trả về kết quả và ĐẢM BẢO giữ nguyên các key của state
    return {
        "matched_products": matched_list,
        "messages": [("system", f"Đã khớp {len(matched_list)} sản phẩm WinMart mới.")],
        "total_cost": 0.0,      # Sẽ tính lại ở node Budget
        "optimization_log": []  # Reset log để node Budget ghi mới, không bị dính log cũ
    }

def budget_optimizer_node(state: AgentState):
    """Tối ưu ngân sách: Giữ nguyên logic cũ nhưng thêm kiểm tra trùng lặp"""
    products = state.get("matched_products", [])
    budget = state.get("user_profile", {}).get("budget", 0)
    user_id = state.get("user_id", "lam_ai_eng")

    def price_for_budget(p: dict) -> int:
        mc = p.get("main_category") or p.get("category")
        if is_excluded_main_category(mc): return 0
        return int(p.get("price_final", 0) or 0)

    total_cost = sum(price_for_budget(p) for p in products)
    optimization_log = []

    if total_cost > budget:
        sorted_prods = sorted(products, key=lambda x: x.get('price_final', 0), reverse=True)
        optimized = sorted_prods.copy()
        for i, p in enumerate(sorted_prods):
            if sum(price_for_budget(px) for px in optimized) <= budget: break
            if price_for_budget(p) == 0: continue
            
            alt = repo.find_cheaper_alternative(p.get("category_level_5"), p.get("price_final"), p.get("name"))
            if alt:
                optimization_log.append(f"Thay {p['name']} -> {alt['name']}")
                optimized[i] = alt
        products = optimized
        total_cost = sum(price_for_budget(p) for p in products)

    # Lưu session để đồng bộ với UI Sidebar
    memory_repo.update_current_session(user_id, {
        "dishes": state.get("meal_plan", []), 
        "total_cost": total_cost, 
        "products": products
    })

    status = "đã được tối ưu" if total_cost <= budget else "vẫn vượt ngân sách"
    response = f"Thực đơn {status}. Tổng chi phí: {total_cost:,}đ / Ngân sách: {budget:,}đ."
    
    return {
        "matched_products": products, 
        "total_cost": total_cost, 
        "final_response": response, 
        "optimization_log": optimization_log
    }

def final_response_node(state: AgentState):
    """
    Render kết quả cuối cùng: 
    1. Giữ nguyên chuỗi 'res' có chứa Budget để không lỗi UI cũ.
    2. Trả về object để UI mới (Tabs/Cards) hiển thị đẹp hơn.
    """
    res = state.get("final_response", "")
    products = state.get("matched_products", [])
    meal_plan = state.get("meal_plan", []) or []
    budget = state.get("user_profile", {}).get("budget", 0)
    total_cost = state.get("total_cost", 0)

    # Xây dựng phần hiển thị Markdown (vẫn giữ để đề phòng Lâm chưa sửa app.py)
    full_md = f"### {res}\n\n"
    
    if meal_plan:
        full_md += "#### 👨‍🍳 Cách nấu & Công thức\n"
        for d in meal_plan:
            name = d.get('name', 'Món ăn')
            recipe = d.get('recipe', 'Đang cập nhật công thức...')
            spices = d.get('spices_note', 'Gia vị cơ bản')
            full_md += f"**{name}**\n- *Gia vị:* {spices}\n- *Cách nấu:* {recipe}\n\n"

    budget_items = [p for p in products if not is_excluded_main_category(p.get("main_category"))]
    if budget_items:
        full_md += "#### 🛒 Giỏ hàng WinMart\n"
        for p in budget_items:
            p_price = f"{int(p.get('price_final', 0)):,}đ"
            img_list = p.get("image_url") or p.get("images") or []
            img_url = img_list[0] if isinstance(img_list, list) and img_list else p.get("thumbnail") or ""
            img_html = f"<img src='{img_url}' width='45' style='vertical-align:middle; margin-right:10px;'>" if img_url else "📦 "
            full_md += f"<div style='margin-bottom:10px;'>{img_html} <b>{p.get('name')}</b>: <span style='color:red;'>{p_price}</span></div>"

    return {
        "final_response": full_md, # Trả về Markdown đầy đủ cả Budget + Hình ảnh
        "messages": [("assistant", full_md)],
        # Trả về thêm metadata để Lâm làm UI Tabs/Columns bên app.py
        "ui_data": {
            "meal_plan": meal_plan,
            "products": budget_items,
            "total_cost": total_cost,
            "budget": budget
        }
    }

def general_inquiry_node(state: AgentState):
    agent = GeneralAgent(llm)
    response = agent.run(state["user_input"], state.get("user_profile", {}))
    return {"final_response": str(response), "total_cost": 0.0}