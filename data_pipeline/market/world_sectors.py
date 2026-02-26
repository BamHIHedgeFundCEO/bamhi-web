"""
data_pipeline/market/world_sectors.py
負責抓取龜族世界觀 (全球板塊與資產) 的日線收盤價
"""
import yfinance as yf
import pandas as pd
import os

DATA_DIR = "data"
FILE_PATH = os.path.join(DATA_DIR, "world_sectors.csv")

# 扁平化的所有 Ticker 清單
TICKERS = [
    "EWA", "EWH", "EWM", "EWS", "EWT", "EWY", "IFN", "EWJ", "EPP", "AAXJ", # 亞洲
    "ILF", "EEM", "EWC", "EWW", "EWZ", "ARS", "ECH",                       # 美洲與新興
    "EFA", "EZU", "IEUR", "EWD", "EWG", "EWK", "EWL", "EWN", "EWO", "EWP", "EWQ", "EWU", "EWI", # 歐洲
    "SPY", "QQQ", "DIA", "IWM", "MDY", "VTI", "XLK", "XLF", "XLV", "GLD", "SLV", "USO", "TLT", "IEF", "LQD", "HYG", "VNQ" # 美國與核心
]

def update():
    print("   ↳ 🐢 [World Sectors] 正在更新龜族世界觀資產報價...")
    try:
        # 抓取過去 1 年的資料，確保有足夠的日數可以計算 120D 波動率
        df = yf.download(TICKERS, period="1y", progress=False, auto_adjust=False)['Close']
        
        # 整理格式
        df = df.reset_index()
        # 統一欄位名稱，並移除時區
        df = df.rename(columns={'Date': 'date'})
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        df.to_csv(FILE_PATH, index=False)
        print(f"   ✅ [World Sectors] 儲存成功，共 {len(df.columns)-1} 檔資產。")
        
    except Exception as e:
        print(f"      [Error] World Sectors 下載失敗: {e}")
