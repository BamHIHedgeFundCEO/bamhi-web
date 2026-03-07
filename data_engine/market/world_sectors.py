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
    "🌐 全球與美國大盤 (Global & US Broad)": {
        "VT": "全球全市場", "ACWI": "全球市場(ACWI)", "ACWX": "全球(除美國)",
        "VTI": "美股全市場", "SPY": "標普500", "QQQ": "納斯達克", "DIA": "道瓊工業",
        "IWM": "羅素2000", "MDY": "中型股", 
        "XLK": "科技板塊", "XLF": "金融板塊", "XLV": "醫療保健"
    },
    "🌏 亞洲與太平洋 (Asia & Pacific)": {
        "EWA": "澳洲", "EWH": "香港", "EWM": "馬來西亞", "EWS": "新加坡",
        "EWT": "台灣", "EWY": "南韓", "IFN": "印度(IFN)", "INDA": "印度(INDA)", 
        "EWJ": "日本", "EPP": "亞洲(不含日本)", "AAXJ": "亞洲(除日本)",
        "FXI": "中國大型股(H股)", "MCHI": "中國全市場", "ASHR": "中國滬深300(A股)", 
        "KWEB": "中國互聯網", "VNM": "越南", "EIDO": "印尼", "THD": "泰國", "EPHE": "菲律賓"
    },
    "🌎 美洲與新興市場 (Americas & EM)": {
        "EEM": "新興市場", "EMXC": "新興市場(除中國)", "VWO": "新興市場(Vanguard)",
        "ILF": "拉丁美洲", "EWC": "加拿⼤", "EWW": "墨西哥", "EWZ": "巴西",
        "ARS": "阿根廷", "ARGT": "阿根廷(ARGT)", "ECH": "智利", "EPU": "秘魯", "GXG": "哥倫比亞"
    },
    "🌍 歐洲板塊 (Europe)": {
        "EFA": "歐澳遠東", "EZU": "歐元區", "IEUR": "歐洲全市場", "VGK": "歐洲(Vanguard)",
        "EWD": "瑞典", "EWG": "德國", "EWK": "比利時", "EWL": "瑞士",
        "EWN": "荷蘭", "EWO": "奧地利", "EWP": "西班牙", "EWQ": "法國", 
        "EWU": "英國", "EWI": "義大利", "GREK": "希臘", "EPOL": "波蘭"
    },
    "🐫 中東與非洲 (Middle East & Africa)": {
        "EZA": "南非", "TUR": "土耳其", "KSA": "沙烏地阿拉伯", 
        "EIS": "以色列", "AFK": "非洲全市場"
    },
    "🏢 房地產與抵押債 (Real Estate)": {
        "VNQ": "美國房地產", "VNQI": "全球房地產(除美國)", "REET": "全球REITs", 
        "REM": "抵押貸款REITs", "MBB": "MBS抵押債券"
    },
    "💰 高股息與進階收益 (Dividend & Income)": {
        "PFF": "特別股與收益", "DVY": "精選高股息", "SCHD": "美國紅利", "IDV": "國際高股息", 
        "AMLP": "能源MLP", "JEPI": "標普掩護性買權", "JEPQ": "納指掩護性買權", 
        "QQQI": "納斯達克高收益", "DIVO": "增強型股息", "QDVO": "成長與收益", 
        "QYLD": "納指Covered Call", "XYLD": "標普Covered Call"
    },
    "🛡️ 固定收益與債券 (Fixed Income)": {
        "BND": "全市場債券", "AGG": "美國總體債", "BNDX": "國際債券", 
        "TIP": "抗通膨債", "VTIP": "短期抗通膨債", 
        "TLT": "20年期公債", "TLH": "10-20年公債", "IEF": "7-10年公債", 
        "IEI": "3-7年公債", "SHY": "1-3年公債", "BILS": "3-12個月國庫券", 
        "BIL": "1-3個月國庫券", "SGOV": "0-3個月國庫券", 
        "LQD": "投資級公司債", "HYG": "高收益債", "BINC": "主動型彈性收益", 
        "JAAA": "AAA級CLO", "JBBB": "BBB級CLO", "EMB": "新興市場債", "EMHY": "新興市場高收債"
    },
    "🛢️ 大宗商品與加密資產 (Commodities & Crypto)": {
        "DBC": "廣泛大宗商品", "PDBC": "大宗商品(PDBC)", "DBB": "基本金屬", "DBA": "農產品", 
        "GLD": "黃金", "SLV": "白銀", "CPER": "銅礦指數",
        "USO": "美國原油", "UNG": "天然氣", 
        "UUP": "美元指數", "IBIT": "比特幣"
    }
}

@st.cache_data(ttl=3600)
def fetch_world_data_fallback():
    all_tickers = []
    for group in PORTFOLIO_STRUCTURE.values():
        all_tickers.extend(group.keys())
    all_tickers = list(set(all_tickers))
    try:
        import yfinance as yf
        yf_df = yf.download(all_tickers, period="2y", auto_adjust=False, progress=False)['Close']
        df = yf_df.reset_index()
        df = df.rename(columns={'Date': 'date'})
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        df = df.ffill().bfill()
        return df
    except Exception as e:
        return pd.DataFrame()

def fetch_data(ticker: str):
    file_path = "data/world_sectors.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, parse_dates=['date'])
    else:
        df = fetch_world_data_fallback()
        
    if df is None or df.empty:
        return None
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
    
    # 新增：計算進階信號所需指標 (使用 yfinance 抓取 OHLC 計算 ATR)
    import yfinance as yf
    
    flat_tickers = []
    ticker_to_name = {}
    for group, dict_ in PORTFOLIO_STRUCTURE.items():
        for t, name in dict_.items():
            flat_tickers.append(t)
            ticker_to_name[t] = name
            
    try:
        yf_df = yf.download(flat_tickers, period="1y", auto_adjust=False, progress=False)
    except Exception:
        yf_df = pd.DataFrame()
        
    calc_data = []
    if not yf_df.empty and 'Close' in yf_df.columns:
        for t in flat_tickers:
            if isinstance(yf_df.columns, pd.MultiIndex):
                if t not in yf_df['Close'].columns: continue
                close_s = yf_df['Close'][t].dropna()
                high_s = yf_df['High'][t].dropna()
                low_s = yf_df['Low'][t].dropna()
            else:
                close_s = yf_df['Close'].dropna()
                high_s = yf_df['High'].dropna()
                low_s = yf_df['Low'].dropna()
                
            if len(close_s) < 50:
                continue
                
            close_s = close_s.sort_index()
            high_s = high_s.sort_index()
            low_s = low_s.sort_index()

            curr_price = float(close_s.iloc[-1])
            ma50 = float(close_s.rolling(window=50).mean().iloc[-1])
            
            ret_20d = float((curr_price - close_s.iloc[-21]) / close_s.iloc[-21] * 100) if len(close_s) >= 21 else np.nan
            ret_10d = float((curr_price - close_s.iloc[-11]) / close_s.iloc[-11] * 100) if len(close_s) >= 11 else np.nan
            ret_3d = float((curr_price - close_s.iloc[-4]) / close_s.iloc[-4] * 100) if len(close_s) >= 4 else np.nan

            prev_close = close_s.shift(1)
            tr1 = high_s - low_s
            tr2 = (high_s - prev_close).abs()
            tr3 = (low_s - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = float(tr.rolling(window=14).mean().iloc[-1])
            atr_pct = (atr_14 / curr_price) * 100 if curr_price > 0 else np.nan

            if np.isnan(ret_20d) or np.isnan(atr_pct): continue

            calc_data.append({
                "代號": t,
                "名稱": ticker_to_name[t],
                "最新價格": curr_price,
                "ma50": ma50,
                "20D漲跌(%)": ret_20d,
                "10D漲跌(%)": ret_10d,
                "3D點火(%)": ret_3d,
                "日常波動(ATR%)": atr_pct
            })
            
    # 計算 20D PR 排名
    if calc_data:
        calc_df = pd.DataFrame(calc_data)
        calc_df['20D排名(PR)'] = calc_df['20D漲跌(%)'].rank(pct=True) * 100
        
        strategy_a, strategy_b, strategy_c = [], [], []
        
        for _, row in calc_df.iterrows():
            atr = row['日常波動(ATR%)']
            cond_a = (row['最新價格'] > row['ma50']) and (row['20D排名(PR)'] >= 70) and (abs(row['10D漲跌(%)']) < 2.0 * atr) and (row['3D點火(%)'] > 1.5 * atr)
            cond_b = (row['最新價格'] > row['ma50']) and (row['20D排名(PR)'] >= 70) and (row['10D漲跌(%)'] < -3.0 * atr) and (row['3D點火(%)'] > 1.0 * atr)
            cond_c = (row['最新價格'] < row['ma50']) and (row['20D漲跌(%)'] < 0) and (row['3D點火(%)'] < 0)

            if cond_a: strategy_a.append(row)
            if cond_b: strategy_b.append(row)
            if cond_c: strategy_c.append(row)
                
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
    
    # 動態產生 2 欄佈局以因應群組數量的變更
    for i in range(0, len(groups), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(groups):
                group = groups[i + j]
                with cols[j]:
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
        display_cols = ['代號', '名稱', '最新價格', '日常波動(ATR%)', '20D排名(PR)', '10D漲跌(%)', '3D點火(%)']
        
        def render_strategy(df_strat):
            if not df_strat.empty:
                df_display = df_strat[display_cols].copy()
                st.dataframe(
                    df_display.style.format({
                        "最新價格": "{:.2f}",
                        "日常波動(ATR%)": "{:.2f}",
                        "20D排名(PR)": "{:.2f}", 
                        "10D漲跌(%)": "{:+.2f}",
                        "3D點火(%)": "{:+.2f}"
                    }).map(_color_surfer, subset=['10D漲跌(%)', '3D點火(%)']),
                    use_container_width=True, hide_index=True
                )
            else:
                st.write("目前無標的符合此條件")

        st.subheader("🔥 策略 A：動態點火 (VCP 動態突破)")
        render_strategy(strategy_a_df)
        
        st.subheader("💎 策略 B：動態錯殺 (乖離過大反彈)")
        render_strategy(strategy_b_df)
        
        st.subheader("⚠️ 策略 C：波段破壞 (避險與資金撤出)")
        render_strategy(strategy_c_df)
                
    # 回傳空圖以符合 app.py 的架構規範
    empty_fig = go.Figure()
    empty_fig.update_layout(height=10, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return empty_fig
