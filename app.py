import streamlit as st
import uuid

from src.core.settings import get_settings
from src.database.mongo_client import get_mongo_client
from src.database.repositories.product_repository import ProductRepository
from src.graph.worker import GraphWorker

# 1. CẤU HÌNH TRANG (configs/app.json + .env)
_ui = get_settings()
st.set_page_config(
    page_title=_ui.streamlit_page_title,
    page_icon=_ui.streamlit_page_icon,
    layout=_ui.streamlit_layout,
)

# 2. KHỞI TẠO RESOURCES (DB & REPO)
@st.cache_resource
def get_db_resources():
    db = get_mongo_client()
    product_repo = ProductRepository(db)
    worker = GraphWorker()
    return product_repo, worker

product_repo, worker = get_db_resources()

@st.cache_data(ttl=600) 
def get_pantry_options_from_db():
    # Gọi hàm get_unique_categories từ Repository bạn đã viết
    return product_repo.get_unique_categories()

pantry_options = get_pantry_options_from_db()

# 3. QUẢN LÝ TRẠNG THÁI (SESSION STATE)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = f"lam_dev_{uuid.uuid4().hex[:4]}"
if "current_meal" not in st.session_state:
    st.session_state.current_meal = None
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "full_name": "Lâm",
        "budget": 200000,
        "persons": 2,
        "pantry_items": [],
        "allergies": []
    }

# 4. SIDEBAR: FORM ĐIỀN THÔNG TIN
with st.sidebar:
    st.header("📋 Hồ Sơ Cá Nhân")
    with st.form("profile_form"):
        name = st.text_input("Tên người dùng", value=st.session_state.user_profile["full_name"])
        budget = st.slider("Ngân sách (VNĐ)", 50000, 1000000, st.session_state.user_profile["budget"], step=10000)
        persons = st.number_input("Số người ăn", min_value=1, value=st.session_state.user_profile["persons"])
        
        st.write("---")
        st.subheader("🧂 Gia vị đã có sẵn")
        
        # Đảm bảo mặc định không gây lỗi nếu DB thay đổi
        defaults = [i for i in st.session_state.user_profile["pantry_items"] if i in pantry_options]
        selected_pantry = st.multiselect("Danh mục sẵn có:", options=pantry_options, default=defaults)
        
        st.write("---")
        allergies_str = st.text_area("Dị ứng (cách nhau bằng dấu phẩy)", 
                                    value=", ".join(st.session_state.user_profile["allergies"]))
        
        if st.form_submit_button("CẬP NHẬT HỒ SƠ", use_container_width=True):
            st.session_state.user_profile.update({
                "full_name": name, "budget": budget, "persons": persons,
                "pantry_items": selected_pantry,
                "allergies": [a.strip() for a in allergies_str.split(",") if a.strip()]
            })
            st.success("Hồ sơ đã lưu!")

    st.divider()
    if st.button("✨ TẠO BỮA ĂN GỢI Ý", type="primary", use_container_width=True):
        with st.spinner("AI đang tính toán thực đơn..."):
            result = worker.run(
                user_id=st.session_state.user_id,
                user_input="Hãy tạo thực đơn 3 món dựa trên hồ sơ.",
                user_profile_from_ui=st.session_state.user_profile
            )
            st.session_state.current_meal = result
            st.session_state.messages.append({"role": "assistant", "content": result.get("final_response", "")})

# 5. GIAO DIỆN CHÍNH
st.title("🥗 SmartMeal Assistant")

# Hiển thị thực đơn (Meal Cards)
if st.session_state.current_meal:
    m = st.session_state.current_meal
    st.subheader("🍴 Thực đơn đề xuất")
    cols = st.columns(3)
    for idx, dish in enumerate(m.get("meal_plan", [])):
        with cols[idx % 3]:
            st.info(f"**Món {idx+1}**\n\n{dish}")
            
    st.metric("Tổng dự toán đi chợ", f"{int(m.get('total_cost', 0)):,}đ")
    
    with st.expander("🛒 Chi tiết giỏ hàng WinMart (Đã lọc đồ có sẵn)"):
        for p in m.get("matched_products", []):
            # Hiển thị category_level_5 cho chi tiết
            cat = p.get('category_level_5', 'Hàng hóa')
            st.write(f"- [{cat}] **{p['name']}**: {int(p['price_final']):,}đ")

# Khu vực Chat
st.divider()
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Bạn muốn điều chỉnh gì không?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang điều chỉnh..."):
            result = worker.run(
                user_id=st.session_state.user_id,
                user_input=prompt,
                user_profile_from_ui=st.session_state.user_profile
            )
            st.session_state.current_meal = result
            st.markdown(result.get("final_response"))
            st.session_state.messages.append({"role": "assistant", "content": result.get("final_response")})
            st.rerun()