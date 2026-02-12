"""加密貨幣數據"""
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


@st.cache_data(ttl=3600)
def fetch_data(ticker: str):
    """
    抓取 1 年歷史數據。
    回傳 {"value": float, "change_pct": float, "history": DataFrame} 或 None。
    """
    try:
        end = datetime.now()
        start = end - timedelta(days=365)
        obj = yf.Ticker(ticker)
        df = obj.history(start=start, end=end, auto_adjust=True)
        if df is None or df.empty or len(df) < 2:
            return None
        close = df["Close"]
        value = float(close.iloc[-1])
        change_pct = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100.0
        history = df[["Close"]].rename(columns={"Close": "value"}).reset_index()
        history["date"] = history["Date"]
        return {"value": value, "change_pct": change_pct, "history": history}
    except Exception:
        return None
