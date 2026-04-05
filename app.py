import streamlit as st
from datetime import datetime, timedelta
from src.database.mongo_client import get_mongo_client
from src.database.repositories.memory_repository import MemoryRepository
from src.database.repositories.product_repository import ProductRepository
from src.graph.worker import GraphWorker

# --- CẤU HÌNH ---
CATALOG_SIDEBAR_BUTTON_LABEL = "Xem hàng hoá WinMart"

st.set_page_config(page_title="SmartMeal AI", page_icon="🥗", layout="wide")

@st.cache_resource
def get_resources():
    db = get_mongo_client()
    return ProductRepository(db), MemoryRepository(), GraphWorker()

product_repo, memory_repo, worker = get_resources()

# --- UTILS HIỂN THỊ ---
def get_thumb(p: dict) -> str:
    iu = p.get("image_url") or p.get("images") or p.get("thumbnail") or ""
    return str(iu[0]) if isinstance(iu, list) and iu else str(iu)

def get_price(p: dict) -> int:
    return int(p.get("price_final") or p.get("salePrice") or p.get("price") or 0)

# --- SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = "lam_dev_01"
if "messages" not in st.session_state: st.session_state.messages = []
if "current_meal" not in st.session_state: st.session_state.current_meal = None
if "view_mode" not in st.session_state: st.session_state.view_mode = "chat"
if "profile_updated" not in st.session_state: st.session_state.profile_updated = False
if "catalog_pick_item_no" not in st.session_state: st.session_state.catalog_pick_item_no = None

# Tải hồ sơ từ DB (Đã loại bỏ pantry_items)
if "user_profile" not in st.session_state:
    db_memory = memory_repo.get_user_memory(st.session_state.user_id)
    st.session_state.user_profile = db_memory.get("user_profile", {
        "full_name": "Lâm", 
        "budget": 200000, 
        "persons": 2, 
        "allergies": [], 
        "last_updated": None
    })

# --- HÀM NGHIỆP VỤ AI ---
def trigger_meal_planning(reason: str):
    """Gọi Worker để lên thực đơn dựa trên Profile mới (không check đồ sẵn)"""
    with st.spinner(f"AI đang {reason}..."):
        # Gửi kèm hướng dẫn ngầm để AI tính toán mua mới toàn bộ
        result = worker.run(
            user_id=st.session_state.user_id,
            user_input=f"Hãy {reason}. Lưu ý: Tính toán chi phí cho toàn bộ nguyên liệu cần dùng.",
            user_profile_from_ui=st.session_state.user_profile
        )
        st.session_state.current_meal = result
        st.session_state.messages.append({"role": "assistant", "content": result.get("final_response", "")})
        st.session_state.profile_updated = False
        st.session_state.view_mode = "chat"
        st.rerun()

# --- SIDEBAR: HỒ SƠ & ĐIỀU HƯỚNG ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user_profile['full_name']}")
    
    with st.expander("📝 Thông tin hồ sơ", expanded=True):
        p = st.session_state.user_profile
        st.write(f"**Ngân sách:** {p['budget']:,}đ")
        st.write(f"**Số người:** {p['persons']}")
        st.caption(f"**Dị ứng:** {', '.join(p['allergies']) if p['allergies'] else 'Không'}")
        if st.button("Sửa hồ sơ", use_container_width=True):
            st.session_state.view_mode = "setup"
            st.rerun()

    st.divider()

    if st.session_state.profile_updated or not st.session_state.current_meal:
        btn_label = "🍽️ LÀM MỚI THỰC ĐƠN" if st.session_state.current_meal else "🍽️ TẠO BỮA ĂN ĐẦU TIÊN"
        if st.button(btn_label, type="primary", use_container_width=True):
            trigger_meal_planning("tạo thực đơn mới")

    st.divider()
    if st.button("💬 Chat AI", use_container_width=True): 
        st.session_state.view_mode = "chat"
        st.rerun()
    if st.button(f"📦 {CATALOG_SIDEBAR_BUTTON_LABEL}", use_container_width=True): 
        st.session_state.view_mode = "catalog"
        st.rerun()
    
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.session_state.current_meal = None
        st.rerun()

# --- NỘI DUNG CHÍNH ---

# 1. MÀN HÌNH SETUP (Loại bỏ Multiselect Gia vị/Đồ có sẵn)
if st.session_state.view_mode == "setup":
    st.subheader("Cập nhật hồ sơ nấu ăn")
    prof = st.session_state.user_profile
    with st.form("update_profile_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Tên", value=prof['full_name'])
            budget = st.number_input("Ngân sách (VNĐ)", value=int(prof['budget']), step=10000)
            
        with c2:
            persons = st.number_input("Số người", min_value=1, value=int(prof['persons']))
            # KHÔNG CÒN PHẦN CHỌN PANTRY Ở ĐÂY
            st.info("💡 AI sẽ tự động gợi ý danh sách mua sắm đầy đủ cho các món ăn.")
        prefs_str = st.text_area("Sở thích ăn uống (VD: đồ Hàn, ít dầu mỡ, thích ăn cay...)", 
                             value=", ".join(prof.get("preferences", [])))
        allergies_str = st.text_area("Dị ứng (phân cách bằng dấu phẩy)", value=", ".join(prof['allergies']))
        
        if st.form_submit_button("LƯU THÔNG TIN"):
            updated_profile = {
                "full_name": name, 
                "budget": budget, 
                "persons": persons,
                "allergies": [a.strip() for a in allergies_str.split(",") if a.strip()],
                "preferences": [p.strip() for p in prefs_str.split(",") if p.strip()],
                "last_updated": datetime.now().isoformat()
            }
            st.session_state.user_profile = updated_profile
            memory_repo.upsert_user_profile(st.session_state.user_id, {"user_profile": updated_profile})
            
            st.session_state.profile_updated = True 
            st.session_state.view_mode = "chat"
            st.success("Đã lưu! Hãy bấm nút 'Làm mới thực đơn' ở Sidebar.")
            st.rerun()

# 2. MÀN HÌNH CHAT
elif st.session_state.view_mode == "chat":
    # Logic 12h
    if st.session_state.profile_updated and st.session_state.user_profile.get("last_updated"):
        last_ts = datetime.fromisoformat(st.session_state.user_profile["last_updated"])
        if datetime.now() > last_ts + timedelta(hours=12):
            trigger_meal_planning("tự động cập nhật thực đơn")

    # Widget thực đơn
    if st.session_state.current_meal:
        m = st.session_state.current_meal
        with st.container(border=True):
            st.markdown("### 🍴 Thực đơn đang áp dụng")
            cols = st.columns(len(m.get("meal_plan", [])) or 1)
            for i, dish in enumerate(m.get("meal_plan", [])):
                d_name = dish.get("name") if isinstance(dish, dict) else dish
                cols[i].success(f"**{d_name}**")
            st.caption(f"💰 Tổng chi phí dự kiến: {int(m.get('total_cost', 0)):,}đ")

    # Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Hỏi AI..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            result = worker.run(st.session_state.user_id, prompt, st.session_state.user_profile)
            content = result.get("final_response", "")
            st.markdown(content, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": content})
        st.rerun()

# 3. MÀN HÌNH CATALOG
elif st.session_state.view_mode == "catalog":
    st.header(f"📦 {CATALOG_SIDEBAR_BUTTON_LABEL}")
    main_cats = product_repo.get_all_main_categories()
    if main_cats:
        selected_cat = st.selectbox("Chọn danh mục hàng", main_cats)
        
        if st.session_state.catalog_pick_item_no:
            detail = product_repo.find_by_item_no(st.session_state.catalog_pick_item_no)
            if detail:
                with st.container(border=True):
                    c_img, c_txt = st.columns([1, 2])
                    c_img.image(get_thumb(detail), width=250)
                    c_txt.subheader(detail.get("name"))
                    c_txt.write(f"Giá: {get_price(detail):,}đ")
                    if st.button("Đóng chi tiết"):
                        st.session_state.catalog_pick_item_no = None
                        st.rerun()
        
        prods = product_repo.get_products_by_main_category(selected_cat)
        grid = st.columns(4)
        for idx, p in enumerate(prods):
            with grid[idx % 4]:
                st.image(get_thumb(p), use_container_width=True)
                st.markdown(f"**{p.get('name')}**")
                st.caption(f"{get_price(p):,}đ")
                if st.button("Chi tiết", key=f"cat_{idx}", use_container_width=True):
                    st.session_state.catalog_pick_item_no = p.get("item_no")
                    st.rerun()