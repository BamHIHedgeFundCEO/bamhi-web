"""
data_pipeline/market/strength.py
負責抓取美股板塊資料 (終極修正版：單檔下載確保還原權值)
"""
import yfinance as yf
import pandas as pd
import os
import time

# 定義清單
BENCHMARK = "VTI"

SECTORS_BIG = [
    'VGT', 'VHT', 'VFH', 'VCR', 'VOX', 'VIS', 
    'VDC', 'VDE', 'VPU', 'VAW', 'VNQ'
]

SECTORS_SMALL = [
    'SMH', 'IGV', 'CIBR', 'SKYY', 'FINX', 
    'XBI', 'UFO', 'ROBO', 
    'XOP', 'OIH', 'URA', 'NLR', 'TAN', 
    'GDX', 'COPX', 'LIT', 
    'XHB', 'XRT', 'XTN', 'JETS', 'PAVE', 
    'XAR', 'IHI'
]

def update():
    print("   ↳ 💪 [Sector Strength] 正在下載資料 (慢速穩定模式)...")
    
    file_path = "data/sector_strength.csv"
    if os.path.exists(file_path):
        os.remove(file_path)

    all_tickers = list(set([BENCHMARK] + SECTORS_BIG + SECTORS_SMALL))
    
    # 建立一個空的 DataFrame 來存所有資料
    combined_df = pd.DataFrame()

    # 迴圈：一檔一檔抓，確保資料正確
    # 雖然笨，但這能解決 yfinance 批量下載時 auto_adjust 失效的問題
    for ticker in all_tickers:
        try:
            # 抓取單檔，強制 auto_adjust=True
            df = yf.download(ticker, start="2006-01-01", progress=False, auto_adjust=True)
            
            # 取出 Close (因為 auto_adjust=True，這個 Close 就是還原後的價格)
            if 'Close' in df.columns:
                series = df['Close']
                # 重新命名為股票代號
                series.name = ticker
                
                # 合併到大表
                if combined_df.empty:
                    combined_df = pd.DataFrame(series)
                else:
                    combined_df = combined_df.join(series, how='outer')
            else:
                print(f"      ⚠️ {ticker} 下載成功但找不到 Close 欄位")

        except Exception as e:
            print(f"      ❌ {ticker} 下載失敗: {e}")
            
    # 簡單清理
    combined_df = combined_df.ffill().dropna(how='all')
    
    # 存檔
    df_result = combined_df.reset_index()
    if "Date" in df_result.columns:
        df_result.rename(columns={"Date": "date"}, inplace=True)
        
    if not os.path.exists("data"): os.makedirs("data")
    
    df_result.to_csv(file_path, index=False)
    print(f"   ✅ [Sector Strength] 儲存成功 (SMH 修正確認): {file_path}")

if __name__ == "__main__":
    update()