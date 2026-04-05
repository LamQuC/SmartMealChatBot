from typing import TypedDict, List, Optional, Annotated
import operator
from langgraph.graph.message import add_messages

class UserProfile(TypedDict):
    """Thông tin cố định từ Form UI"""
    full_name: Optional[str]
    budget: float
    persons: int
    preferences: List[str]
    allergies: List[str]
    pantry_items: List[str]  # Gia vị/đồ dùng sẵn có (Muối, mắm...)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    optimization_log: List[str] # Log các bước tối ưu hóa đã thực hiện
    user_id: str
    # 1. Dữ liệu từ Database nạp vào
    user_profile: UserProfile
    recent_meals: List[List[str]]  # Lịch sử 7 bữa đã CHỐT
    current_session: Optional[dict] # Bữa ăn đang thảo luận trong 12h
    
    # 2. Input từ logic xử lý
    user_owned_ingredients: List[str] # Đồ user vừa báo "nhà còn"
    change_dish_info: str # Thông tin từ IntentAgent về món cần đổi
    
    # 3. Kết quả output
    current_intent: str
    # Mỗi phần tử: {"name", "recipe", "spices_note"} hoặc chuỗi tên món (tương thích cũ)
    meal_plan: List
    raw_ingredients: List[str]
    matched_products: List[dict]
    total_cost: float
    final_response: str