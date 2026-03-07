import os

file_path = r"c:\Users\User\Desktop\bamhi-web\data_engine\market\world_sectors.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

parts = text.split("def plot_chart(df, item):")
if len(parts) < 2:
    print("Could not find plot_chart")
    exit(1)

new_code = """def plot_chart(df, item):
    if df is None or df.empty:
        return go.Figure()

    df = df.set_index('date').ffill().bfill() # 處理空值
    
    # 計算進階量化指標 (Sparklines, Ranks)
    import yfinance as yf
    calc_data = []
    
    spy_close = df["SPY"].dropna() if "SPY" in df.columns else pd.Series()
    
    for group, dict_ in PORTFOLIO_STRUCTURE.items():
        for t, name in dict_.items():
            if t not in df.columns:
                continue
            close_s = df[t].dropna()
            if len(close_s) < 130:
                continue
                
            curr_price = float(close_s.iloc[-1])
            ret_20d = float((curr_price - close_s.iloc[-21]) / close_s.iloc[-21] * 100)
            ret_60d = float((curr_price - close_s.iloc[-61]) / close_s.iloc[-61] * 100)
            ret_120d = float((curr_price - close_s.iloc[-121]) / close_s.iloc[-121] * 100)
            ret_1d = float((curr_price - close_s.iloc[-2]) / close_s.iloc[-2] * 100)
            
            hist_prices = close_s.tail(126).tolist()
            
            # RS Line & 60MA vs SPY
            is_rs_above_ma, is_rs_ma_up = False, False
            if not spy_close.empty:
                common_idx = close_s.index.intersection(spy_close.index)
                if len(common_idx) > 60:
                    rs_line = close_s.loc[common_idx] / spy_close.loc[common_idx]
                    current_rs = float(rs_line.iloc[-1])
                    rs_60ma = rs_line.rolling(window=60).mean()
                    curr_60ma = float(rs_60ma.iloc[-1])
                    prev_60ma = float(rs_60ma.iloc[-2])
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
            high_s = close_s * 1.01  # Approximation if High/Low not available in CSV seamlessly
            low_s = close_s * 0.99
            prev_close = close_s.shift(1)
            tr1 = high_s - low_s
            tr2 = (high_s - prev_close).abs()
            tr3 = (low_s - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = float(tr.rolling(window=14).mean().iloc[-1])
            atr_pct = (atr_14 / curr_price) * 100 if curr_price > 0 else 0

            calc_data.append({
                "群組": group,
                "代號": t,
                "名稱": name,
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
    if not df_calc.empty:
        df_calc['20R'] = df_calc['_ret_20d'].rank(pct=True) * 100
        df_calc['60R'] = df_calc['_ret_60d'].rank(pct=True) * 100
        df_calc['120R'] = df_calc['_ret_120d'].rank(pct=True) * 100
        df_calc['Total Rank'] = (0.2 * df_calc['20R']) + (0.4 * df_calc['60R']) + (0.4 * df_calc['120R'])
    
    tab1, tab2 = st.tabs(["🧭 全球資產動能輪動 (Heatmap)", "📊 宏觀資金邏輯與篩選 (Macro Screener)"])
    
    with tab1:
        st.markdown("### ⚙️ 動能週期設定 (Heatmap)")
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
        
        hm_data = []
        if len(df) > lookback + 1:
            curr_prices = df.iloc[-1]
            prev_prices = df.iloc[-lookback-1]
            pct_changes = (curr_prices - prev_prices) / prev_prices
            
            if lookback >= 5:
                daily_returns = df.pct_change().tail(lookback)
                period_vols = daily_returns.std()
            else:
                period_vols = None
                
            for group, tickers in PORTFOLIO_STRUCTURE.items():
                for t, name in tickers.items():
                    if t not in df.columns or pd.isna(curr_prices.get(t)): continue
                    pct_chg = pct_changes[t]
                    if lookback < 5:
                        score = pct_chg * 100
                    else:
                        vol = period_vols[t]
                        score = (pct_chg / vol) if vol > 0 else 0
                    hm_data.append({
                        "代號": t, "名稱": name, "群組": group,
                        "現價": curr_prices[t], "漲跌幅(%)": pct_chg * 100, "強弱分數": score
                    })

        result_df = pd.DataFrame(hm_data)
        if not result_df.empty:
            st.markdown("---")
            fig = px.treemap(
                result_df, path=[px.Constant("全球資產"), '群組', '代號'], values=[1] * len(result_df),
                color='強弱分數', color_continuous_scale='RdYlGn', color_continuous_midpoint=0,
                custom_data=['名稱', '現價', '漲跌幅(%)', '強弱分數'],
            )
            fig.update_traces(
                textposition='middle center',
                texttemplate="<b>%{label}</b><br>%{customdata[2]:.2f}%",
                hovertemplate="<b>%{label} (%{customdata[0]})</b><br>現價: %{customdata[1]:.2f}<br>漲跌幅: %{customdata[2]:.2f}%<br>強弱分: %{customdata[3]:.2f}<extra></extra>"
            )
            fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=550, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 📖 全球宏觀資金流向筆記")
        st.info('''
**🛡️ 宏觀大類資產輪動判斷 (資金風險偏好)**
- **攻擊型 (Cyclical & Growth)**: `SPY`, `QQQ`, `XLK` - 牛市發動機，代表市場追逐經濟成長與企業盈利。
- **防禦型 (Defensive)**: `XLV` (醫療), `XLP` (消費) - 資金轉向防守，可能有衰退疑慮。
- **避險與流動性 (Safe Haven)**: `UUP` (美元), `TLT` (長債), `GLD` (黃金) - 市場恐慌或聯準會政策轉向時的避風港。
- **通膨與實體經濟 (Inflation)**: `DBC` (原物料), `USO` (原油), `XLE` (能源) - 反映實體通膨預期。

💡 **伏擊篩選條件**：
1. **中期強勢**：`Total Rank >= 70` (資金青睞度高)
2. **回檔整理**：`14D RSI` 介於 `40~60` (強勢股良性回測)
3. **長線保護**：相對大盤 RS Line 在 `60MA` 之上且趨勢向上
''')
        st.markdown("---")
        if not df_calc.empty:
            st.markdown("### 🔥 宏觀資產伏擊清單 (Golden Macro List)")
            df_golden = df_calc[
                (df_calc['Total Rank'] >= 70) & 
                (df_calc['RS>60MA_bool'] == True) & 
                (df_calc['RSI'] >= 40) & (df_calc['RSI'] <= 60)
            ].copy()

            if df_golden.empty:
                st.write("目前無宏觀資產符合完美進場條件 (多頭回檔)。")
            else:
                df_golden_disp = df_golden[['群組', '代號', '名稱', '價格走勢', '最新價格', 'Total Rank', 'RSI', 'Is RS>60MA', '1D Return']].sort_values(by='Total Rank', ascending=False)
                st.dataframe(
                    df_golden_disp,
                    column_config={
                        "價格走勢": st.column_config.LineChartColumn("近6月走勢", y_min=0),
                        "Total Rank": st.column_config.NumberColumn("Total Rank", format="%.1f"),
                        "RSI": st.column_config.NumberColumn("14D RSI", format="%.1f"),
                        "1D Return": st.column_config.NumberColumn("日漲跌(%)", format="%.2f"),
                    },
                    use_container_width=True, hide_index=True
                )
                
            st.markdown("---")
            st.markdown("### 📊 全球主要資產動能總表")
            df_all_disp = df_calc[['群組', '代號', '名稱', '價格走勢', '最新價格', 'Total Rank', '60R', '120R', '1D Return']].sort_values(by='群組')
            st.dataframe(
                df_all_disp,
                column_config={
                    "價格走勢": st.column_config.LineChartColumn("近6月走勢", y_min=0),
                    "Total Rank": st.column_config.NumberColumn("Total Rank", format="%.1f"),
                    "60R": st.column_config.NumberColumn("中期(60R)", format="%.1f"),
                    "120R": st.column_config.NumberColumn("長期(120R)", format="%.1f"),
                    "1D Return": st.column_config.NumberColumn("日漲跌(%)", format="%.2f"),
                },
                use_container_width=True, hide_index=True, height=600
            )

    empty_fig = go.Figure()
    empty_fig.update_layout(height=10, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return empty_fig
"""

final_code = parts[0] + new_code
with open(file_path, "w", encoding="utf-8") as f:
    f.write(final_code)
print("done rewriting world sectors")
