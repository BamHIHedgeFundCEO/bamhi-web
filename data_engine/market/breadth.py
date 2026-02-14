"""S&P 500 市場寬度數據引擎"""
import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gc
from datetime import datetime

@st.cache_data(ttl=86400) # 快取 24 小時，因為算 500 檔股票很耗時
def fetch_data(ticker: str):
    """
    抓取 S&P 500 成分股，計算市場寬度，並與 S&P 500 大盤指數合併
    """
    try:
        START_DATE = "2007-01-01" 
        BATCH_SIZE = 50 

        # 1. 取得 S&P 500 成分股清單
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        tables = pd.read_html(StringIO(r.text), header=0)
        tickers = tables[0]['Symbol'].tolist()
        tickers = [t.replace('.', '-') for t in tickers]

        # 2. 批量下載資料
        data = yf.download(tickers, start=START_DATE, auto_adjust=True, threads=True, progress=False)['Close']
        data = data.dropna(axis=1, how='all').ffill().astype('float32')

        # 3. 分批計算市場寬度
        numerator_50 = pd.Series(0, index=data.index, dtype='float32')
        numerator_200 = pd.Series(0, index=data.index, dtype='float32')
        denominator = pd.Series(0, index=data.index, dtype='float32')

        all_cols = data.columns
        total_stocks = len(all_cols)

        for i in range(0, total_stocks, BATCH_SIZE):
            batch_cols = all_cols[i : i + BATCH_SIZE]
            batch_data = data[batch_cols]
            
            ma50_batch = batch_data.rolling(window=50).mean()
            ma200_batch = batch_data.rolling(window=200).mean()
            
            above_50_batch = (batch_data > ma50_batch).astype('float32')
            above_200_batch = (batch_data > ma200_batch).astype('float32')
            valid_batch = batch_data.notna().astype('float32')
            
            numerator_50 = numerator_50.add(above_50_batch.sum(axis=1).fillna(0), fill_value=0)
            numerator_200 = numerator_200.add(above_200_batch.sum(axis=1).fillna(0), fill_value=0)
            denominator = denominator.add(valid_batch.sum(axis=1).fillna(0), fill_value=0)
            
            del batch_data, ma50_batch, ma200_batch, above_50_batch, above_200_batch, valid_batch
            gc.collect()

        breadth_50 = (numerator_50 / denominator).fillna(0) * 100
        breadth_200 = (numerator_200 / denominator).fillna(0) * 100
        
        # 在這裡先算好平滑值，避免切區間後產生 NaN
        breadth_50_smooth = breadth_50.rolling(window=3).mean()

        del data, numerator_50, numerator_200, denominator
        gc.collect()

        # 4. 下載 S&P 500 大盤
        sp500_df = yf.download("^GSPC", start=START_DATE, auto_adjust=True, progress=False)
        sp500 = sp500_df['Close'].squeeze() if 'Close' in sp500_df.columns else sp500_df.squeeze()

        # 5. 合併成一個 DataFrame
        history = pd.DataFrame({
            "value": sp500,             # 大盤價格 (作為主 value)
            "breadth_200": breadth_200, # 200MA 寬度
            "breadth_50": breadth_50_smooth # 50MA 寬度 (已平滑)
        }).dropna().reset_index()
        
        history["date"] = history["Date"]
        
        # 計算最新報價與漲跌幅 (針對大盤)
        current_value = float(history["value"].iloc[-1])
        change_pct = (history["value"].iloc[-1] - history["value"].iloc[0]) / history["value"].iloc[0] * 100.0

        return {"value": current_value, "change_pct": change_pct, "history": history}

    except Exception as e:
        print(f"Error fetching breadth data: {e}")
        return None

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