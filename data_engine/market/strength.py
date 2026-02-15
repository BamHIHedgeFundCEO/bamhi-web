"""
data_engine/market/strength.py
讀取 sector_strength.csv 並使用 Tabs 顯示大板塊與小板塊
(視覺優化版：高亮配色 + 高精度小數點)
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.colors as pc
import pandas as pd
from data_engine import load_csv

# 定義清單
BENCHMARK = "VTI"
SECTORS_BIG = [
    'VGT', 'VHT', 'VFH', 'VCR', 'VOX', 'VIS', 
    'VDC', 'VDE', 'VPU', 'VAW', 'VNQ'
]
SECTORS_SMALL = [
    'SMH', 'IGV', 'CIBR', 'SKYY', 'FINX', 
    'XBI', 'UFO', 'ROBO', 
    'XOP', 'OIH', 'URA', 'NLR', 'TAN', 
    'GDX', 'COPX', 'LIT', 
    'XHB', 'XRT', 'IYT', 'JETS', 'PAVE', 
    'ITA', 'IHI'
]

def fetch_data(ticker: str):
    df = load_csv("sector_strength.csv")
    if df is None: return None
    
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    latest_price = 0.0
    if BENCHMARK in df.columns:
        latest_price = float(df[BENCHMARK].iloc[-1])

    return {
        "history": df,
        "value": latest_price,
        "change_pct": 0.0
    }

def _create_fig(df, tickers, title_suffix):
    fig = go.Figure()

    # 1. 畫基準 VTI (左軸) - 白色半透明，當作背景參考
    if BENCHMARK in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[BENCHMARK],
            mode='lines', name=f'{BENCHMARK} (左軸)',
            line=dict(color='white', width=4, dash='solid'),
            yaxis='y1', opacity=0.3 # 調淡一點，讓主角更明顯
        ))

    # 2. 畫板塊 RS (右軸)
    
    # 🎨 [配色優化]：使用高亮、高對比的色彩組合，避免深紫色/深藍色看不見
    # 組合 Prism (鮮豔) + Pastel (粉嫩亮) + Bold (粗獷亮)，確保在黑底都很清楚
    bright_colors = pc.qualitative.Prism + pc.qualitative.Pastel + pc.qualitative.Bold
    # 移除可能太暗的顏色 (手動過濾掉一些深色，這裡先依賴 Plotly 的亮色系)
    
    if not tickers:
        fig.update_layout(title="請選擇至少一個板塊", height=600, template="plotly_dark")
        return fig

    for i, t in enumerate(tickers):
        if t not in df.columns: continue
        
        rs = df[t] / df[BENCHMARK]
        
        first_valid = rs.first_valid_index()
        if first_valid is not None:
            base_value = rs.loc[first_valid]
            if base_value > 0:
                rs = rs / base_value

        # 循環使用亮色系
        line_color = bright_colors[i % len(bright_colors)]

        fig.add_trace(go.Scatter(
            x=df["date"], y=rs,
            mode='lines', 
            name=f'{t} / {BENCHMARK}',
            line=dict(width=2, color=line_color),
            yaxis='y2',
            # 這裡設定個別線條的 hover 格式，但主要還是靠 layout 全局設定
        ))

    # 3. 版面設定
    recessions = [("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30")]
    shapes = [dict(type="rect", xref="x", yref="paper", x0=s, x1=e, y0=0, y1=1, fillcolor="white", opacity=0.1, layer="below", line_width=0) for s, e in recessions]

    fig.update_layout(
        title=f"相對強度分析 - {title_suffix}",
        hovermode="x unified",
        height=650,
        template="plotly_dark",
        shapes=shapes,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
        ),
        yaxis=dict(
            title=f"{BENCHMARK} Price",
            side="left", showgrid=False,
            titlefont=dict(color="rgba(255,255,255,0.5)"), # 標題也淡一點
            tickfont=dict(color="rgba(255,255,255,0.5)")
        ),
        yaxis2=dict(
            title="Relative Strength",
            side="right",
            overlaying="y",
            showgrid=True,
            gridcolor="#333333",
            
            # 🔥 [關鍵設定 1]：Y軸刻度顯示 2 位小數，保持整潔 (例如 1.50)
            tickformat=".2f", 
            dtick=0.5,
            
            # 🔥 [關鍵設定 2]：滑鼠懸停 (Hover) 時顯示 6 位小數！(例如 1.501234)
            hoverformat=".6f"
        )
    )

    fig.update_xaxes(
        showgrid=False,
        rangeselector=dict(
            buttons=list([
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(count=3, label="3y", step="year", stepmode="backward"),
                dict(count=5, label="5y", step="year", stepmode="backward"),
                dict(step="all", label="All")
            ]),
            bgcolor="#333333",
            activecolor="#00d2ff",
            x=0, y=1.05
        )
    )
    return fig

def plot_chart(df, item_name):
    tab1, tab2 = st.tabs(["🛡️ GICS 大板塊 (Big)", "🚀 戰術型 Alpha (Small)"])
    with tab1:
        st.subheader("GICS 11 大板塊相對強度")
        selected_big = st.multiselect("👇 選擇板塊:", options=SECTORS_BIG, default=SECTORS_BIG, key="ms_big")
        fig1 = _create_fig(df, selected_big, "Big Sectors")
        st.plotly_chart(fig1, use_container_width=True)
    with tab2:
        st.subheader("戰術型子產業相對強度")
        # 預設全開，因為現在有篩選器很方便
        selected_small = st.multiselect("👇 選擇板塊:", options=SECTORS_SMALL, default=SECTORS_SMALL, key="ms_small")
        fig2 = _create_fig(df, selected_small, "Tactical Alpha")
        st.plotly_chart(fig2, use_container_width=True)

    empty_fig = go.Figure()
    empty_fig.update_layout(height=10, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return empty_fig