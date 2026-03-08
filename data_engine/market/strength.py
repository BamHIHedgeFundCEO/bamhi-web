"""
data_engine/market/strength.py
負責讀取 sector_strength.csv 與 etf_holdings.json，渲染板塊熱力圖、總表與漏斗式選股面板
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.colors as pc
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
from data_engine import load_csv

BENCHMARK = "VTI"

PORTFOLIO_STRUCTURE = {
    "通訊服務 (Communication)": {
        "XLC": "通訊服務 SPDR", "SOCL": "社群媒體", "HERO": "電競與遊戲"
    },
    "非必需消費 (Discretionary)": {
        "XLY": "非必需消費 SPDR", "ITB": "房屋建築 (iShares)", "XHB": "房屋建築 (SPDR)",
        "IBUY": "線上零售 (Amplify)", "ONLN": "線上零售 (ProShares)", "PEJ": "休閒娛樂", "XRT": "零售業 SPDR" 
    },
    "必需消費 (Staples)": {
        "XLP": "必需消費 SPDR", "PBJ": "食品與飲料"
    },
    "能源 (Energy)": {
        "XLE": "能源 SPDR", "GUNR": "全球天然資源", "FCG": "天然氣", "XOP": "油氣開採",
        "ICLN": "全球乾淨能源", "QCLN": "綠能與乾淨能源", "OIH": "石油服務", "TAN": "太陽能",
        "NLR": "鈾與核能", "AMLP": "能源基礎建設"
    },
    "金融 (Financial)": {
        "XLF": "金融 SPDR", "VFH": "金融 (Vanguard)", "KRE": "區域型銀行", "KBE": "銀行業 SPDR",
        "IAI": "券商與交易所", "KIE": "保險業", "IPAY": "數位支付", "BIZD": "商業發展公司(BDC)"
    },
    "醫療保健 (Health Care)": {
        "XLV": "醫療保健 SPDR", "IBB": "生技 (iShares)", "XBI": "生技 (SPDR)", "IHI": "醫療設備",
        "IHF": "醫療服務提供商", "XHE": "醫療器材", "XPH": "製藥業", "MJ": "大麻替代收成"
    },
    "工業 (Industrial)": {
        "XLI": "工業 SPDR", "ITA": "航太與國防", "ROKT": "太空與深海探勘", "UFO": "太空產業",
        "SHLD": "國防科技", "BOTZ": "機器人與AI", "IYT": "交通運輸", "JETS": "全球航空業",
        "SNSR": "物聯網", "DRIV": "自駕與電動車", "PAVE": "美國基礎建設", "GRID": "智慧電網"
    },
    "原物料 (Materials)": {
        "XLB": "原物料 SPDR", "GDX": "金礦開採", "SIL": "白銀開採", "COPX": "銅礦開採",
        "XME": "金屬與採礦", "LIT": "鋰電池技術", "IYM": "美國基本物料", "URA": "鈾礦 ETF", "REMX": "稀土與戰略金屬"
    },
    "不動產 (Real Estate)": {
        "XLRE": "不動產 SPDR", "VNQ": "美國房地產 (Vanguard)", "VNQI": "全球房地產(除美國)",
        "REET": "全球 REITs", "REM": "抵押貸款 REITs"
    },
    "科技 (Technology)": {
        "XLK": "科技 SPDR", "CHAT": "生成式 AI 與科技", "AIQ": "AI 與科技", "IXN": "全球科技",
        "QTEC": "納斯達克 100 科技", "QTUM": "量子運算", "VGT": "資訊科技 (Vanguard)",
        "SOXX": "半導體 (iShares)", "SMH": "半導體 (VanEck)", "XSD": "半導體(等權重)",
        "IGV": "軟體服務", "FDN": "網路指數", "KWEB": "中國互聯網", "CIBR": "網路資安 (First Trust)",
        "HACK": "網路資安 (Amplify)", "SKYY": "雲端運算", "METV": "元宇宙", "FINX": "金融科技", "XT": "指數型科技"
    },
    "公用事業 (Utilities)": {
        "XLU": "公用事業 SPDR", "IGF": "全球基礎建設"
    },
    "主題型與極端動能 (Thematic & Momentum)": {
        "MEME": "迷因股", "DXYZ": "Destiny Tech100", "BLOK": "區塊鏈技術", "IPO": "新股上市 IPO",
        "MOAT": "寬護城河優勢", "MOO": "全球農業", "ARKK": "ARK 創新", "ARKW": "ARK 下一代網路",
        "ARKF": "ARK 金融科技", "ARKX": "ARK 太空探勘", "ARKQ": "ARK 自行技術與機器人",
        "ARKG": "ARK 基因革命", "WGMI": "比特幣礦企"
    }
}

NAME_MAPPING = {t: name for group in PORTFOLIO_STRUCTURE.values() for t, name in group.items()}
GROUP_MAPPING = {t: group_name for group_name, tickers in PORTFOLIO_STRUCTURE.items() for t in tickers.keys()}

def fetch_data(ticker: str):
    df = load_csv("sector_strength.csv")
    if df is None or df.empty: return None
    if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
    latest_price = float(df[BENCHMARK].iloc[-1]) if BENCHMARK in df.columns else 0.0
    return {"history": df, "value": latest_price, "change_pct": 0.0}

def _create_fig(df, tickers, title_suffix):
    fig = go.Figure()
    if BENCHMARK in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[BENCHMARK], mode='lines', name=f'{BENCHMARK} (左軸)',
            line=dict(color='white', width=4, dash='solid'), yaxis='y1', opacity=0.3
        ))
    bright_colors = pc.qualitative.Prism + pc.qualitative.Pastel + pc.qualitative.Bold
    valid_tickers = [t for t in tickers if t in df.columns]
    if not valid_tickers: return fig.update_layout(title="請選擇至少一個板塊", height=600, template="plotly_dark")

    for i, t in enumerate(valid_tickers):
        rs = df[t] / df[BENCHMARK]
        first_valid = rs.first_valid_index()
        if first_valid is not None:
            base_value = rs.loc[first_valid]
            if base_value > 0: rs = rs / base_value
        fig.add_trace(go.Scatter(x=df["date"], y=rs, mode='lines', name=f'{t} / {BENCHMARK}', line=dict(width=2, color=bright_colors[i % len(bright_colors)]), yaxis='y2'))

    recessions = [("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30")]
    shapes = [dict(type="rect", xref="x", yref="paper", x0=s, x1=e, y0=0, y1=1, fillcolor="white", opacity=0.1, layer="below", line_width=0) for s, e in recessions]
    fig.update_layout(
        title=f"相對強度分析 - {title_suffix}", hovermode="x unified", height=650, template="plotly_dark", shapes=shapes,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        yaxis=dict(title=dict(text=f"{BENCHMARK} Price", font=dict(color="rgba(255,255,255,0.5)")), side="left", showgrid=False),
        yaxis2=dict(title="Relative Strength", side="right", overlaying="y", showgrid=True, gridcolor="#333333", tickformat=".2f", dtick=0.5)
    )
    fig.update_xaxes(showgrid=False)
    return fig

@st.cache_data(ttl=86400)
def get_etf_top_holdings(ticker: str):
    file_path = "data/etf_holdings.json"
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            etf_holdings = json.load(f)
        return etf_holdings.get(ticker, [])
    except: return []

@st.cache_data(ttl=3600)
def compute_universal_metrics(close_df, high_df=None, low_df=None, benchmark="VTI"):
    if benchmark not in close_df.columns: return pd.DataFrame()
    bench_close = close_df[benchmark].dropna()
    
    calc_data = []
    for t in close_df.columns:
        if t == benchmark: continue
        c = close_df[t].dropna()
        
        common_idx = c.index.intersection(bench_close.index)
        if len(common_idx) < 130: continue
        
        c = c.loc[common_idx]
        b = bench_close.loc[common_idx]
        
        curr = float(c.iloc[-1])
        b_curr = float(b.iloc[-1])
        
        ret1 = (curr / float(c.iloc[-2]) - 1) * 100
        ret3 = (curr / float(c.iloc[-4]) - 1) * 100 
        ret5 = (curr / float(c.iloc[-6]) - 1) * 100
        ret10 = (curr / float(c.iloc[-11]) - 1) * 100 
        ret20 = (curr / float(c.iloc[-21]) - 1) * 100
        ret60 = (curr / float(c.iloc[-61]) - 1) * 100
        ret120 = (curr / float(c.iloc[-121]) - 1) * 100
        
        rel5 = ret5 - ((b_curr / float(b.iloc[-6]) - 1) * 100)
        rel20 = ret20 - ((b_curr / float(b.iloc[-21]) - 1) * 100)

        rs_line = c / b
        rs_60ma = rs_line.rolling(window=60).mean()
        is_rs_above_ma = float(rs_line.iloc[-1]) > float(rs_60ma.iloc[-1])
        is_rs_ma_up = float(rs_60ma.iloc[-1]) > float(rs_60ma.iloc[-2])

        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        rs = rs.replace([np.inf, -np.inf], 9999)
        rsi = (100 - (100 / (1 + rs))).fillna(50)
        curr_rsi = float(rsi.iloc[-1])

        if high_df is not None and low_df is not None and t in high_df.columns:
            h = high_df[t].loc[common_idx]
            l = low_df[t].loc[common_idx]
            pc = c.shift(1)
            tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
            atr_14 = float(tr.rolling(14).mean().iloc[-1])
        else:
            atr_14 = float(delta.abs().rolling(14).mean().iloc[-1])
            
        atr_pct = (atr_14 / curr) * 100 if curr > 0 else 0

        calc_data.append({
            "Ticker": t, "Name": NAME_MAPPING.get(t, t), "Group": GROUP_MAPPING.get(t, "個股"),
            "Price": curr, "1D%": ret1, "3D%": ret3, "10D%": ret10,
            "REL5": rel5, "REL20": rel20, "_ret20": ret20, "_ret60": ret60, "_ret120": ret120,
            "RSI": curr_rsi, "RS>60MA_bool": (is_rs_above_ma and is_rs_ma_up),
            "Is RS>60MA": "✅" if (is_rs_above_ma and is_rs_ma_up) else "❌",
            "ATR%": atr_pct, "Trend": c.tail(126).tolist()
        })
        
    df_res = pd.DataFrame(calc_data)
    if df_res.empty: return df_res
    
    df_res['20R'] = df_res['_ret20'].rank(pct=True) * 100
    df_res['60R'] = df_res['_ret60'].rank(pct=True) * 100
    df_res['120R'] = df_res['_ret120'].rank(pct=True) * 100
    df_res['Total Rank'] = (0.2 * df_res['20R']) + (0.4 * df_res['60R']) + (0.4 * df_res['120R'])
    
    # 自動標記符合「4大黃金條件」的標的
    conditions = (
        (df_res['Total Rank'] >= 80) & 
        (df_res['RS>60MA_bool'] == True) & 
        (df_res['RSI'] >= 45) & 
        (df_res['RSI'] <= 60) & 
        (df_res['1D%'] > 1.0 * df_res['ATR%'])
    )
    df_res['Signal'] = np.where(conditions, '🔥', '')
    
    return df_res

def _get_display_column_config():
    return {
        "Signal": st.column_config.TextColumn("訊號", help="🔥 代表符合黃金伏擊條件"),
        "Group": "所屬板塊",
        "Name": "標的名稱",
        "Trend": st.column_config.LineChartColumn("60-Day Trend", y_min=0),
        "Price": st.column_config.NumberColumn("Price", format="%.2f"),
        "1D%": st.column_config.NumberColumn("1D%", format="%+.2f"),
        "REL5": st.column_config.NumberColumn("REL5", format="%+.2f"),
        "REL20": st.column_config.NumberColumn("REL20", format="%+.2f"),
        "20R": st.column_config.NumberColumn("20R", format="%.0f"),
        "60R": st.column_config.NumberColumn("60R", format="%.0f"),
        "120R": st.column_config.NumberColumn("120R", format="%.0f"),
        "Total Rank": st.column_config.NumberColumn("Rank", format="%.1f"),
        "RSI": st.column_config.NumberColumn("14D RSI", format="%.1f"),
        "ATR%": st.column_config.NumberColumn("ATR%", format="%.2f"),
    }

def _color_surfer(val):
    if pd.isna(val): return ''
    color = '#00eb00' if val > 0 else '#ff2b2b' if val < 0 else 'grey'
    return f'color: {color}; font-weight: bold;'

def plot_chart(df_history, item_name):
    with st.spinner("正在初始化全市場動能數據..."):
        df_etf_metrics = compute_universal_metrics(df_history.set_index('date'), benchmark=BENCHMARK)

    tab1, tab2 = st.tabs(["🧭 板塊動能與多週期掃描", "🎯 Top-Down 漏斗式動能選股"])
    
    with tab1:
        with st.expander("📈 展開查看各大板塊相對強度線圖", expanded=False):
            all_flatten_tickers = [t for group in PORTFOLIO_STRUCTURE.values() for t in group.keys()]
            selected_tickers = st.multiselect("👇 選擇要觀察的板塊/主題:", options=all_flatten_tickers, default=all_flatten_tickers[:5], key="ms_all")
            st.plotly_chart(_create_fig(df_history, selected_tickers, "Market Sectors & Themes"), use_container_width=True)
            
        st.markdown("---")
        st.subheader("🟩 板塊資金動能輪動 (Momentum Heatmap)")
        lookback_options = {"1天 (1D)": 1, "3天 (3D)": 3, "1週 (5D)": 5, "1個月 (20D)": 20, "3個月 (60D)":60}
        selected_period = st.radio("⏳ 選擇觀察週期:", options=list(lookback_options.keys()), index=3, horizontal=True)
        lookback_days = lookback_options[selected_period]
        
        all_data = []
        df_sorted = df_history.sort_values("date").ffill()
        if len(df_sorted) > lookback_days + 1:
            latest = df_sorted.iloc[-1]
            prev = df_sorted.iloc[-(lookback_days + 1)]
            for group, tickers in PORTFOLIO_STRUCTURE.items():
                for t, name in tickers.items():
                    if t in df_sorted.columns and pd.notna(latest.get(t)) and prev.get(t, 0) > 0:
                        change = ((latest[t] - prev[t]) / prev[t]) * 100
                        all_data.append({"代號": t, "名稱": name, "群組": group, "現價": latest[t], "漲跌幅(%)": change, "強弱分數": change})
                        
        result_df = pd.DataFrame(all_data)
        if not result_df.empty:
            fig_hm = px.treemap(
                result_df, path=[px.Constant("全市場板塊與主題"), '群組', '代號'], values=[1] * len(result_df),
                color='強弱分數', color_continuous_scale='RdYlGn', color_continuous_midpoint=0,
                custom_data=['名稱', '現價', '漲跌幅(%)'],
            )
            fig_hm.update_traces(texttemplate="<b>%{label}</b><br>%{customdata[2]:.2f}%", hovertemplate="<b>%{label} (%{customdata[0]})</b><br>現價: %{customdata[1]:.2f}<br>漲跌幅: %{customdata[2]:.2f}%<extra></extra>")
            fig_hm.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=550, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hm, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 全球板塊與主題總覽 (Global Sectors Overview)")
        st.caption("一眼看穿大盤資金流向，包含 20R/60R/120R 排名與相對大盤表現 (REL5, REL20)。")
        
        if not df_etf_metrics.empty:
            # 加入 RSI 供 Tab 1 總覽檢視
            overview_cols = ['Group', 'Ticker', 'Name', 'Price', '1D%', 'Trend', '20R', '60R', '120R', 'Total Rank', 'REL5', 'REL20', 'RSI']
            st.dataframe(
                df_etf_metrics[overview_cols].sort_values(['Group', 'Total Rank'], ascending=[True, False]),
                column_config=_get_display_column_config(), use_container_width=True, hide_index=True, height=600
            )

        st.markdown("---")
        st.subheader("🎯 多週期量化信號掃描")
        if not df_etf_metrics.empty:
            df_strat_base = df_etf_metrics.rename(columns={
                'Ticker': '代號', 'Name': '名稱', 'Price': '最新價格',
                'ATR%': '日常波動(ATR%)', '20R': '20D排名(PR)', 
                '10D%': '10D漲跌(%)', '3D%': '3D點火(%)'
            })
            display_cols_strat = ['代號', '名稱', '最新價格', '日常波動(ATR%)', '20D排名(PR)', '10D漲跌(%)', '3D點火(%)']

            strategy_a_df = df_strat_base[(df_strat_base['Total Rank'] >= 70) & (df_strat_base['3D點火(%)'] > 1.0 * df_strat_base['日常波動(ATR%)'])]
            strategy_b_df = df_strat_base[(df_strat_base['Total Rank'] <= 30) & (df_strat_base['10D漲跌(%)'] < -2.0 * df_strat_base['日常波動(ATR%)']) & (df_strat_base['3D點火(%)'] > 0)]
            strategy_c_df = df_strat_base[(df_strat_base['Total Rank'] >= 50) & (df_strat_base['3D點火(%)'] < -1.5 * df_strat_base['日常波動(ATR%)'])]

            def render_strategy(df_strat):
                if not df_strat.empty:
                    df_display = df_strat[display_cols_strat].sort_values('3D點火(%)', ascending=False)
                    st.dataframe(
                        df_display.style.format({
                            "最新價格": "{:.2f}", "日常波動(ATR%)": "{:.2f}",
                            "20D排名(PR)": "{:.0f}", "10D漲跌(%)": "{:+.2f}", "3D點火(%)": "{:+.2f}"
                        }).map(_color_surfer, subset=['10D漲跌(%)', '3D點火(%)']),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.write("目前無標的符合此條件")

            st.markdown("##### 🔥 策略 A：動態點火 (VCP 動態突破)")
            render_strategy(strategy_a_df)
            st.markdown("##### 💎 策略 B：動態錯殺 (乖離過大反彈)")
            render_strategy(strategy_b_df)
            st.markdown("##### ⚠️ 策略 C：波段破壞 (避險與資金撤出)")
            render_strategy(strategy_c_df)

    with tab2:
        st.subheader("🎯 第一階段：強勢板塊掃描 (點擊向下鑽取)")
        st.markdown("👉 **請在下方表格最左側的「核取方塊 (Checkbox)」打勾**，即可瞬間展開該板塊內部的成分股！")
        st.caption("💡 備註：最左側帶有 🔥 代表該板塊自身今日剛好符合「完美伏擊 4 條件」。若無 🔥 屬於正常現象，代表大盤目前處於極端單邊或混沌期。")
        
        # 🌟 補上你要求的所有欄位 (包含 RSI, ATR%, Is RS>60MA)
        interactive_cols = ['Signal', 'Group', 'Ticker', 'Name', 'Price', '1D%', 'Trend', '20R', '60R', '120R', 'Total Rank', 'REL5', 'REL20', 'RSI', 'Is RS>60MA', 'ATR%']
        
        display_df = df_etf_metrics[interactive_cols].sort_values('Total Rank', ascending=False)
        
        event = st.dataframe(
            display_df,
            column_config=_get_display_column_config(),
            use_container_width=True, hide_index=True, height=350,
            on_select="rerun", selection_mode="single-row"
        )
        
        selected_etf = None
        if event.selection.rows:
            # 確保點擊到的 index 能夠完美對應排序後的 dataframe
            selected_idx = event.selection.rows[0]
            selected_etf = display_df.iloc[selected_idx]['Ticker']

        if selected_etf:
            st.markdown("---")
            st.subheader(f"🧬 第二階段：{selected_etf} 內部成分股掃描")
            
            holdings = get_etf_top_holdings(selected_etf)
            if not holdings:
                st.warning(f"⚠️ {selected_etf} 無法載入成分股，請確認 Pipeline 有成功抓取。")
            else:
                with st.spinner(f"正在即時計算 {selected_etf} 成分股的動能指標..."):
                    yf_df = yf.download(holdings + [BENCHMARK], period="1y", auto_adjust=False, progress=False)
                    if not yf_df.empty and 'Close' in yf_df.columns:
                        close_df = yf_df['Close'] if isinstance(yf_df.columns, pd.MultiIndex) else yf_df
                        high_df = yf_df['High'] if isinstance(yf_df.columns, pd.MultiIndex) else None
                        low_df = yf_df['Low'] if isinstance(yf_df.columns, pd.MultiIndex) else None
                        
                        df_comp_metrics = compute_universal_metrics(close_df, high_df, low_df, benchmark=BENCHMARK)
                        
                        if not df_comp_metrics.empty:
                            df_comp_golden = df_comp_metrics[df_comp_metrics['Signal'] == '🔥']

                            st.markdown("### 🔥 終極成分股伏擊清單 (Golden Ambush List)")
                            if df_comp_golden.empty:
                                st.info(f"目前 {selected_etf} 成分股內無標的符合完美進場條件。")
                            else:
                                st.warning("💡 紀律提醒：進場後絕對止損位設於買入價下方 2.0 * ATR。單筆持倉勿超過總資金 12.5%。")
                                # 成分股也加上完整的 R 排行與相對強弱
                                golden_cols = ['Signal', 'Ticker', 'Name', 'Trend', 'Price', '1D%', '20R', '60R', '120R', 'Total Rank', 'REL5', 'REL20', 'RSI', 'Is RS>60MA', 'ATR%']
                                st.dataframe(df_comp_golden[golden_cols].sort_values('Total Rank', ascending=False), column_config=_get_display_column_config(), use_container_width=True, hide_index=True)

                            st.markdown(f"**🔍 {selected_etf} 所有成分股總覽** (點擊欄位標題可自由排序)")
                            comp_cols = ['Signal', 'Ticker', 'Name', 'Price', '1D%', 'Trend', '20R', '60R', '120R', 'Total Rank', 'REL5', 'REL20', 'RSI', 'Is RS>60MA', 'ATR%']
                            st.dataframe(df_comp_metrics[comp_cols].sort_values('Total Rank', ascending=False), column_config=_get_display_column_config(), use_container_width=True, hide_index=True)

    empty_fig = go.Figure()
    empty_fig.update_layout(height=10, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return empty_fig