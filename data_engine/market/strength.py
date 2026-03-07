"""
data_engine/market/strength.py
讀取 sector_strength.csv 並使用 Tabs 顯示大板塊與小板塊
(終極熱力圖升級版：解決 NaN 顯示問題 + 實作多週期動能選擇器)
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.colors as pc
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from data_engine import load_csv

# 定義清單
BENCHMARK = "VTI"

PORTFOLIO_STRUCTURE = {
    "通訊服務 (Communication)": {
        "XLC": "通訊服務 SPDR",
        "SOCL": "社群媒體",
        "HERO": "電競與遊戲"
    },
    "非必需消費 (Discretionary)": {
        "XLY": "非必需消費 SPDR",
        "ITB": "房屋建築 (iShares)",
        "XHB": "房屋建築 (SPDR)",
        "IBUY": "線上零售 (Amplify)",
        "ONLN": "線上零售 (ProShares)",
        "PEJ": "休閒娛樂",
        "XRT": "零售業 SPDR" 
    },
    "必需消費 (Staples)": {
        "XLP": "必需消費 SPDR",
        "PBJ": "食品與飲料"
    },
    "能源 (Energy)": {
        "XLE": "能源 SPDR",
        "GUNR": "全球天然資源",
        "FCG": "天然氣",
        "XOP": "油氣開採",
        "ICLN": "全球乾淨能源",
        "QCLN": "綠能與乾淨能源",
        "OIH": "石油服務",
        "TAN": "太陽能",
        "NLR": "鈾與核能",
        "AMLP": "能源基礎建設"
    },
    "金融 (Financial)": {
        "XLF": "金融 SPDR",
        "VFH": "金融 (Vanguard)",
        "KRE": "區域型銀行",
        "KBE": "銀行業 SPDR",
        "IAI": "券商與交易所",
        "KIE": "保險業",
        "IPAY": "數位支付",
        "BIZD": "商業發展公司(BDC)"
    },
    "醫療保健 (Health Care)": {
        "XLV": "醫療保健 SPDR",
        "IBB": "生技 (iShares)",
        "XBI": "生技 (SPDR)",
        "IHI": "醫療設備",
        "IHF": "醫療服務提供商",
        "XHE": "醫療器材",
        "XPH": "製藥業",
        "MJ": "大麻替代收成"
    },
    "工業 (Industrial)": {
        "XLI": "工業 SPDR",
        "ITA": "航太與國防",
        "ROKT": "太空與深海探勘",
        "UFO": "太空產業",
        "SHLD": "國防科技",
        "BOTZ": "機器人與AI",
        "IYT": "交通運輸",
        "JETS": "全球航空業",
        "SNSR": "物聯網",
        "DRIV": "自駕與電動車",
        "PAVE": "美國基礎建設",
        "GRID": "智慧電網"
    },
    "原物料 (Materials)": {
        "XLB": "原物料 SPDR",
        "GDX": "金礦開採",
        "SIL": "白銀開採",
        "COPX": "銅礦開採",
        "XME": "金屬與採礦",
        "LIT": "鋰電池技術",
        "IYM": "美國基本物料",
        "URA": "鈾礦 ETF",
        "REMX": "稀土與戰略金屬"
    },
    "不動產 (Real Estate)": {
        "XLRE": "不動產 SPDR",
        "VNQ": "美國房地產 (Vanguard)",
        "VNQI": "全球房地產(除美國)",
        "REET": "全球 REITs",
        "REM": "抵押貸款 REITs"
    },
    "科技 (Technology)": {
        "XLK": "科技 SPDR",
        "CHAT": "生成式 AI 與科技",
        "AIQ": "AI 與科技",
        "IXN": "全球科技",
        "QTEC": "納斯達克 100 科技",
        "QTUM": "量子運算",
        "VGT": "資訊科技 (Vanguard)",
        "SOXX": "半導體 (iShares)",
        "SMH": "半導體 (VanEck)",
        "XSD": "半導體(等權重)",
        "IGV": "軟體服務",
        "FDN": "網路指數",
        "KWEB": "中國互聯網",
        "CIBR": "網路資安 (First Trust)",
        "HACK": "網路資安 (Amplify)",
        "SKYY": "雲端運算",
        "METV": "元宇宙",
        "FINX": "金融科技",
        "XT": "指數型科技"
    },
    "公用事業 (Utilities)": {
        "XLU": "公用事業 SPDR",
        "IGF": "全球基礎建設"
    },
    "主題型與極端動能 (Thematic & Momentum)": {
        "MEME": "迷因股",
        "DXYZ": "Destiny Tech100",
        "BLOK": "區塊鏈技術",
        "IPO": "新股上市 IPO",
        "MOAT": "寬護城河優勢",
        "MOO": "全球農業",
        "ARKK": "ARK 創新",
        "ARKW": "ARK 下一代網路",
        "ARKF": "ARK 金融科技",
        "ARKX": "ARK 太空探勘",
        "ARKQ": "ARK 自行技術與機器人",
        "ARKG": "ARK 基因革命",
        "WGMI": "比特幣礦企"
    }
}

@st.cache_data(ttl=3600)
def fetch_data_fallback():
    all_tickers = [BENCHMARK]
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
    df = load_csv("sector_strength.csv")
    if df is None or df.empty or BENCHMARK not in df.columns:
        df = fetch_data_fallback()
        
    if df is None or df.empty:
        return None
        
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

# 內部繪圖工具 1：相對強度線圖
def _create_fig(df, tickers, title_suffix):
    fig = go.Figure()

    if BENCHMARK in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[BENCHMARK],
            mode='lines', name=f'{BENCHMARK} (左軸)',
            line=dict(color='white', width=4, dash='solid'),
            yaxis='y1', opacity=0.3
        ))

    bright_colors = pc.qualitative.Prism + pc.qualitative.Pastel + pc.qualitative.Bold
    valid_tickers = [t for t in tickers if t in df.columns]
    
    if not valid_tickers:
        fig.update_layout(title="請選擇至少一個板塊", height=600, template="plotly_dark")
        return fig

    for i, t in enumerate(valid_tickers):
        rs = df[t] / df[BENCHMARK]
        first_valid = rs.first_valid_index()
        if first_valid is not None:
            base_value = rs.loc[first_valid]
            if base_value > 0:
                rs = rs / base_value

        line_color = bright_colors[i % len(bright_colors)]

        fig.add_trace(go.Scatter(
            x=df["date"], y=rs,
            mode='lines', 
            name=f'{t} / {BENCHMARK}',
            line=dict(width=2, color=line_color),
            yaxis='y2',
        ))

    recessions = [("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30")]
    shapes = [dict(type="rect", xref="x", yref="paper", x0=s, x1=e, y0=0, y1=1, fillcolor="white", opacity=0.1, layer="below", line_width=0) for s, e in recessions]

    fig.update_layout(
        title=f"相對強度分析 - {title_suffix}",
        hovermode="x unified",
        height=650,
        template="plotly_dark",
        shapes=shapes,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        yaxis=dict(
            title=dict(text=f"{BENCHMARK} Price", font=dict(color="rgba(255,255,255,0.5)")),
            side="left", showgrid=False, tickfont=dict(color="rgba(255,255,255,0.5)")
        ),
        yaxis2=dict(
            title="Relative Strength",
            side="right", overlaying="y", showgrid=True, gridcolor="#333333",
            tickformat=".2f", dtick=0.5, hoverformat=".6f"
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
            bgcolor="#333333", activecolor="#00d2ff", x=0, y=1.05
        )
    )
    return fig

@st.cache_data(ttl=86400)
def get_etf_top_holdings(ticker: str):
    """從 data/etf_holdings.json 中讀取預先由 Pipeline 下載的 ETF 成分股資料"""
    import json
    import os
    
    file_path = "data/etf_holdings.json"
    if not os.path.exists(file_path):
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            etf_holdings = json.load(f)
            
        return etf_holdings.get(ticker, [])
    except Exception as e:
        return []

def _calculate_quant_metrics(target_tickers, etf_ticker, benchmark="SPY"):
    """給定目標名單，計算所需的量化指標"""
    all_tickers = list(set(target_tickers + [etf_ticker, benchmark]))
    try:
        yf_df = yf.download(all_tickers, period="1y", auto_adjust=False, progress=False)
    except Exception:
        return pd.DataFrame()

    if yf_df.empty or 'Close' not in yf_df.columns:
        return pd.DataFrame()

    calc_data = []

    # 若抓下來只有一檔，格式不是 MultiIndex
    is_multi = isinstance(yf_df.columns, pd.MultiIndex)
    
    # 用來取得某檔的收盤價/高/低
    def get_series(t, col):
        if is_multi:
            if t in yf_df[col].columns: return yf_df[col][t].dropna()
        else:
            if t == all_tickers[0]: return yf_df[col].dropna()
        return pd.Series()

    spy_close = get_series(benchmark, 'Close')
    if spy_close.empty: return pd.DataFrame()

    for t in target_tickers:
        close_s = get_series(t, 'Close')
        high_s = get_series(t, 'High')
        low_s = get_series(t, 'Low')

        if len(close_s) < 130: continue

        close_s = close_s.sort_index()
        high_s = high_s.sort_index()
        low_s = low_s.sort_index()

        curr_price = float(close_s.iloc[-1])
        
        # 區間報酬
        ret_20d = float((curr_price - close_s.iloc[-21]) / close_s.iloc[-21] * 100)
        ret_60d = float((curr_price - close_s.iloc[-61]) / close_s.iloc[-61] * 100)
        ret_120d = float((curr_price - close_s.iloc[-121]) / close_s.iloc[-121] * 100)
        ret_1d = float((curr_price - close_s.iloc[-2]) / close_s.iloc[-2] * 100)

        # 歷史走勢 (Sparkline) - 近半年 (大約 126 個交易日)
        hist_prices = close_s.tail(126).tolist()

        # RS Line & 60MA
        common_idx = close_s.index.intersection(spy_close.index)
        rs_line = close_s.loc[common_idx] / spy_close.loc[common_idx]
        current_rs = float(rs_line.iloc[-1]) if len(rs_line) > 0 else 0
        
        rs_60ma = rs_line.rolling(window=60).mean()
        curr_60ma = float(rs_60ma.iloc[-1]) if len(rs_60ma) >= 60 else 0
        prev_60ma = float(rs_60ma.iloc[-2]) if len(rs_60ma) >= 60 else 0
        is_rs_above_ma = current_rs > curr_60ma
        is_rs_ma_up = curr_60ma > prev_60ma

        # 14 Day RSI
        delta = close_s.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1]) if len(rsi) >= 14 else 50
        
        # 14d ATR
        prev_close = close_s.shift(1)
        tr1 = high_s - low_s
        tr2 = (high_s - prev_close).abs()
        tr3 = (low_s - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_14 = float(tr.rolling(window=14).mean().iloc[-1])
        atr_pct = (atr_14 / curr_price) * 100 if curr_price > 0 else 0

        calc_data.append({
            "代號": t,
            "價格走勢": hist_prices,
            "最新價格": curr_price,
            "1D Return": ret_1d,
            "ATR%": atr_pct,
            "RSI": current_rsi,
            "Is RS>60MA": "✅" if (is_rs_above_ma and is_rs_ma_up) else "❌",
            "RS>60MA_bool": (is_rs_above_ma and is_rs_ma_up),
            "_ret_20d": ret_20d,
            "_ret_60d": ret_60d,
            "_ret_120d": ret_120d,
        })
        
    df_calc = pd.DataFrame(calc_data)
    if df_calc.empty: return df_calc
    
    # 計算 Percentile Rank 與 Total Rank
    df_calc['20R'] = df_calc['_ret_20d'].rank(pct=True) * 100
    df_calc['60R'] = df_calc['_ret_60d'].rank(pct=True) * 100
    df_calc['120R'] = df_calc['_ret_120d'].rank(pct=True) * 100
    df_calc['Total Rank'] = (0.2 * df_calc['20R']) + (0.4 * df_calc['60R']) + (0.4 * df_calc['120R'])
    
    return df_calc

# 負責繪製顏色的輔助函數
def _color_surfer(val):
    if pd.isna(val): return ''
    color = '#00eb00' if val > 0 else '#ff2b2b' if val < 0 else 'grey'
    return f'color: {color}; font-weight: bold;'

# 主函數
def plot_chart(df, item_name):
    # 改為 2 個主要的 Tabs
    tab1, tab2 = st.tabs(["🧭 板塊動能與多週期掃描", "🎯 Top-Down 漏斗式動能選股"])
    
    with tab1:
        # 原本 Heatmap 前的 Line chart 合併進來
        with st.expander("📈 展開查看各大板塊相對強度線圖", expanded=False):
            all_flatten_tickers = []
            for group, tickers in PORTFOLIO_STRUCTURE.items():
                all_flatten_tickers.extend(list(tickers.keys()))
            default_selected = all_flatten_tickers[:5] if len(all_flatten_tickers) >= 5 else all_flatten_tickers
            selected_tickers = st.multiselect("👇 選擇要觀察的板塊/主題:", options=all_flatten_tickers, default=default_selected, key="ms_all")
            fig1 = _create_fig(df, selected_tickers, "Market Sectors & Themes")
            st.plotly_chart(fig1, use_container_width=True)
            
        st.markdown("---")
        st.subheader("板塊資金動能輪動 (Momentum Heatmap)")
        st.caption("💡 切換時間週期，尋找短線資金正在流入 (綠色) 或流出 (紅色) 的板塊。")
        
        # 水平時間週期選擇器
        lookback_options = {
            "1天 (1D)": 1, 
            "3天 (3D)": 3, 
            "1週 (5D)": 5, 
            "2週 (10D)": 10, 
            "1個月 (20D)": 20,
            "2個月 (40D)":40,
            "3個月 (60D)":60,
        }
        selected_period = st.radio(
            "⏳ 選擇觀察週期:", 
            options=list(lookback_options.keys()), 
            index=4,
            horizontal=True
        )
        lookback_days = lookback_options[selected_period]
        
        all_data = []
        # 確保資料時間順序並填補空值
        df_sorted = df.sort_values("date").ffill()
        
        if len(df_sorted) > lookback_days + 1:
            latest = df_sorted.iloc[-1]
            prev = df_sorted.iloc[-(lookback_days + 1)]
            
            for group, tickers in PORTFOLIO_STRUCTURE.items():
                for t, name in tickers.items():
                    if t in df_sorted.columns and pd.notna(latest.get(t)) and pd.notna(prev.get(t)) and prev.get(t) > 0:
                        change = ((latest[t] - prev[t]) / prev[t]) * 100
                        all_data.append({
                            "代號": t,
                            "名稱": name,
                            "群組": group,
                            "現價": latest[t],
                            "漲跌幅(%)": change,
                            "強弱分數": change  # 使用漲跌幅作為分數
                        })
                        
        result_df = pd.DataFrame(all_data)
        
        if result_df.empty:
            st.warning("資料天數不足以計算此週期。")
        else:
            import plotly.express as px
            # 繪製分類 Treemap
            fig_hm = px.treemap(
                result_df,
                path=[px.Constant("全市場板塊與主題"), '群組', '代號'],
                values=[1] * len(result_df),
                color='強弱分數',
                color_continuous_scale='RdYlGn',
                color_continuous_midpoint=0,
                custom_data=['名稱', '現價', '漲跌幅(%)', '強弱分數'],
            )

            fig_hm.update_traces(
                textposition='middle center',
                texttemplate="<b>%{label}</b><br>%{customdata[2]:.2f}%",
                hovertemplate="<b>%{label} (%{customdata[0]})</b><br>現價: %{customdata[1]:.2f}<br>漲跌幅: %{customdata[2]:.2f}%<extra></extra>"
            )

            fig_hm.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=550, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hm, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📋 各板塊詳細強弱排行")
            
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
                            display_df = group_df[['代號', '名稱', '現價', '漲跌幅(%)']]
                            
                            st.dataframe(
                                display_df.style.map(_color_surfer, subset=['漲跌幅(%)'])
                                .format({"現價": "{:.2f}", "漲跌幅(%)": "{:+.2f}"}),
                                use_container_width=True,
                                hide_index=True,
                                height=400 
                            )

    with tab2:
        st.subheader("🎯 Top-Down 漏斗式動能選股")
        st.markdown("結合 **板塊動能** 與 **內部相對強勢** 進行雙重篩選，抓取處於長線強勢回檔，並發生短線乖離點火的伏擊機會。")
        
        flat_tickers = []
        etf_options = {}
        for group, dict_ in PORTFOLIO_STRUCTURE.items():
            for t, name in dict_.items():
                flat_tickers.append(t)
                etf_options[t] = f"{t} ({name})"
                
        # 建立上方終極目標清單框架區塊 (目前此設計需要在背景算完全部 ETF，我們這裡調整成先選定特定 ETF 再幫用戶算該 ETF 的 Golden List 來最佳化速度，或是預設不主動算全部)
        st.markdown("#### 1. 選擇要掃描的板塊 ETF (Top-Down Drill)")
        selected_etf = st.selectbox(
            "👇 選擇板塊 ETF:", 
            options=flat_tickers, 
            format_func=lambda x: etf_options[x]
        )
        
        if selected_etf:
            st.info(f"正在分析 {selected_etf} 的內部結構與搜尋伏擊目標...")
            
            # 使用 Playwright 獲取前 15 大持股
            holdings = get_etf_top_holdings(selected_etf)
            if not holdings:
                st.warning(f"無法獲取 {selected_etf} 的成分股資料，請稍後再試。")
            else:
                st.success(f"成功抓取 {selected_etf} 前 {len(holdings)} 大成分股。")
                
                # 計算量化指標
                df_calc = _calculate_quant_metrics(holdings, selected_etf)
                
                if not df_calc.empty:
                    # 第三步：過濾出黃金伏擊清單
                    df_golden = df_calc[
                        (df_calc['Total Rank'] >= 80) & 
                        (df_calc['RS>60MA_bool'] == True) & 
                        (df_calc['RSI'] >= 45) & (df_calc['RSI'] <= 60) &
                        (df_calc['1D Return'] > 1.0 * df_calc['ATR%'])
                    ].copy()

                    st.markdown("### 🔥 今日終極伏擊清單 (Golden Ambush List)")
                    if df_golden.empty:
                        st.write("目前該板塊內無標的符合完美進場條件。")
                    else:
                        st.info("💡 紀律提醒：進場後絕對止損位設於買入價下方 2.0 * ATR。單筆持倉勿超過總資金 12.5%。")
                        
                        df_golden_disp = df_golden[['代號', '價格走勢', '最新價格', 'Total Rank', 'RSI', 'Is RS>60MA', '1D Return', 'ATR%']].sort_values(by='Total Rank', ascending=False)
                        st.dataframe(
                            df_golden_disp,
                            column_config={
                                "價格走勢": st.column_config.LineChartColumn("近6月走勢", y_min=0),
                                "Total Rank": st.column_config.NumberColumn("Total Rank", format="%.1f"),
                                "RSI": st.column_config.NumberColumn("14D RSI", format="%.1f"),
                                "1D Return": st.column_config.NumberColumn("日漲跌(%)", format="%.2f"),
                                "ATR%": st.column_config.NumberColumn("ATR%", format="%.2f"),
                            },
                            use_container_width=True, hide_index=True
                        )

                    st.markdown("---")
                    st.markdown("#### 🔍 此板塊所有成分股總覽")
                    df_all_disp = df_calc[['代號', '價格走勢', '最新價格', 'Total Rank', 'RSI', 'Is RS>60MA', '1D Return']].sort_values(by='Total Rank', ascending=False)
                    st.dataframe(
                        df_all_disp,
                        column_config={
                            "價格走勢": st.column_config.LineChartColumn("近6月走勢", y_min=0),
                            "Total Rank": st.column_config.NumberColumn("Total Rank", format="%.1f"),
                            "RSI": st.column_config.NumberColumn("14D RSI", format="%.1f"),
                            "1D Return": st.column_config.NumberColumn("日漲跌(%)", format="%.2f"),
                        },
                        use_container_width=True, hide_index=True
                    )

    empty_fig = go.Figure()
    empty_fig.update_layout(height=10, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return empty_fig