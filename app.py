import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import importlib
# 🚨 關鍵：把它搬到這裡！緊接在 import 套件的下方！
st.set_page_config(
    page_title="BamHI Macro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ✅ 設定完網頁後，才能載入你自己寫的這些模組
import config
from data_engine import get_data
import notes 
import data_engine.rates as rates_engine

# ============== 必須保留的 CSS（保留你原本的排版） ==============
st.markdown("""
<style>
    /* 按鈕做成卡片狀 - 避險基金風格 */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #1E1E1E;
        color: white;
        border: 1px solid #4B4B4B;
    }
    .stButton>button:hover {
        border-color: #00FF00;
        color: #00FF00;
    }
    
    /* 全域深色背景 */
    .stApp { background-color: #0d1117; }
    [data-testid="stHeader"] { background-color: #161b22; }
    
    /* 主標題 */
    h1 { color: #e6edf3 !important; font-weight: 700; }
    h2, h3 { color: #c9d1d9 !important; }
    p, label { color: #8b949e !important; }
    
    /* 返回按鈕風格 */
    .stButton > button[kind="secondary"] {
        background: #1E1E1E !important;
        color: white !important;
        border: 1px solid #4B4B4B !important;
    }
</style>
""", unsafe_allow_html=True)


# ============== Session State 初始化 ==============
def init_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = None
    if "selected_item" not in st.session_state:
        st.session_state.selected_item = None

def go_back():
    if st.session_state.page == "detail":
        st.session_state.page = "category_list"
        st.session_state.selected_item = None
    elif st.session_state.page == "category_list":
        st.session_state.page = "home"
        st.session_state.selected_category = None
    else:
        st.session_state.page = "home"

# ============== 第一層：Home ==============
def render_home():
    st.title("📊 BamHI Macro")
    st.markdown("關鍵總經指標，一鍵深入。")
    st.divider()

    indicators_config = config.INDICATORS
    cat_ids = list(indicators_config.keys())
    n = len(cat_ids)
    cols = st.columns(min(n, 3) if n else 1)

    for i, cat_id in enumerate(cat_ids):
        cat = indicators_config[cat_id]
        title = cat.get("title", cat_id)
        with cols[i % 3]:
            if st.button(f"**{title}**", key=f"card_{cat_id}", use_container_width=True, type="secondary"):
                st.session_state.selected_category = cat_id
                st.session_state.page = "category_list"
                st.rerun()

# ============== 第二層：Category List ==============
def render_category_list():
    st.button("← 返回上一層", key="back_from_list", on_click=go_back)
    cat_id = st.session_state.selected_category
    if cat_id not in config.INDICATORS:
        st.session_state.page = "home"
        st.rerun()
        return

    cat = config.INDICATORS[cat_id]
    st.title(f"📋 {cat['title']}")
    st.divider()

    for item in cat["items"]:
        ticker = item["ticker"]
        # 【修改點】加入 item.get("module") 讓系統知道要去哪個資料夾找資料
        row_data = get_data(cat_id, item.get("module"), ticker)
        
        # (修改後的樣子)
        if row_data is None:
            value_str = "—"
        else:
            value_str = f"{row_data['value']:.2f}"
            # change_str 這一行可以刪掉或是留著不理它
            
        # ✨ 關鍵修改：只保留名稱和數值，刪掉後面的漲跌幅
        label = f"{item['name']}  ·  最新: **{value_str}**"
        if st.button(label, key=f"ind_{item['id']}", use_container_width=True, type="secondary"):
            st.session_state.selected_item = {**item, "value": row_data["value"] if row_data else None, "change_pct": row_data["change_pct"] if row_data else None}
            st.session_state.page = "detail"
            st.rerun()

# ============== 第三層：Chart Detail ==============
def render_detail():
    st.button("← 返回上一層", key="back_from_detail", on_click=go_back)
    item = st.session_state.selected_item
    cat_id = st.session_state.selected_category

    if not item:
        st.session_state.page = "category_list"
        st.rerun()
        return

    st.title(f"📈 {item['name']}")
    
    # 【修改點】加入 module 參數
    row_data = get_data(cat_id, item.get("module"), item["ticker"]) if cat_id else None
    
    if row_data:
        st.caption(f"最新: {row_data['value']:.2f}  |  漲跌幅: {row_data['change_pct']:+.2f}%")
        df = row_data["history"]
    else:
        st.caption("無法取得數據")
        df = pd.DataFrame()
    st.divider()

    # =========================================================
    # 【超級核心修改】將時間區間選擇器獨立出來，讓所有圖表共用！
    # =========================================================
    if not df.empty and "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

        # 區間選擇器 (不再限定只有 rates 才能用)
        col_range, _ = st.columns([3, 1])
        with col_range:
            range_option = st.radio("期間", ["All", "6m", "YTD", "1Y", "3Y", "5Y", "10Y"], horizontal=True, key=f"range_{item['id']}")

        # 計算過濾區間
        end = df["date"].max()
        if range_option == "All": start = df["date"].min()
        elif range_option == "6m": start = end - pd.DateOffset(months=6)
        elif range_option == "YTD": start = datetime(end.year, 1, 1)
        elif range_option == "1Y": start = end - pd.DateOffset(years=1)
        elif range_option == "3Y": start = end - pd.DateOffset(years=3)
        elif range_option == "5Y": start = end - pd.DateOffset(years=5)
        else: start = end - pd.DateOffset(years=10) # 10Y

        # 準備好切過的資料
        df_filtered = df[(df["date"] >= start) & (df["date"] <= end)]

        # 【魔法發生的地方】動態呼叫畫圖引擎
        try:
            # 自動去 data_engine / 分類 / 檔案 找 plot_chart 這個畫圖函式
            mod = importlib.import_module(f"data_engine.{cat_id}.{item.get('module')}")
            fig = mod.plot_chart(df_filtered, item)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"無法載入繪圖邏輯：data_engine/{cat_id}/{item.get('module')}.py。錯誤: {e}")

    else:
        st.info("暫無歷史數據可繪製。")

    # ============== 筆記系統 ==============
    st.markdown("---")
    st.subheader(f"📝 {config.INDICATORS[cat_id]['title']} - 交易筆記")
    
    # 【修改點】筆記系統也加入 module 參數來找檔案
    note_content = notes.fetch_note(cat_id, item.get("module"), item["ticker"])
    
    with st.container():
        st.markdown(note_content)
    
    st.caption(f"💡 提示：此筆記由 `notes/{cat_id}/{item.get('module')}.py` 控制。")

# ============== 主程式 ==============
def main():
    init_session_state()
    if st.session_state.page == "home":
        render_home()
    elif st.session_state.page == "category_list":
        render_category_list()
    elif st.session_state.page == "detail":
        render_detail()
    else:
        st.session_state.page = "home"
        st.rerun()

if __name__ == "__main__":
    main()