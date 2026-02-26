"""
data_engine/market/world_sectors.py
讀取 world_sectors.csv，計算動能與波動率，並繪製熱力圖與排行榜
"""
import pandas as pd
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 定義龜族世界觀 ETF 清單結構
PORTFOLIO_STRUCTURE = {
    "🌏 亞洲與太平洋": {
        "EWA": "澳洲", "EWH": "香港", "EWM": "馬來西亞", "EWS": "新加坡",
        "EWT": "台灣", "EWY": "南韓", "IFN": "印度", "EWJ": "日本", 
        "EPP": "亞洲(不含日本)", "AAXJ": "亞洲(不含日本)"
    },
    "🌎 美洲與新興市場": {
        "ILF": "拉丁美洲", "EEM": "新興市場", 
        "EWC": "加拿⼤", "EWW": "墨西哥", "EWZ": "巴西",
        "ARS": "阿根廷", "ECH": "智利"
    },
    "🌍 歐洲板塊": {
        "EFA": "歐澳遠東", "EZU": "歐元區", "IEUR": "歐洲全市場",
        "EWD": "瑞典", "EWG": "德國", "EWK": "比利時", "EWL": "瑞士",
        "EWN": "荷蘭", "EWO": "奧地利", "EWP": "西班牙", "EWQ": "法國", 
        "EWU": "英國", "EWI": "義大利"
    },
    "🦅 美國與核心資產": {
        "SPY": "標普500", "QQQ": "納斯達克", "DIA": "道瓊工業",
        "IWM": "羅素2000", "MDY": "中型股", "VTI": "美股全市場",
        "XLK": "科技板塊", "XLF": "金融板塊", "XLV": "醫療保健",
        "GLD": "黃金", "SLV": "白銀", "USO": "石油",
        "TLT": "20年公債", "IEF": "7-10年公債", "LQD": "投資級債", "HYG": "高收債",
        "VNQ": "房地產REITs"
    }
}

def fetch_data(ticker: str):
    file_path = "data/world_sectors.csv"
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path, parse_dates=['date'])
    return {"history": df, "value": 0, "change_pct": 0}

# 負責繪製顏色的輔助函數
def _color_surfer(val):
    if pd.isna(val): return ''
    color = '#00eb00' if val > 0 else '#ff2b2b' if val < 0 else 'grey'
    return f'color: {color}; font-weight: bold;'

def plot_chart(df, item):
    if df.empty:
        return go.Figure()

    df = df.set_index('date').ffill() # 處理可能的空值
    
    # --- 1. 介面控制：週期選擇器 ---
    st.markdown("### ⚙️ 動能週期設定")
    period_mapping = {
        "1天 (1D)": 1, "3天 (3D)": 3, "1週 (5D)": 5, "2週 (10D)": 10,
        "1個月 (20D)": 20, "2個月 (40D)": 40, "3個月 (60D)": 60, "半年 (120D)": 120
    }
    
    selected_label = st.radio(
        "觀察週期 (Lookback Period)", 
        options=list(period_mapping.keys()), 
        index=4, 
        horizontal=True
    )
    lookback = period_mapping[selected_label]
    st.caption(f"當前模式：{'🛡️ 波動率調整計分 (總報酬 ÷ 期間標準差)' if lookback >= 5 else '⚡ 純價格漲跌幅'}")
    
    # --- 2. 向量化計算所有資產數據 ---
    all_data = []
    
    # 新增：計算進階信號所需指標
    # 要求至少需要 200 天歷史資料，若不足則略過
    
    calc_data = []
    
    for group, tickers in PORTFOLIO_STRUCTURE.items():
        for t, name in tickers.items():
            if t not in df.columns:
                continue
                
            series = df[t].dropna()
            if len(series) < 200:
                continue # 歷史資料不足 200 天則略過
                
            curr_price = series.iloc[-1]
            ma200 = series.rolling(window=200).mean().iloc[-1]
            
            # 計算 5D
            pct_chg_5d = (curr_price - series.iloc[-6]) / series.iloc[-6] * 100 if len(series) >= 6 else 0
            
            # 計算每日報酬率
            daily_returns = series.pct_change()
            
            # 計算 20D 波動率分數
            if len(series) >= 21:
                pct_chg_20d = (curr_price - series.iloc[-21]) / series.iloc[-21]
                vol_20d = daily_returns.tail(20).std()
                score_20d = (pct_chg_20d / vol_20d) if vol_20d > 0 else 0
            else:
                score_20d = 0
                
            # 計算 40D 波動率分數
            if len(series) >= 41:
                pct_chg_40d = (curr_price - series.iloc[-41]) / series.iloc[-41]
                vol_40d = daily_returns.tail(40).std()
                score_40d = (pct_chg_40d / vol_40d) if vol_40d > 0 else 0
            else:
                score_40d = 0
                
            calc_data.append({
                "代號": t,
                "名稱": name,
                "群組": group,
                "現價": curr_price,
                "ma200": ma200,
                "score_40d": score_40d,
                "score_20d": score_20d,
                "pct_chg_5d": pct_chg_5d,
            })
            
    # 計算 20D PR 排名
    if calc_data:
        calc_df = pd.DataFrame(calc_data)
        calc_df['pr_20d'] = calc_df['score_20d'].rank(pct=True) * 100
        
        # 產生策略信號
        strategy_a = []
        strategy_b = []
        strategy_c = []
        
        for _, row in calc_df.iterrows():
            # 策略 A：突破共振
            if row['現價'] > row['ma200'] and row['score_40d'] > 0 and row['pr_20d'] >= 75 and row['pct_chg_5d'] > 0:
                strategy_a.append(row)
            # 策略 B：錯殺反彈
            elif row['現價'] > row['ma200'] and row['score_40d'] > 0 and row['score_20d'] < -0.5 and row['pct_chg_5d'] > 1:
                strategy_b.append(row)
            # 策略 C：弱勢避險
            elif row['現價'] < row['ma200'] and row['score_40d'] <= 0 and row['score_20d'] < 0 and row['pct_chg_5d'] < 0:
                strategy_c.append(row)
                
        strategy_a_df = pd.DataFrame(strategy_a)
        strategy_b_df = pd.DataFrame(strategy_b)
        strategy_c_df = pd.DataFrame(strategy_c)
        
    if len(df) > lookback + 1:
        curr_prices = df.iloc[-1]
        prev_prices = df.iloc[-lookback-1]
        pct_changes = (curr_prices - prev_prices) / prev_prices
        
        # 計算波動率 (只取過去 lookback 天的日報酬率算標準差)
        if lookback >= 5:
            daily_returns = df.pct_change().tail(lookback)
            period_vols = daily_returns.std()
        
        # 組裝數據
        for group, tickers in PORTFOLIO_STRUCTURE.items():
            for t, name in tickers.items():
                if t not in df.columns or pd.isna(curr_prices.get(t)):
                    continue
                    
                pct_chg = pct_changes[t]
                
                if lookback < 5:
                    score = pct_chg * 100
                    vol_val = 0
                else:
                    vol = period_vols[t]
                    score = (pct_chg / vol) if vol > 0 else 0
                    vol_val = vol * (252**0.5) * 100 # 顯示用年化波動率
                
                all_data.append({
                    "代號": t,
                    "名稱": name,
                    "群組": group,
                    "現價": curr_prices[t],
                    "漲跌幅(%)": pct_chg * 100,
                    "波動率(%)": vol_val,
                    "強弱分數": score
                })

    result_df = pd.DataFrame(all_data)
    
    if result_df.empty:
        st.warning("數據量不足以計算，請確認資料是否更新。")
        return go.Figure()

    # --- 3. 繪製互動式板塊熱力圖 (Treemap) ---
    st.markdown("---")
    fig = px.treemap(
        result_df,
        path=[px.Constant("全球資產"), '群組', '代號'],
        values=[1] * len(result_df),
        color='強弱分數',
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0,
        custom_data=['名稱', '現價', '漲跌幅(%)', '強弱分數'],
    )

    fig.update_traces(
        textposition='middle center',
        texttemplate="<b>%{label}</b><br>%{customdata[2]:.2f}%",
        hovertemplate="<b>%{label} (%{customdata[0]})</b><br>現價: %{customdata[1]:.2f}<br>漲跌幅: %{customdata[2]:.2f}%<br>強弱分: %{customdata[3]:.2f}<extra></extra>"
    )

    fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=550, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 分組排行詳細數據 ---
    st.markdown("---")
    st.subheader("📋 各區域詳細強弱排行")
    
    groups = list(PORTFOLIO_STRUCTURE.keys())
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    cols = [col1, col2, col3, col4]

    for i, group in enumerate(groups):
        with cols[i]:
            st.markdown(f"#### {group}")
            group_df = result_df[result_df['群組'] == group].sort_values(by='強弱分數', ascending=False)
            display_df = group_df[['代號', '名稱', '現價', '漲跌幅(%)', '強弱分數']]
            
            st.dataframe(
                display_df.style.map(_color_surfer, subset=['漲跌幅(%)', '強弱分數'])
                .format({"現價": "{:.2f}", "漲跌幅(%)": "{:+.2f}", "強弱分數": "{:+.2f}"}),
                use_container_width=True,
                hide_index=True,
                height=400 
            )

    # --- 5. 多週期量化信號掃描 ---
    st.markdown("---")
    st.subheader("🎯 多週期量化信號掃描")
    
    if calc_data:
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown("### 🔥 突破共振 (策略 A)")
            st.caption("順勢作多：均線之上，長線動能佳，中期強勢前25%，短線點火。")
            if not strategy_a_df.empty:
                st.dataframe(
                    strategy_a_df[['代號', '名稱', '現價', 'score_40d', 'pr_20d', 'pct_chg_5d']]
                    .rename(columns={'score_40d': '40D分數', 'pr_20d': '20D排名(PR)', 'pct_chg_5d': '5D漲幅(%)'})
                    .style.format({"現價": "{:.2f}", "40D分數": "{:.2f}", "20D排名(PR)": "{:.0f}", "5D漲幅(%)": "{:+.2f}"})
                    .map(_color_surfer, subset=['5D漲幅(%)']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("目前無觸發標的")
                
        with col_b:
            st.markdown("### 💎 錯殺反彈 (策略 B)")
            st.caption("拉回低接：均線之上，長線動能佳，中期深度洗盤，短線強彈(>1%)。")
            if not strategy_b_df.empty:
                st.dataframe(
                    strategy_b_df[['代號', '名稱', '現價', 'score_40d', 'pr_20d', 'pct_chg_5d']]
                    .rename(columns={'score_40d': '40D分數', 'pr_20d': '20D排名(PR)', 'pct_chg_5d': '5D漲幅(%)'})
                    .style.format({"現價": "{:.2f}", "40D分數": "{:.2f}", "20D排名(PR)": "{:.0f}", "5D漲幅(%)": "{:+.2f}"})
                    .map(_color_surfer, subset=['5D漲幅(%)']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("目前無觸發標的")
                
        with col_c:
            st.markdown("### ⚠️ 弱勢避險 (策略 C)")
            st.caption("剔除與放空觀察：破年線，且長中短期動能皆為負值。")
            if not strategy_c_df.empty:
                st.dataframe(
                    strategy_c_df[['代號', '名稱', '現價', 'score_40d', 'pr_20d', 'pct_chg_5d']]
                    .rename(columns={'score_40d': '40D分數', 'pr_20d': '20D排名(PR)', 'pct_chg_5d': '5D漲幅(%)'})
                    .style.format({"現價": "{:.2f}", "40D分數": "{:.2f}", "20D排名(PR)": "{:.0f}", "5D漲幅(%)": "{:+.2f}"})
                    .map(_color_surfer, subset=['5D漲幅(%)']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("目前無觸發標的")
                
    # 回傳空圖以符合 app.py 的架構規範
    empty_fig = go.Figure()
    empty_fig.update_layout(height=10, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return empty_fig
