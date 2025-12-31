import streamlit as st
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# ========== 配置 ==========
ADMIN_PASSWORD = "5201314"
DATA_DIR, IMG_DIR = "data", "images"
RECIPES_FILE = os.path.join(DATA_DIR, "recipes.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
for d in [DATA_DIR, IMG_DIR]:
    os.makedirs(d, exist_ok=True)

# 情侣双向邮箱（留空=不发送）
COUPLE_SMTP = {
    "老公": {"host": "smtp.qq.com",
             "port": 465,
             "user": "1441625686@qq.com",
             "password": "hkysfmfwacegjbfi",
             "partner_email": "3050338817@qq.com"},
    "老婆": {"host": "smtp.qq.com",
             "port": 465,
             "user": "3050338817@qq.com",
             "password": "xmgftrlkmrocdgig",
             "partner_email": "1441625686@qq.com"},
}


# ---------- 数据 ----------
def load_recipes():
    if os.path.exists(RECIPES_FILE):
        with open(RECIPES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def save_recipes(recipes):
    with open(RECIPES_FILE, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def save_orders(orders):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


# ---------- 业务 ----------
def add_recipe(name, price, img_file, desc="", category="菜类"):
    recipes = load_recipes()
    rid = str(int(datetime.now().timestamp()))
    img_path = os.path.join(IMG_DIR, f"{rid}.jpg") if img_file else ""
    if img_file:
        with open(img_path, "wb") as f:
            f.write(img_file.getbuffer())
    recipes.append({
        "id": rid, "name": name, "price": float(price),
        "image": img_path, "description": desc, "category": category
    })
    save_recipes(recipes)


def del_recipe(rid):
    recipes = load_recipes()
    recipes[:] = [r for r in recipes if r["id"] != rid]
    save_recipes(recipes)


def save_order(cart, notes, customer):
    if not cart:
        return
    orders = load_orders()
    oid = datetime.now().strftime("%Y%m%d%H%M%S")
    total = sum(it["price"] * it["quantity"] for it in cart)
    orders.append({
        "id": oid, "customer": customer, "items": cart,
        "notes": notes, "total": total, "created_at": datetime.now().isoformat()
    })
    save_orders(orders)
    send_order_email(customer, oid, cart, notes, total)
    st.success(f"下单成功，总价 ¥{total:.2f}")
    st.balloons()


def send_order_email(customer, oid, cart, notes, total):
    """谁下单，邮件发给对方"""
    cfg = COUPLE_SMTP.get(customer)
    if not cfg:
        return
    items_text = "\n".join([f"- {it['name']} × {it['quantity']} = ¥{it['price']*it['quantity']}"
                            for it in cart])
    content = f"""
❤️ 新订单通知 ❤️
订单号：{oid}
来自：{customer}
时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}

【菜品明细】
{items_text}
备注：{notes}
总价：¥{total:.2f}
    """
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['Subject'] = f"新订单：{customer} 点了 {len(cart)} 道菜"
        msg['From'] = cfg["user"]
        msg['To'] = cfg["partner_email"]
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"]) as srv:
            srv.login(cfg["user"], cfg["password"])
            srv.send_message(msg)
        st.success(f"邮件已发送至 {cfg['partner_email']}")
    except Exception as e:
        st.warning(f"邮件发送失败（不影响下单）：{e}")


# ---------- 页面 ----------
def admin_page():
    st.title("👨‍🍳 菜谱管理")
    with st.form("add"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("菜品名称")
            price = st.number_input("价格（元）", min_value=0.0, step=0.5)
            category = st.selectbox("分类", ["🥗菜类", "🍲汤类", "🍜主食类", "🍰甜品小吃类", "🍓水果类", "🍹饮料类" ,"🌹花类", "💕炒菜类"])
        with c2:
            img = st.file_uploader("上传图片", type=["jpg", "png", "jpeg"])
            desc = st.text_input("描述（可选）")
        if st.form_submit_button("添加菜品", use_container_width=True):
            if name and price and img:
                add_recipe(name, price, img, desc, category)
                st.rerun()
            else:
                st.error("请填写完整并上传图片")

    st.divider()
    st.subheader("已有菜品")
    for r in load_recipes():
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            if r["image"] and os.path.exists(r["image"]):
                st.image(r["image"], width=120)
            else:
                st.image("https://via.placeholder.com/120", width=120)
        with c2:
            st.write(f"**{r['name']}**  （{r['category']}）")
            st.write(f"¥{r['price']}  {r.get('description', '')}")
        with c3:
            if st.button("删除", key=f"del_{r['id']}"):
                del_recipe(r["id"])
                st.rerun()

    st.divider()
    st.subheader("最近订单")
    for o in load_orders()[-5:]:
        with st.expander(f"{o['id']}  {o['customer']}  ¥{o['total']}"):
            for it in o["items"]:
                st.write(f"- {it['name']} × {it['quantity']}")
            st.write(f"备注：{o['notes']}")


def user_page():
    st.title("🍽️ 小陈的私房菜")

    # 1. 原来的「我是老公」「我是老婆」按钮原封不动
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👨‍💼 我是老公", use_container_width=True):
            st.session_state.user_type = "老公"
            st.session_state.customer_name = "老公"
            st.rerun()
    with col2:
        if st.button("👩‍💼 我是老婆", use_container_width=True):
            st.session_state.user_type = "老婆"
            st.session_state.customer_name = "老婆"
            st.rerun()

    st.caption(f"当前用户：**{st.session_state.get('customer_name', '未选择')}**")
    st.divider()

    # 2. 顶部加 1 行分类筛选（不挤按钮区）
    recipes = load_recipes()
    categories = ["全部"] + ["🥗菜类", "🍲汤类", "🍜主食类", "🍰甜品小吃类", "🍓水果类", "🍹饮料类" ,"🌹花类", "💕炒菜类"]
    sel_cat = st.selectbox("选择分类", categories, index=0)
    if sel_cat != "全部":
        recipes = [r for r in recipes if r.get("category") == sel_cat]

    if "cart" not in st.session_state:
        st.session_state.cart = []
    if not recipes:
        st.warning("该分类暂无菜品")
        return

    # 3. 原网格布局完全保留
    cols = st.columns(2)
    for idx, recipe in enumerate(recipes):
        with cols[idx % 2]:
            with st.container(border=True):
                if recipe['image'] and os.path.exists(recipe['image']):
                    st.image(recipe['image'], width=300)
                else:
                    img_path = r["image"] or "https://via.placeholder.com/300"
                    if img_path.startswith("images/"):
                        img_path = img_path[7:]          # 去掉前缀
                    st.image("images/" + img_path, width=300)
                    ##st.image("images/" + os.path.basename(r["image"]), width=300)
                    #st.image("https://via.placeholder.com/300", width=300)
                st.write(f"**{recipe['name']}**")
                st.write(f"💰 ¥{recipe['price']}  （{recipe['category']}）")
                if recipe['description']:
                    st.caption(recipe['description'])
                qty = st.number_input("数量", 0, 10, 0, key=f"qty_{recipe['id']}", label_visibility="collapsed")
                if qty > 0:
                    if st.button("加入购物车", key=f"add_{recipe['id']}", use_container_width=True):
                        for it in st.session_state.cart:
                            if it["id"] == recipe["id"]:
                                it["quantity"] = qty
                                break
                        else:
                            st.session_state.cart.append({"id": recipe["id"], "name": recipe["name"],
                                                          "price": recipe["price"], "quantity": qty})
                        st.success(f"已添加 {recipe['name']} × {qty}")
                        st.rerun()

    # 4. 购物车及以下全部原样
    st.divider()
    st.subheader(f"🛒 购物车 ({len(st.session_state.cart)})")
    if st.session_state.cart:
        total = 0
        for it in st.session_state.cart:
            sub = it["price"] * it["quantity"]
            total += sub
            st.write(f"{it['name']} × {it['quantity']} = ¥{sub:.2f}")
        st.write(f"**总计 ¥{total:.2f}**")
        notes = st.text_area("备注")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("清空购物车"):
                st.session_state.cart = []
                st.rerun()
        with c2:
            if st.button("💕 提交订单", type="primary", use_container_width=True):
                save_order(st.session_state.cart, notes, st.session_state.get('customer_name', '未选择'))
                st.session_state.cart = []
                st.rerun()
    else:
        st.info("购物车是空的～")


def main():
    st.set_page_config(page_title="小陈的私房菜", page_icon="🍽️", layout="wide")
    if st.sidebar.text_input("管理员密码", type="password") == ADMIN_PASSWORD:
        admin_page()
    else:
        user_page()


if __name__ == "__main__":
    main()

















