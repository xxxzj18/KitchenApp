import streamlit as st
import datetime
import pandas as pd
import os

# 1. 页面基础配置
st.set_page_config(page_title="厨房调料管家", page_icon="🍳", layout="wide")

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

st.title("🍳 厨房调料管家 3.2")
st.caption("视觉优化版：只在名称列进行精准红黄预警 ✨")

# 2. 数据库与文件夹初始化
DATA_FILE = "kitchen_data.csv"
PHOTO_DIR = "photos"
CORE_COLUMNS = ["调料名称", "生产日期", "保质期(月)", "存放位置", "分类", "照片路径"]

if not os.path.exists(PHOTO_DIR): os.makedirs(PHOTO_DIR)
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=CORE_COLUMNS).to_csv(DATA_FILE, index=False)

# 读取原始数据
df = pd.read_csv(DATA_FILE)

# 3. 页面标签切换
tab1, tab2, tab3 = st.tabs(["📊 库存大盘 (支持编辑)", "➕ 录入新调料", "🔍 智能搜索"])

# --- 计算逻辑函数 ---
def process_data(input_df):
    temp_df = input_df.copy()
    if not temp_df.empty:
        # 1. 日期计算
        temp_df["生产日期"] = pd.to_datetime(temp_df["生产日期"])
        temp_df["到期日"] = temp_df.apply(lambda row: row["生产日期"] + pd.DateOffset(months=int(row["保质期(月)"])), axis=1)
        today = pd.to_datetime(datetime.date.today())
        temp_df["剩余天数"] = (temp_df["到期日"] - today).dt.days
        
        # 2. 格式化日期为全数字字符串
        temp_df["生产日期"] = temp_df["生产日期"].dt.strftime("%Y-%m-%d")
        temp_df["到期日"] = temp_df["到期日"].dt.strftime("%Y-%m-%d")
        
        # 3. 调整列顺序
        new_order = ["调料名称", "生产日期", "剩余天数", "到期日", "保质期(月)", "存放位置", "分类", "照片路径"]
        temp_df = temp_df[new_order]
        
    return temp_df

# --- 【全新优化】只给名称列上色的样式函数 ---
def highlight_expiry(row):
    # 先生成一个和列数一样长的“无颜色”列表
    styles = [''] * len(row)
    
    # 获取“调料名称”这一列在表格里的排位索引
    name_idx = row.index.get_loc('调料名称')
    days = row['剩余天数']
    
    if days < 0:
        # 已过期：只给名称这一格涂红色
        styles[name_idx] = 'background-color: #ff4b4b; color: white'
    elif 0 <= days <= 30:
        # 临期：只给名称这一格涂黄色
        styles[name_idx] = 'background-color: #f1c40f; color: black'
        
    return styles

# ----------------- Tab 1: 库存大盘 -----------------
with tab1:
    if df.empty:
        st.info("目前厨房空空如也，快去录入第一瓶调料吧！")
    else:
        display_df = process_data(df)
        
        # 顶部看板数据
        expired_count = len(display_df[display_df["剩余天数"] < 0])
        warning_count = len(display_df[(display_df["剩余天数"] >= 0) & (display_df["剩余天数"] <= 30)])
        safe_count = len(display_df) - expired_count - warning_count
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 安全可用", f"{safe_count} 瓶")
        c2.metric("🟡 临期预警 (30天内)", f"{warning_count} 瓶")
        c3.metric("🔴 已经过期", f"{expired_count} 瓶")

        st.subheader("📦 详细清单 (双击格子可直接编辑)")
        
        # 数据编辑器
        edited_df = st.data_editor(
            display_df.style.apply(highlight_expiry, axis=1),
            column_config={
                "照片路径": st.column_config.ImageColumn("预览图"),
                "剩余天数": st.column_config.NumberColumn("剩余天数", format="%d 天"),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )

        if st.button("💾 保存所有修改"):
            save_df = edited_df[CORE_COLUMNS]
            save_df.to_csv(DATA_FILE, index=False)
            st.toast("修改已同步至本地数据库！", icon="✅")
            st.rerun()

# ----------------- Tab 2: 录入新调料 -----------------
with tab2:
    st.subheader("➕ 录入新调料")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("调料名称*")
        uploaded_file = st.file_uploader("拍照/上传图片", type=["jpg", "png", "jpeg"])
        c1, c2 = st.columns(2)
        p_date = c1.date_input("生产日期", datetime.date.today())
        s_life = c2.number_input("保质期(个月)", min_value=1, value=12)
        loc = st.selectbox("存放位置", ["灶台旁边", "冰箱冷藏", "冰箱冷冻", "吊柜上层", "吊柜下层", "角落纸箱"])
        cat = st.selectbox("分类", ["日常调味品", "酱料/调味汁", "烘焙辅料", "干货/香料", "其他"])
        
        if st.form_submit_button("立即存入厨房", use_container_width=True):
            if name:
                path = ""
                if uploaded_file:
                    path = os.path.join(PHOTO_DIR, f"{name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png")
                    with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
                
                new_line = pd.DataFrame([[name, p_date, s_life, loc, cat, path]], columns=CORE_COLUMNS)
                df = pd.concat([df, new_line], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.toast(f"成功添加: {name}")
                st.rerun()
            else:
                st.error("调料名字是必填项哦！")

# ----------------- Tab 3: 智能搜索 -----------------
with tab3:
    st.subheader("🔍 智能匹配搜索")
    query = st.text_input("输入关键词（支持模糊匹配，如‘白糖’找‘白砂糖’）")
    
    if query and not df.empty:
        def smart_match(target_name, search_query):
            target_name = str(target_name).lower()
            search_query = str(search_query).lower()
            return all(char in target_name for char in search_query)

        search_display = process_data(df)
        mask = search_display["调料名称"].apply(lambda x: smart_match(x, query))
        results = search_display[mask]
        
        if results.empty:
            st.warning(f"没找到包含“{query}”的调料。")
        else:
            st.success(f"为您找到 {len(results)} 件匹配项：")
            st.dataframe(
                results.style.apply(highlight_expiry, axis=1), 
                column_config={"照片路径": st.column_config.ImageColumn("预览")}, 
                use_container_width=True,
                hide_index=True
            )
