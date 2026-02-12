"""利率數據：10Y、2Y、10-2 Spread（FRED）與繪圖邏輯"""
import streamlit as st
import pandas as pd
import datetime as dt
from pandas_datareader import data as web
import plotly.graph_objects as go # 新增：為了畫圖
from datetime import datetime     # 新增：為了處理日期

@st.cache_data(ttl=3600)
def fetch_data(ticker: str):
    """(維持原樣) 抓取數據"""
    try:
        start_date = dt.datetime(1980, 1, 1)
        end_date = dt.datetime.now()

        df = web.DataReader(["DGS10", "DGS2"], "fred", start_date, end_date)
        df["Spread"] = df["DGS10"] - df["DGS2"]
        df = df.dropna()

        if df.empty:
            return None

        if ticker == "DGS10":
            series = df["DGS10"]
        elif ticker == "DGS2":
            series = df["DGS2"]
        elif ticker == "SPREAD_10_2":
            series = df["Spread"]
        else:
            return None

        history = df[["DGS10", "DGS2", "Spread"]].copy()
        history["date"] = history.index
        history["value"] = series.values
        history = history.reset_index(drop=True)

        value = float(series.iloc[-1])
        change_pct = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100.0

        return {"value": value, "change_pct": change_pct, "history": history}
    except Exception:
        return None


def plot_rates_chart(df, item, range_option):
    """
    (新增) 專門處理利率圖表的繪製邏輯
    包含：區間篩選、衰退區塊繪製、Spread 雙軸圖處理
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    
    # 1. 處理時間區間篩選
    end = df["date"].max()
    if range_option == "All":
        start = df["date"].min()
    elif range_option == "6m":
        start = end - pd.DateOffset(months=6)
    elif range_option == "YTD":
        start = datetime(end.year, 1, 1)
    elif range_option == "1Y":
        start = end - pd.DateOffset(years=1)
    elif range_option == "3Y":
        start = end - pd.DateOffset(years=3)
    elif range_option == "5Y":
        start = end - pd.DateOffset(years=5)
    else:  # "10Y"
        start = end - pd.DateOffset(years=10)

    df_range = df[(df["date"] >= start) & (df["date"] <= end)]

    # 2. 定義衰退區塊 (維持你的設定)
    recessions = [
        (datetime(1990, 7, 1), datetime(1991, 3, 31)),
        (datetime(2001, 3, 1), datetime(2001, 11, 30)),
        (datetime(2007, 12, 1), datetime(2009, 6, 30)),
        (datetime(2020, 2, 1), datetime(2020, 4, 30)),
    ]

    # 3. 判斷繪圖模式：Spread (雙軸) vs 單線圖
    
    # === Spread 圖：三線 + 右軸利差 + 灰色衰退區 ===
    if item.get("id") == "SPREAD_10_2" and all(col in df_range.columns for col in ["DGS10", "DGS2", "Spread"]):
        fig = go.Figure()
        # 10Y（藍）、2Y（紅） - 左軸
        fig.add_trace(go.Scatter(x=df_range["date"], y=df_range["DGS10"], mode="lines", name="10Y Yield (L)", line=dict(color="#2980b9", width=1.5), yaxis="y1"))
        fig.add_trace(go.Scatter(x=df_range["date"], y=df_range["DGS2"], mode="lines", name="2Y Yield (L)", line=dict(color="#e74c3c", width=1.5), yaxis="y1"))

        # 利差（黃色區域）- 右軸
        fig.add_trace(go.Scatter(
            x=df_range["date"], y=df_range["Spread"], mode="lines", name="10Y-2Y Spread (R)",
            line=dict(color="#f1c40f", width=0.5), fill="tozeroy", fillcolor="rgba(241, 196, 15, 0.35)", yaxis="y2"
        ))

        # 設定 Layout (雙軸)
        yaxis_config = dict(title="Yield (%)", gridcolor="#30363d", showgrid=True)
        yaxis2_config = dict(title="Spread (%)", overlaying="y", side="right", showgrid=False)
        legend_config = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)

    # === 10Y / 2Y 單指標圖 ===
    else:
        if item.get("id") == "DGS10":
            series = df_range["DGS10"] if "DGS10" in df_range.columns else df_range["value"]
            color, name = "#2980b9", "10Y Yield"
        elif item.get("id") == "DGS2":
            series = df_range["DGS2"] if "DGS2" in df_range.columns else df_range["value"]
            color, name = "#e74c3c", "2Y Yield"
        else:
            series = df_range["value"]
            color, name = "#58a6ff", item["name"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_range["date"], y=series, mode="lines", name=name,
            line=dict(color=color, width=1.8), fill="tozeroy", fillcolor="rgba(88, 166, 255, 0.10)"
        ))

        # 設定 Layout (單軸)
        yaxis_config = dict(title="Yield (%)", gridcolor="#30363d", showgrid=True)
        yaxis2_config = None # 單軸沒有 yaxis2
        legend_config = dict()

    # 4. 加入衰退區塊 (共用邏輯)
    for start_rec, end_rec in recessions:
        x0 = max(start_rec, start)
        x1 = min(end_rec, end)
        if x0 >= x1: continue
        fig.add_shape(type="rect", xref="x", yref="paper", x0=x0, x1=x1, y0=0, y1=1,
                      fillcolor="rgba(127, 140, 141, 0.35)", line=dict(width=0), layer="below")

    # 5. 最終樣式設定 (共用邏輯)
    layout_args = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(22, 27, 34, 0.9)",
        font=dict(color="#c9d1d9", size=12),
        margin=dict(l=50, r=30, t=40, b=50),
        xaxis=dict(gridcolor="#30363d", showgrid=True),
        yaxis=yaxis_config,
        hovermode="x unified",
        height=450 if item.get("id") == "SPREAD_10_2" else 400, # Spread 圖稍微高一點
    )
    
    if yaxis2_config:
        layout_args['yaxis2'] = yaxis2_config
    if legend_config:
        layout_args['legend'] = legend_config
        
    fig.update_layout(**layout_args)
    
    return fig