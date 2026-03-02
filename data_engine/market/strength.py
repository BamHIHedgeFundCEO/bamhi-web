"""
data_engine/market/strength.py
讀取 sector_strength.csv 並使用 Tabs 顯示大板塊與小板塊
(終極熱力圖升級版：解決 NaN 顯示問題 + 實作多週期動能選擇器)
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
    'XOP', 'XES', 'URA', 'NLR', 'TAN', 
    'GDX', 'COPX', 'LIT', 
    'XHB', 'XRT', 'XTN', 'JETS', 'PAVE', 
    'XAR', 'IHI'
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

# 內部繪圖工具 2：動態週期資金動能熱力圖 (解決 NaN 並加入 lookback)
def _create_heatmap(df, tickers, title_text, lookback_days):
    valid_tickers = [t for t in tickers if t in df.columns]
    if not valid_tickers: return go.Figure()

    # 確保資料時間順序並填補空值
    df_sorted = df.sort_values("date").dropna(subset=valid_tickers, how='all').ffill()

    # 防呆：確保歷史資料天數足夠計算 lookback
    if len(df_sorted) < lookback_days + 1: 
        fig = go.Figure()
        fig.update_layout(title="資料天數不足以計算此週期", template="plotly_dark")
        return fig
        
    latest = df_sorted.iloc[-1]
    prev = df_sorted.iloc[-(lookback_days + 1)] # 取 N 天前的值當基準
    
    labels = []
    parents = []
    values = []
    colors = []
    texts = [] # 🌟 新增：手動格式化文字，解決 NaN 顯示問題
    
    for t in valid_tickers:
        if pd.notna(latest[t]) and pd.notna(prev[t]) and prev[t] > 0:
            change = ((latest[t] - prev[t]) / prev[t]) * 100
            labels.append(t)
            parents.append("")
            values.append(1)
            colors.append(change)
            # 🌟 強制格式化為字串，加上正負號與 %
            texts.append(f"{change:+.2f}%")

    if not labels: return go.Figure()

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        text=texts, # 🌟 指定顯示這組文字
        marker=dict(
            colors=colors,
            colorscale=[[0, '#ff3333'], [0.5, '#1e1e1e'], [1.0, '#00cc66']], 
            cmid=0,
            showscale=True,
            colorbar=dict(title=f"{lookback_days}D 漲跌", ticksuffix="%")
        ),
        # 🌟 修改範本，使用我們算好的 %{text}
        texttemplate="<b>%{label}</b><br>%{text}",
        textfont=dict(size=18, color="white"),
        hovertemplate="<b>%{label}</b><br>動能漲跌: %{text}<extra></extra>"
    ))

    fig.update_layout(
        title=title_text,
        height=380,
        template="plotly_dark",
        margin=dict(t=40, l=0, r=0, b=0)
    )
    return fig

# 主函數
def plot_chart(df, item_name):
    tab1, tab2, tab3, tab4 = st.tabs(["🛡️ GICS 大板塊 (線圖)", "🚀 戰術型 Alpha (線圖)", "🔥 資金動能熱力圖", "🎯 波段量化信號掃描"])
    
    with tab1:
        st.subheader("GICS 11 大板塊相對強度")
        selected_big = st.multiselect("👇 選擇板塊:", options=SECTORS_BIG, default=SECTORS_BIG, key="ms_big")
        fig1 = _create_fig(df, selected_big, "Big Sectors")
        st.plotly_chart(fig1, use_container_width=True)
        
    with tab2:
        st.subheader("戰術型子產業相對強度")
        selected_small = st.multiselect("👇 選擇板塊:", options=SECTORS_SMALL, default=SECTORS_SMALL, key="ms_small")
        fig2 = _create_fig(df, selected_small, "Tactical Alpha")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("板塊資金動能輪動 (Momentum Heatmap)")
        st.caption("💡 切換時間週期，尋找短線資金正在流入 (綠色) 或流出 (紅色) 的板塊。")
        
        # 🌟 新增：水平時間週期選擇器
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
            horizontal=True
        )
        lookback_days = lookback_options[selected_period]
        
        fig_hm_big = _create_heatmap(df, SECTORS_BIG, f"🛡️ 大板塊 (過去 {lookback_days} 個交易日)", lookback_days)
        st.plotly_chart(fig_hm_big, use_container_width=True)
        
        st.divider()
        
        fig_hm_small = _create_heatmap(df, SECTORS_SMALL, f"🚀 戰術小板塊 (過去 {lookback_days} 個交易日)", lookback_days)
        st.plotly_chart(fig_hm_small, use_container_width=True)

    with tab4:
        st.subheader("🎯 多週期波段量化信號掃描")
        
        import yfinance as yf
        import numpy as np
        
        all_tickers = SECTORS_BIG + SECTORS_SMALL
        calc_data = []
        
        try:
            yf_df = yf.download(all_tickers, period="1y", auto_adjust=False, progress=False)
        except Exception:
            yf_df = pd.DataFrame()
            
        if not yf_df.empty and 'Close' in yf_df.columns:
            for t in all_tickers:
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
                    "名稱": t,
                    "最新價格": curr_price,
                    "ma50": ma50,
                    "20D漲跌(%)": ret_20d,
                    "10D漲跌(%)": ret_10d,
                    "3D點火(%)": ret_3d,
                    "日常波動(ATR%)": atr_pct
                })

        if calc_data:
            calc_df = pd.DataFrame(calc_data)
            calc_df['20D排名(PR)'] = calc_df['20D漲跌(%)'].rank(pct=True) * 100
            
            strat_a, strat_b, strat_c = [], [], []
            
            for _, row in calc_df.iterrows():
                atr = row['日常波動(ATR%)']
                cond_a = (row['最新價格'] > row['ma50']) and (row['20D排名(PR)'] >= 70) and (abs(row['10D漲跌(%)']) < 2.0 * atr) and (row['3D點火(%)'] > 1.5 * atr)
                cond_b = (row['最新價格'] > row['ma50']) and (row['20D排名(PR)'] >= 70) and (row['10D漲跌(%)'] < -3.0 * atr) and (row['3D點火(%)'] > 1.0 * atr)
                cond_c = (row['最新價格'] < row['ma50']) and (row['20D漲跌(%)'] < 0) and (row['3D點火(%)'] < 0)

                if cond_a: strat_a.append(row)
                if cond_b: strat_b.append(row)
                if cond_c: strat_c.append(row)
                        
            df_a = pd.DataFrame(strat_a)
            df_b = pd.DataFrame(strat_b)
            df_c = pd.DataFrame(strat_c)
            
            def _color_format_strength(val):
                if pd.isna(val): return ''
                color = '#00eb00' if val > 0 else '#ff2b2b' if val < 0 else 'grey'
                return f'color: {color}; font-weight: bold;'
                
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
                        }).map(_color_format_strength, subset=['10D漲跌(%)', '3D點火(%)']),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.write("目前無標的符合此條件")

            st.subheader("🔥 策略 A：動態點火 (VCP 動態突破)")
            render_strategy(df_a)
            
            st.subheader("💎 策略 B：動態錯殺 (乖離過大反彈)")
            render_strategy(df_b)
            
            st.subheader("⚠️ 策略 C：波段破壞 (避險與資金撤出)")
            render_strategy(df_c)

    empty_fig = go.Figure()
    empty_fig.update_layout(height=10, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return empty_fig