"""
BamHI Macro Dashboard - 資料驅動三層架構
頁面：home -> category_list -> detail，由 config.INDICATORS 與 data_engine 驅動。
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

import config
from data_engine import get_data
import notes 
import data_engine.rates as rates_engine # <--- 【新增】引用 rates 模組來畫圖

# ============== 頁面配置 ==============
st.set_page_config(
    page_title="BamHI Macro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============== 必須保留的 CSS（勿修改內容） ==============
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
    p, span, label { color: #8b949e !important; }
    
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


# ============== 第一層：Home（依 config 動態生成分類卡片） ==============
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
            if st.button(
                f"**{title}**",
                key=f"card_{cat_id}",
                use_container_width=True,
                type="secondary"
            ):
                st.session_state.selected_category = cat_id
                st.session_state.page = "category_list"
                st.rerun()


# ============== 第二層：Category List（依 config 清單 + data_engine 真實報價） ==============
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
        row_data = get_data(cat_id, ticker)
        if row_data is None:
            value_str = "—"
            change_str = "—"
        else:
            value_str = f"{row_data['value']:.2f}"
            ch = row_data["change_pct"]
            change_str = f"{ch:+.2f}%"
        label = f"{item['name']}  ·  最新: **{value_str}**  ·  {change_str}"
        if st.button(
            label,
            key=f"ind_{item['id']}",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state.selected_item = {**item, "value": row_data["value"] if row_data else None, "change_pct": row_data["change_pct"] if row_data else None}
            st.session_state.page = "detail"
            st.rerun()


# ============== 第三層：Chart Detail（Plotly 線圖 + 分析區） ==============
def render_detail():
    st.button("← 返回上一層", key="back_from_detail", on_click=go_back)
    item = st.session_state.selected_item
    cat_id = st.session_state.selected_category

    if not item:
        st.session_state.page = "category_list"
        st.rerun()
        return

    # 1. 繪圖邏輯
    st.title(f"📈 {item['name']}")
    row_data = get_data(cat_id, item["ticker"]) if cat_id else None
    
    if row_data:
        df = row_data["history"]
    else:
        df = pd.DataFrame()

    if cat_id == "rates" and not df.empty and "date" in df.columns:
        col_range, _ = st.columns([3, 1])
        with col_range:
            range_option = st.radio("期間", ["All", "6m", "YTD", "1Y", "3Y", "5Y", "10Y"], horizontal=True, key=f"range_{item['id']}")
        fig = rates_engine.plot_rates_chart(df, item, range_option)
        st.plotly_chart(fig, use_container_width=True)

    elif not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["date"], y=df["value"], fill="tozeroy", line=dict(color="#00FF00")))
        fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(22, 27, 34, 0.9)", paper_bgcolor="rgba(0,0,0,0)", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無歷史數據")

    # 2. 筆記系統 (已修復：刪除 ugly table，改用純淨顯示)
    st.markdown("---")
    st.subheader(f"📝 {config.INDICATORS[cat_id]['title']} - 交易筆記")
    
    note_content = notes.fetch_note(cat_id, item["ticker"])
    
    # 這裡使用 container 包住，創造一點背景區隔，但不會變成表格亂碼
    with st.container():
        st.markdown(note_content)
    
    st.caption(f"💡 提示：此筆記由 `notes/{cat_id}.py` 控制，修改檔案後請按 'R' 重新整理。")

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
