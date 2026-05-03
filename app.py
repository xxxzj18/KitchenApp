import streamlit as st
import datetime
import pandas as pd
import os

# 1. 页面基础配置与 CSS 魔法（美化核心）
st.set_page_config(page_title="厨房调料管家", page_icon="🍳", layout="wide")

# 注入自定义 CSS 来美化看板和按钮
st.markdown("""
    <style>
    /* 美化顶部数据看板，加圆角和阴影 */
    div[data-testid="metric-container"] {
        background-color: #f7f9fc;
        border: 1px solid #e1e4e8;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.04);
    }
    /* 隐藏默认的底部 Streamlit 水印 */
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("🍳 厨房管家")
st.caption("目标：告别混乱，还我厨房清净！✨")

# 2. 数据库与文件夹初始化
DATA_FILE = "kitchen_data.csv"
PHOTO_DIR = "photos"
CORE_COLUMNS = ["调料名称", "生产日期", "保质期(月)", "存放位置", "分类", "照片路径"]

if not os.path.exists(PHOTO_DIR): os.makedirs(PHOTO_DIR)
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=CORE_COLUMNS).to_csv(DATA_FILE, index=False)

df = pd.read_csv(DATA_FILE)

# 【美化大招】使用 Tabs 选项卡分割页面结构
tab1, tab2, tab3 = st.tabs(["📊 库存大盘", "➕ 录入与搜索", "🗑️ 扔垃圾啦"])

# ----------------- Tab 1: 库存大盘 -----------------
with tab1:
    if df.empty:
        st.info("👋 欢迎！目前厨房空空如也，请前往「录入与搜索」添加你的第一瓶调料！")
    else:
        # 数据处理与计算
        display_df = df.copy()
        display_df["生产日期"] = pd.to_datetime(display_df["生产日期"])
        display_df["到期日"] = display_df.apply(lambda row: row["生产日期"] + pd.DateOffset(months=int(row["保质期(月)"])), axis=1)
        today = pd.to_datetime(datetime.date.today())
        display_df["剩余天数"] = (display_df["到期日"] - today).dt.days
        
        display_df["生产日期"] = display_df["生产日期"].dt.strftime("%Y-%m-%d")
        display_df["到期日"] = display_df.apply(lambda row: row["到期日"].strftime("%Y-%m-%d"), axis=1)

        # 顶部看板
        expired_count = len(display_df[display_df["剩余天数"] < 0])
        warning_count = len(display_df[(display_df["剩余天数"] >= 0) & (display_df["剩余天数"] <= 30)])
        safe_count = len(display_df) - expired_count - warning_count
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 安全可用", f"{safe_count} 瓶", "保质期 > 30天")
        c2.metric("🟡 临期预警", f"{warning_count} 瓶", "-30天内到期")
        c3.metric("🔴 毒药警告", f"{expired_count} 瓶", "已过期，快扔！")
        
        st.write("---")
        
        # 优化表格展示
        def highlight_rows(row):
            if row['剩余天数'] < 0: return ['background-color: #ffcccc; color: #a30000'] * len(row)
            elif row['剩余天数'] <= 30: return ['background-color: #fff3cd; color: #856404'] * len(row)
            return [''] * len(row)

        st.subheader("📦 详细清单")
        st.data_editor(
            display_df.style.apply(highlight_rows, axis=1),
            column_config={"照片路径": st.column_config.ImageColumn("调料照片")},
            hide_index=True, use_container_width=True, disabled=True, height=500
        )

# ----------------- Tab 2: 录入与搜索 -----------------
with tab2:
    col_search, col_add = st.columns([1, 1.5], gap="large")
    
    with col_search:
        st.subheader("🔍 去超市前搜一搜")
        st.info("在超市不知道家里有没有？搜一下防重买！")
        search_term = st.text_input("输入调料名称：", placeholder="例如：黄油、生抽...")
        
        if search_term and not df.empty:
            search_res = df[df["调料名称"].str.contains(search_term, na=False)]
            if search_res.empty:
                st.success(f"家里没有找到关于【{search_term}】的调料，放心买！")
            else:
                st.warning(f"家里已经有 {len(search_res)} 份关于【{search_term}】的调料啦！别多买！")
                st.dataframe(search_res[["调料名称", "存放位置"]], hide_index=True, use_container_width=True)

    with col_add:
        st.subheader("➕ 刚买回来的新调料")
        with st.form("my_form", clear_on_submit=True):
            name = st.text_input("调料名称*", placeholder="必填...")
            uploaded_file = st.file_uploader("拍照留档 (选填)", type=["jpg", "jpeg", "png"])
            
            c_date, c_life = st.columns(2)
            produce_date = c_date.date_input("生产日期", datetime.date.today())
            shelf_life = c_life.number_input("保质期(个月)", min_value=1, value=12)
            
            c_loc, c_cat = st.columns(2)
            location = c_loc.selectbox("放哪里了？", ["灶台旁边", "冰箱冷藏", "冰箱冷冻", "吊柜上层", "吊柜下层", "角落纸箱"])
            category = c_cat.selectbox("分个类吧", ["日常调味品", "酱料/调味汁", "烘焙辅料", "干货/香料", "其他"])
            
            submitted = st.form_submit_button("💾 保存到我的厨房", use_container_width=True)
            
            if submitted:
                if name == "":
                    st.error("⚠️ 调料名称不能为空哦！")
                else:
                    img_path = ""
                    if uploaded_file is not None:
                        img_path = os.path.join(PHOTO_DIR, f"{name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png")
                        with open(img_path, "wb") as f: f.write(uploaded_file.getbuffer())
                    
                    new_data = pd.DataFrame({"调料名称": [name], "生产日期": [produce_date], "保质期(月)": [shelf_life], "存放位置": [location], "分类": [category], "照片路径": [img_path]})
                    df = pd.concat([df, new_data], ignore_index=True)
                    df[CORE_COLUMNS].to_csv(DATA_FILE, index=False)
                    # 【美化大招】使用不干扰画面的 Toast 提示
                    st.toast(f"✅ 【{name}】已成功入库！", icon="🎉")
                    st.rerun()

# ----------------- Tab 3: 扔垃圾啦 -----------------
with tab3:
    st.subheader("🗑️ 清理过期物品")
    st.write("把那些红色的过期调料扔进垃圾桶后，记得在这里把它删掉哦。")
    
    if df.empty:
        st.info("太棒了，目前没有什么需要清理的！")
    else:
        delete_list = [f"{i}: {n} (在 {l})" for i, n, l in zip(df.index, df["调料名称"], df["存放位置"])]
        item_to_delete = st.selectbox("选择你要从系统中删掉的物品：", delete_list)
        
        if st.button("🚨 确认删除 (此操作不可恢复)", type="primary"):
            idx = int(item_to_delete.split(":")[0])
            old_path = df.loc[idx, "照片路径"]
            if pd.notna(old_path) and old_path != "" and os.path.exists(str(old_path)):
                os.remove(str(old_path))
            
            df = df.drop(idx).reset_index(drop=True)
            df[CORE_COLUMNS].to_csv(DATA_FILE, index=False)
            st.toast("🗑️ 已清理出局！", icon="🧹")
            st.rerun()
