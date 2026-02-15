"""S&P 500 市場寬度數據引擎"""
"""
data_engine/market/breadth.py
(極速版) 讀取 data/breadth.csv
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
from data_engine import load_csv # 👈 引用工具

def fetch_data(ticker: str):
    # 1. 秒讀 CSV
    history = load_csv("breadth.csv")
    if history is None: return None

    # 2. 整理數據 (CSV 裡已經有 date, value, breadth_50, breadth_200)
    # 這裡直接用 history 就可以了
    
    current_val = float(history["value"].iloc[-1])
    change = (current_val - float(history["value"].iloc[0])) / float(history["value"].iloc[0]) * 100.0

    return {"value": current_val, "change_pct": change, "history": history}

def plot_chart(df_filtered, item):
    """
    負責繪製市場寬度雙軸圖 (套用深色主題)
    """
    # 建立雙 Y 軸
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # --- Layer 1: S&P 500 (左軸，對數座標) ---
    fig.add_trace(
        go.Scatter(
            x=df_filtered["date"], y=df_filtered["value"],
            name="S&P 500 Index",
            line=dict(color='#ffffff', width=2), # 深色模式改用白色線條
            hovertemplate="Price: %{y:,.0f}<extra></extra>"
        ),
        secondary_y=False 
    )

    # --- Layer 2: 長期寬度 200MA (右軸) ---
    fig.add_trace(
        go.Scatter(
            x=df_filtered["date"], y=df_filtered["breadth_200"],
            name="% > 200MA",
            line=dict(color='#1abc9c', width=1.5),
            opacity=0.7,
            hovertemplate="200MA: %{y:.1f}%<extra></extra>"
        ),
        secondary_y=True
    )

    # --- Layer 3: 短期寬度 50MA (右軸) ---
    fig.add_trace(
        go.Scatter(
            x=df_filtered["date"], y=df_filtered["breadth_50"],
            name="% > 50MA",
            line=dict(color='#e67e22', width=1.5),
            opacity=0.6,
            hovertemplate="50MA: %{y:.1f}%<extra></extra>"
        ),
        secondary_y=True
    )

    # --- 灰色衰退區間 ---
    recessions = [
        (datetime(2007, 12, 1), datetime(2009, 6, 30)), 
        (datetime(2020, 2, 1), datetime(2020, 4, 30))
    ]
    start_date = df_filtered["date"].min()
    end_date = df_filtered["date"].max()
    
    for start_rec, end_rec in recessions:
        x0, x1 = max(start_rec, start_date), min(end_rec, end_date)
        if x0 < x1:
            fig.add_shape(type="rect", xref="x", yref="paper", x0=x0, x1=x1, y0=0, y1=1,
                          fillcolor="rgba(127, 140, 141, 0.35)", line_width=0, layer="below")

    # --- 背景區塊 (超買超賣，畫在右軸) ---
    fig.add_shape(type="rect", xref="paper", yref="y2", x0=0, x1=1, y0=0, y1=15, fillcolor="#e67e22", opacity=0.1, layer="below", line_width=0)
    fig.add_shape(type="rect", xref="paper", yref="y2", x0=0, x1=1, y0=85, y1=100, fillcolor="#1abc9c", opacity=0.1, layer="below", line_width=0)

    # --- 參考線 ---
    for y_val, color in [(15, '#e67e22'), (85, '#1abc9c'), (50, 'gray')]:
        fig.add_shape(type="line", xref="paper", yref="y2", x0=0, x1=1, y0=y_val, y1=y_val, line=dict(color=color, width=1, dash="dash"), opacity=0.5)

    # --- 動態計算對數 Y 軸範圍 ---
    log_min = np.log10(df_filtered["value"].min())
    log_max = np.log10(df_filtered["value"].max())

    # --- Layout 設定 (深色模式) ---
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(22, 27, 34, 0.9)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=40, b=40),
        height=500
    )

    # --- 軸設定 ---
    fig.update_yaxes(
        title_text="S&P 500 (Log Scale)", 
        type="log", 
        secondary_y=False,
        showgrid=True, gridcolor='#30363d',
        range=[log_min - 0.05, log_max + 0.05] 
    )

    fig.update_yaxes(
        title_text="Stocks Above MA (%)", 
        range=[0, 100], 
        secondary_y=True,
        showgrid=False
    )
    
    fig.update_xaxes(gridcolor='#30363d')

    return fig