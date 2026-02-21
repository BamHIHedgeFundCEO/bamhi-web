"""
data_pipeline/market/strength.py
負責抓取美股各大板塊 (GICS + 戰術型) 的股價，存成 data/sector_strength.csv
"""
import yfinance as yf
import pandas as pd
import os

# 定義清單
BENCHMARK = "VTI"

# 大板塊 (GICS 11)
SECTORS_BIG = [
    'VGT', 'VHT', 'VFH', 'VCR', 'VOX', 'VIS', 
    'VDC', 'VDE', 'VPU', 'VAW', 'VNQ'
]

# 戰術小板塊 (Alpha / Tactics)
SECTORS_SMALL = [
    'SMH', 'IGV', 'CIBR', 'SKYY', 'FINX', # 科技細分
    'XBI', 'UFO', 'ROBO',                 # 高成長
    'XOP', 'XES', 'URA', 'NLR', 'TAN',    # 能源與核能
    'GDX', 'COPX', 'LIT',                 # 原物料
    'XHB', 'XRT', 'XTN', 'JETS', 'PAVE',  # 經濟循環
    'XAR', 'IHI'                          # 防禦與醫療
]

def update():
    print("   ↳ 💪 [Sector Strength] 正在下載板塊強弱度資料...")
    
    # 1. 整理所有要下載的代號
    all_tickers = list(set([BENCHMARK] + SECTORS_BIG + SECTORS_SMALL))
    
    try:
        # 2. 下載資料 (使用 auto_adjust=True 修正配息)
        # 這裡我們抓多一點資料，從 2006 年開始，確保回測完整
        data = yf.download(all_tickers, start="2006-01-01", progress=False, auto_adjust=True, threads=True)['Close']
        
        # 簡單清理
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        data = data.ffill().dropna(how='all')
        
        # 3. 整理格式並存檔
        df_result = data.reset_index()
        # 確保日期欄位名稱統一
        if "Date" in df_result.columns:
            df_result.rename(columns={"Date": "date"}, inplace=True)
            
        if not os.path.exists("data"): os.makedirs("data")
        
        file_path = "data/sector_strength.csv"
        df_result.to_csv(file_path, index=False)
        print(f"   ✅ [Sector Strength] 儲存成功: {file_path}")
        
    except Exception as e:
        print(f"   ❌ [Sector Strength] 下載失敗: {e}")

if __name__ == "__main__":
    update()