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
    if detected_intent == "product_browsing":
        return {
            "current_intent": "general_inquiry",
            "user_input": (
                f"Hãy hướng dẫn người dùng nhấn nút sidebar «{CATALOG_SIDEBAR_BUTTON_LABEL}» "
                f"để xem danh mục hàng hoá (gợi ý từ khoá: {entities.get('search_keyword', 'sản phẩm')})."
            ),
            "meal_plan": [], 
            "matched_products": [],
            "raw_ingredients": [],
            "final_response": ""
        }
    # Nếu đang trong 12h và user muốn đổi món, ta giữ nguyên Context cũ
    return {
        "user_id": user_id,
        "user_profile": user_profile,
        "recent_meals": recent_meals,
        "current_session": current_session,
        "current_intent": detected_intent,
        "user_owned_ingredients": owned_items,
        "change_dish_info": change_dish or "",
        
        "meal_plan": [], 
        "matched_products": [],
        "raw_ingredients": [], 
        "optimization_log": [],
        "total_cost": 0.0,
        "final_response": "",
        "messages": [("system", f"Intent: {detected_intent} | New Session Started")]
    }

def _normalize_meal_dishes(raw_dishes: list, fallback_spices: list | None) -> list:
    """Chuẩn hoá dishes từ LLM: list[str] hoặc list[{name, recipe, spices_note}]."""
    out = []
    fallback_spices = fallback_spices or []
    spices_line = ", ".join(str(s) for s in fallback_spices) if fallback_spices else ""
    for d in raw_dishes or []:
        if isinstance(d, str):
            out.append(
                {
                    "name": d.strip(),
                    "recipe": "",
                    "spices_note": spices_line,
                }
            )
            continue
        if not isinstance(d, dict):
            continue
        sn = d.get("spices_note") or d.get("spices_needed")
        if isinstance(sn, list):
            sn = ", ".join(str(x) for x in sn)
        out.append(
            {
                "name": str(d.get("name", "Món")).strip(),
                "recipe": str(d.get("recipe", "") or "").strip(),
                "spices_note": str(sn or spices_line or "").strip(),
            }
        )
    return out


def meal_planner_node(state: AgentState):
    """Lên thực đơn mới hoặc điều chỉnh thực đơn hiện tại"""
    try:
        agent = MealPlannerAgent(llm)
        # Truyền cả state để Agent biết Profile và Current Session (12h logic)
        result = agent.run(state["user_input"], state)
        dishes = _normalize_meal_dishes(
            result.get("dishes", []), result.get("spices")
        )

        return {
            "meal_plan": dishes,
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
    Chỉ tính tiền nguyên liệu chính — không tính gia vị (danh mục loại trừ).
    """
    products = state.get("matched_products", [])
    budget = state.get("user_profile", {}).get("budget", 0)
    user_id = state.get("user_id", "lam_ai_eng")

    def price_for_budget(p: dict) -> int:
        mc = p.get("main_category") or p.get("category")
        if is_excluded_main_category(mc):
            return 0
        return int(p.get("price_final", 0) or 0)

    def calculate_total(prod_list):
        return sum(price_for_budget(p) for p in prod_list)

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
            if price_for_budget(p) == 0:
                continue

            # 2. Tìm hàng thay thế rẻ hơn cùng loại (category_level_5)
            alternative = repo.find_cheaper_alternative(
                p.get("category_level_5"),
                p.get("price_final"),
                p.get("name"),
            )

            if alternative and not is_excluded_main_category(
                alternative.get("main_category")
            ):
                optimization_log.append(f"Thay {p['name']} -> {alternative['name']}")
                optimized_products[i] = alternative
        
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

    response = (
        f"Thực đơn {status}. "
        f"Tổng chi phí nguyên liệu chính (không gồm gia vị): {total_cost:,}đ / Ngân sách: {budget:,}đ."
    )
    
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
    """Render kết quả cuối cùng — giỏ chỉ nguyên liệu chính; gia vị theo từng món (ghi chú)."""
    res = state.get("final_response", "")
    products = state.get("matched_products", [])
    meal_plan = state.get("meal_plan", []) or []

    # 0. Tóm tắt món + ghi chú gia vị (không tính tiền)
    if meal_plan:
        res += "\n\n### 🍽️ Thực đơn & gia vị cần có (ghi chú)\n"
        for d in meal_plan:
            if isinstance(d, dict):
                nm = d.get("name", "")
                sn = (d.get("spices_note") or "").strip()
                res += f"- **{nm}**"
                if sn:
                    res += f" — _Gia vị:_ {sn}"
                res += "\n"
            else:
                res += f"- {d}\n"
        res += "\n*(Chi phí ước tính bên dưới chỉ áp dụng cho nguyên liệu chính — không gồm gia vị.)*\n"

    profile = state.get("user_profile", {})
    pantry = [i.lower() for i in profile.get("pantry_items", [])]

    # 1. Giỏ hàng — chỉ món không thuộc danh mục gia vị (phòng trường hợp lọc sót)
    budget_items = [
        p
        for p in products
        if not is_excluded_main_category(p.get("main_category") or p.get("category"))
    ]
    if budget_items:
        res += "\n\n### 🛒 Giỏ hàng WinMart (nguyên liệu chính)\n"
        for p in budget_items:
            p_name = p.get("name", "Sản phẩm")
            p_price = f"{int(p.get('price_final', 0)):,}đ"

            img_list = p.get("image_url") or p.get("images") or []
            if isinstance(img_list, str):
                img_list = [img_list]
            img_url = img_list[0] if img_list else p.get("thumbnail") or ""
            img_html = (
                f"<img src='{img_url}' width='45' style='border-radius:5px; margin-right:10px; vertical-align:middle;'>"
                if img_url
                else "📦 "
            )

            res += f"<div style='margin-bottom:10px;'>{img_html} <b>{p_name}</b>: <span style='color:red;'>{p_price}</span></div>"

    # 2. So khớp gia vị gợi ý với pantry (theo từng dòng spices_note)
    spice_hints: list[str] = []
    for d in meal_plan:
        if isinstance(d, dict) and d.get("spices_note"):
            spice_hints.append(d["spices_note"])
    if spice_hints and pantry:
        combined = " ".join(spice_hints).lower()
        maybe_missing = []
        for word in ["nước mắm", "đường", "dầu", "muối", "tiêu", "tỏi", "hạt nêm", "bột ngọt"]:
            if word in combined and not any(word in p for p in pantry):
                maybe_missing.append(word)
        if maybe_missing:
            res += f"\n\n**⚠️ Kiểm tra bếp:** có thể cần thêm: _{', '.join(dict.fromkeys(maybe_missing))}_ (so với ghi chú gia vị)."

    return {"final_response": res, "messages": [("assistant", res)]}