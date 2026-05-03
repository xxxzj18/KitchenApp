import streamlit as st
import datetime
import pandas as pd
import os

# 1. 页面基础配置
st.set_page_config(page_title="厨房管家", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #f7f9fc;
        border: 1px solid #e1e4e8;
        padding: 15px 20px;
        border-radius: 12px;
    }
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("🍳 厨房调料管家 3.0")
st.caption("支持智能模糊搜索、直接在线编辑数据 ✨")

# 2. 数据库与文件夹初始化
DATA_FILE = "kitchen_data.csv"
PHOTO_DIR = "photos"
CORE_COLUMNS = ["调料名称", "生产日期", "保质期(月)", "存放位置", "分类", "照片路径"]

if not os.path.exists(PHOTO_DIR): os.makedirs(PHOTO_DIR)
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=CORE_COLUMNS).to_csv(DATA_FILE, index=False)

# 读取数据
df = pd.read_csv(DATA_FILE)

# 3. 页面标签切换
tab1, tab2, tab3 = st.tabs(["📊 库存大盘 (支持编辑)", "➕ 录入新调料", "🔍 智能搜索"])

# --- 计算逻辑函数 ---
def process_data(input_df):
    temp_df = input_df.copy()
    if not temp_df.empty:
        # 确保日期显示为数字格式: YYYY-MM-DD
        temp_df["生产日期"] = pd.to_datetime(temp_df["生产日期"])
        temp_df["到期日"] = temp_df.apply(lambda row: row["生产日期"] + pd.DateOffset(months=int(row["保质期(月)"])), axis=1)
        today = pd.to_datetime(datetime.date.today())
        temp_df["剩余天数"] = (temp_df["到期日"] - today).dt.days
        # 转回全数字字符串
        temp_df["生产日期"] = temp_df["生产日期"].dt.strftime("%Y-%m-%d")
        temp_df["到期日"] = temp_df["到期日"].dt.strftime("%Y-%m-%d")
    return temp_df

# ----------------- Tab 1: 库存大盘 (增加编辑保存功能) -----------------
with tab1:
    if df.empty:
        st.info("目前厨房空空如也。")
    else:
        display_df = process_data(df)
        
        # 顶部看板
        expired_count = len(display_df[display_df["剩余天数"] < 0])
        warning_count = len(display_df[(display_df["剩余天数"] >= 0) & (display_df["剩余天_数"] <= 30)])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 安全可用", f"{len(display_df)-expired_count-warning_count} 瓶")
        c2.metric("🟡 临期预警", f"{warning_count} 瓶")
        c3.metric("🔴 毒药警告", f"{expired_count} 瓶")

        st.subheader("📦 详细清单 (双击格子可直接修改)")
        
        # 使用 data_editor 让表格变得可以编辑
        edited_df = st.data_editor(
            display_df,
            column_config={
                "照片路径": st.column_config.ImageColumn("预览图"),
                "剩余天数": st.column_config.NumberColumn("剩余天数", format="%d 天"),
            },
            hide_index=False, # 显示索引方便对应
            use_container_width=True,
            num_rows="dynamic" # 允许在表格里直接删除行
        )

        # 检查是否有改动并保存
        if st.button("💾 保存表格中的修改"):
            # 将编辑后的数据中，属于核心字段的部分保存回 CSV
            # 注意：只保存录入时的原始字段，不保存计算出来的“剩余天数”
            save_df = edited_df[CORE_COLUMNS]
            save_df.to_csv(DATA_FILE, index=False)
            st.toast("数据保存成功！", icon="✅")
            st.rerun()

# ----------------- Tab 2: 录入新调料 -----------------
with tab2:
    st.subheader("➕ 录入新成员")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("调料名称*")
        uploaded_file = st.file_uploader("拍照", type=["jpg", "png", "jpeg"])
        c1, c2 = st.columns(2)
        p_date = c1.date_input("生产日期", datetime.date.today())
        s_life = c2.number_input("保质期(个月)", min_value=1, value=12)
        loc = st.selectbox("位置", ["灶台旁边", "冰箱冷藏", "冰箱冷冻", "吊柜上层", "吊柜下层", "角落纸箱"])
        cat = st.selectbox("分类", ["日常调味品", "酱料/调味汁", "烘焙辅料", "干货/香料", "其他"])
        
        if st.form_submit_button("保存", use_container_width=True):
            if name:
                path = ""
                if uploaded_file:
                    path = os.path.join(PHOTO_DIR, f"{name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png")
                    with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
                
                new_line = pd.DataFrame([[name, p_date, s_life, loc, cat, path]], columns=CORE_COLUMNS)
                df = pd.concat([df, new_line], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.toast(f"已存入 {name}")
                st.rerun()
            else:
                st.error("请填写名称")

# ----------------- Tab 3: 智能搜索 (解决白糖搜不到白砂糖的问题) -----------------
with tab3:
    st.subheader("🔍 智能模糊搜索")
    query = st.text_input("搜一搜 (支持拆分关键词，如输入‘白糖’也可搜到‘白砂糖’)")
    
    if query and not df.empty:
        # 智能匹配逻辑：检查查询词中的每一个字是否都在名称中出现
        def smart_match(target_name, search_query):
            target_name = str(target_name).lower()
            search_query = str(search_query).lower()
            # 只要搜索词里的字都在目标里，就返回 True
            return all(char in target_name for char in search_query)

        search_display = process_data(df)
        mask = search_display["调料名称"].apply(lambda x: smart_match(x, query))
        results = search_display[mask]
        
        if results.empty:
            st.warning(f"没搜到包含“{query}”的调料。")
        else:
            st.success(f"为您找到 {len(results)} 件匹配项：")
            st.dataframe(results, column_config={"照片路径": st.column_config.ImageColumn("预览")}, use_container_width=True)
