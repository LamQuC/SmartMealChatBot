import streamlit as st

from src.database.mongo_client import get_mongo_client
from src.database.repositories.memory_repository import MemoryRepository
from src.database.repositories.product_repository import ProductRepository
from src.graph.worker import GraphWorker

# Đồng bộ với src/graph/nodes.py (intent product_browsing)
CATALOG_SIDEBAR_BUTTON_LABEL = "Xem hàng hoá WinMart"

st.set_page_config(
    page_title="SmartMeal AI - WinMart Assistant",
    page_icon="🥗",
    layout="wide",
)


@st.cache_resource
def get_resources():
    db = get_mongo_client()
    return ProductRepository(db), MemoryRepository(), GraphWorker()


product_repo, memory_repo, worker = get_resources()


@st.cache_data(ttl=600)
def get_pantry_options():
    return product_repo.get_unique_categories()


@st.cache_data(ttl=300)
def get_main_categories():
    return product_repo.get_all_main_categories()


def dish_label(dish) -> str:
    if isinstance(dish, dict):
        return str(dish.get("name") or "Món")
    return str(dish)


def dish_recipe(dish) -> str:
    if isinstance(dish, dict):
        return str(dish.get("recipe") or "").strip()
    return ""


def dish_spices_note(dish) -> str:
    if isinstance(dish, dict):
        return str(dish.get("spices_note") or "").strip()
    return ""


def product_thumb_url(p: dict) -> str:
    iu = p.get("image_url")
    if isinstance(iu, list) and iu:
        return str(iu[0])
    if isinstance(iu, str) and iu:
        return iu
    imgs = p.get("images") or []
    if isinstance(imgs, list) and imgs:
        return str(imgs[0])
    return str(p.get("thumbnail") or "")


def product_price(p: dict) -> int:
    v = p.get("price_final")
    if v is not None:
        return int(v)
    sp = p.get("salePrice")
    if sp is not None:
        return int(sp)
    return int(p.get("price") or 0)


def product_item_no(p: dict) -> str:
    return str(p.get("item_no") or p.get("itemNo") or "")


# Session state
if "user_id" not in st.session_state:
    st.session_state.user_id = "lam_dev_01"

if "user_profile" not in st.session_state:
    db_memory = memory_repo.get_user_memory(st.session_state.user_id)
    st.session_state.user_profile = db_memory.get(
        "user_profile",
        {
            "full_name": "Lâm",
            "budget": 200000,
            "persons": 2,
            "preferences": [],
            "pantry_items": [],
            "allergies": [],
        },
    )

if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_meal" not in st.session_state:
    st.session_state.current_meal = None
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "chat"
if "catalog_pick_item_no" not in st.session_state:
    st.session_state.catalog_pick_item_no = None

prof = st.session_state.user_profile

with st.sidebar:
    st.header("👤 Hồ sơ & lưu DB")
    with st.form("profile_form"):
        name = st.text_input("Tên", value=prof.get("full_name") or "")
        budget = st.number_input(
            "Ngân sách món chính (VNĐ)",
            value=int(prof.get("budget") or 200000),
            step=10000,
            help="Chỉ tính nguyên liệu chính; gia vị là ghi chú, không cộng vào tổng này.",
        )
        persons = st.number_input(
            "Số người",
            min_value=1,
            value=int(prof.get("persons") or 2),
        )
        allergies_str = st.text_area(
            "Dị ứng (phân cách bằng dấu phẩy)",
            value=", ".join(prof.get("allergies") or []),
        )
        pantry_opts = get_pantry_options()
        selected_pantry = st.multiselect(
            "Gia vị / đồ có sẵn trong bếp:",
            options=pantry_opts,
            default=[x for x in (prof.get("pantry_items") or []) if x in pantry_opts],
        )

        if st.form_submit_button("💾 Lưu hồ sơ vào MongoDB", use_container_width=True):
            allergies = [a.strip() for a in allergies_str.split(",") if a.strip()]
            updated_profile = {
                "full_name": name,
                "budget": budget,
                "persons": persons,
                "preferences": prof.get("preferences") or [],
                "pantry_items": selected_pantry,
                "allergies": allergies,
            }
            st.session_state.user_profile = updated_profile
            memory_repo.upsert_user_profile(
                st.session_state.user_id, {"user_profile": updated_profile}
            )
            st.success("Đã lưu hồ sơ.")
            st.rerun()

    st.divider()
    st.subheader("Điều hướng")
    if st.button("💬 Chat AI", use_container_width=True):
        st.session_state.view_mode = "chat"
        st.rerun()
    if st.button(f"📦 {CATALOG_SIDEBAR_BUTTON_LABEL}", use_container_width=True):
        st.session_state.view_mode = "catalog"
        st.session_state.catalog_pick_item_no = None
        st.rerun()

    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.session_state.current_meal = None
        st.rerun()

st.title("🥗 SmartMeal Assistant")

if st.session_state.view_mode == "chat":
    m = st.session_state.current_meal
    if m and m.get("meal_plan"):
        st.subheader("🍴 Thực đơn")
        dishes = m.get("meal_plan") or []
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            names = [dish_label(d) for d in dishes]
            pick = st.selectbox(
                "Chọn món để xem công thức",
                ["—"] + names,
                key="meal_recipe_select",
            )
        with c3:
            st.metric(
                "Chi phí nguyên liệu chính (ước tính)",
                f"{int(m.get('total_cost', 0)):,}đ",
            )

        if pick and pick != "—":
            for d in dishes:
                if dish_label(d) == pick:
                    st.markdown("#### Công thức")
                    body = dish_recipe(d) or "_Chưa có công thức chi tiết._"
                    st.markdown(body)
                    sn = dish_spices_note(d)
                    if sn:
                        st.info(f"**Gia vị cần có (ghi chú — không tính tiền):** {sn}")
                    break

        with st.expander("Tóm tắt nhanh các món", expanded=False):
            for d in dishes:
                st.markdown(f"**{dish_label(d)}**")
                if dish_spices_note(d):
                    st.caption(f"Gia vị: {dish_spices_note(d)}")
        st.divider()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Nhập yêu cầu (gợi ý thực đơn, đổi món...)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI đang xử lý..."):
                result = worker.run(
                    user_id=st.session_state.user_id,
                    user_input=prompt,
                    user_profile_from_ui=st.session_state.user_profile,
                )
                st.session_state.current_meal = result
                content = result.get("final_response", "")
                st.markdown(content, unsafe_allow_html=True)
                st.session_state.messages.append(
                    {"role": "assistant", "content": content}
                )
                st.rerun()

else:
    st.header(f"📦 {CATALOG_SIDEBAR_BUTTON_LABEL}")
    st.caption(
        "Trang chỉ để xem hàng hoá. Chọn **danh mục chính** (dropdown), xem lưới sản phẩm kèm ảnh, bấm **Xem chi tiết**."
    )

    main_cats = get_main_categories()
    if not main_cats:
        st.warning("Chưa có dữ liệu main_category trong MongoDB.")
    else:
        selected_cat = st.selectbox("Danh mục chính (main_category)", main_cats, index=0)

        detail_doc = None
        if st.session_state.catalog_pick_item_no:
            detail_doc = product_repo.find_by_item_no(st.session_state.catalog_pick_item_no)

        if detail_doc:
            st.divider()
            b1, b2 = st.columns([4, 1])
            with b1:
                st.subheader(detail_doc.get("name", "Sản phẩm"))
            with b2:
                if st.button("Đóng chi tiết"):
                    st.session_state.catalog_pick_item_no = None
                    st.rerun()

            imgs = []
            if detail_doc.get("image_url"):
                iu = detail_doc["image_url"]
                imgs = iu if isinstance(iu, list) else [iu]
            elif detail_doc.get("images"):
                imgs = detail_doc["images"] or []
            for u in imgs[:6]:
                if u:
                    st.image(u, width=320)

            cleft, cright = st.columns(2)
            with cleft:
                st.write("**Giá:**", f"{int(detail_doc.get('price_final') or 0):,}đ")
                st.write("**Thương hiệu:**", detail_doc.get("brand") or "—")
                st.write("**Danh mục chính:**", detail_doc.get("main_category") or "—")
                for i in range(1, 6):
                    k = f"category_level_{i}"
                    if detail_doc.get(k):
                        st.caption(f"{k}: {detail_doc.get(k)}")
            with cright:
                st.write("**Mã sản phẩm:**", detail_doc.get("item_no") or "—")
                st.write("**Tồn (nếu có):**", detail_doc.get("stock_quantity", "—"))

            if detail_doc.get("short_description"):
                st.markdown("**Mô tả ngắn**")
                st.write(detail_doc["short_description"])
            if detail_doc.get("long_description"):
                st.markdown("**Mô tả chi tiết**")
                st.write(detail_doc["long_description"])

            attrs = detail_doc.get("attributes") or {}
            if attrs:
                st.markdown("**Thông tin thêm**")
                for ak, av in attrs.items():
                    if av:
                        st.write(f"- **{ak}:** {av}")

            st.divider()

        prods = product_repo.get_products_by_main_category(selected_cat)
        st.caption(f"{len(prods)} sản phẩm trong «{selected_cat}»")

        grid = st.columns(4)
        for idx, p in enumerate(prods):
            with grid[idx % 4]:
                pid = product_item_no(p) or f"idx_{idx}"
                title = p.get("name", "Sản phẩm")
                img_u = product_thumb_url(p)
                if img_u:
                    st.image(img_u, use_container_width=True)
                st.markdown(f"**{title}**")
                st.caption(f"{product_price(p):,}đ")
                if st.button("Xem chi tiết", key=f"cat_det_{pid}_{idx}", use_container_width=True):
                    st.session_state.catalog_pick_item_no = pid
                    st.rerun()
