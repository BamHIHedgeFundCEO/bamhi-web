"""
data_pipeline/market/naaim.py
負責抓取 NAAIM 機構經理人持倉指數，並與 S&P 500 對照
"""
import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import os

DATA_DIR = "data"
NAAIM_FILE = os.path.join(DATA_DIR, "naaim.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "NAAIM_History.xlsx")

def get_naaim_latest():
    """從 NAAIM 官網爬取最新的 Excel 檔案連結並下載"""
    url = "https://naaim.org/programs/naaim-exposure-index/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    try:
        r = requests.get(url, headers=headers)
        # 如果還是被擋，強制拋出錯誤讓我們知道
        r.raise_for_status() 
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 尋找網頁中的 excel 連結
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if ('.xls' in href or '.xlsx' in href) and 'naaim' in href:
                xls_link = a['href']
                break
                
        if xls_link:
            df = pd.read_excel(xls_link)
            return df
    except Exception as e:
        print(f"      [Error] NAAIM 爬蟲失敗: {e}")
    return pd.DataFrame()

def update():
    print("   ↳ 👔 [NAAIM Exposure] 正在更新機構經理人情緒指標...")
    
    # 1. 讀取基礎數據
    if os.path.exists(NAAIM_FILE):
        base_df = pd.read_csv(NAAIM_FILE, parse_dates=['Date'])
    elif os.path.exists(HISTORY_FILE):
        try:
            base_df = pd.read_excel(HISTORY_FILE, engine='openpyxl')
            
            # 👇 2. 加上防呆：如果讀出來的 Excel 是全空的，直接給空表
            if base_df.empty:
                base_df = pd.DataFrame(columns=['Date', 'NAAIM'])
            else:
                # 智慧解析欄位
                date_col = next((c for c in base_df.columns if 'date' in str(c).lower()), base_df.columns[0])
                naaim_col = next((c for c in base_df.columns if 'naaim' in str(c).lower() or 'exposure' in str(c).lower()), base_df.columns[1])
                
                base_df = base_df.rename(columns={date_col: 'Date', naaim_col: 'NAAIM'})
                base_df['Date'] = pd.to_datetime(base_df['Date'], errors='coerce')
                base_df['NAAIM'] = pd.to_numeric(base_df['NAAIM'], errors='coerce')
                base_df = base_df.dropna(subset=['Date', 'NAAIM'])[['Date', 'NAAIM']]
                
        except Exception as e:
            print(f"      [Error] 讀取 Excel 失敗: {e}")
            base_df = pd.DataFrame(columns=['Date', 'NAAIM'])
    # 2. 抓取最新數據並合併
    new_df = get_naaim_latest()
    if not new_df.empty:
        try:
            date_col = next((c for c in new_df.columns if 'date' in str(c).lower()), new_df.columns[0])
            naaim_col = next((c for c in new_df.columns if 'naaim' in str(c).lower() or 'exposure' in str(c).lower()), new_df.columns[1])
            new_df = new_df.rename(columns={date_col: 'Date', naaim_col: 'NAAIM'})
            new_df['Date'] = pd.to_datetime(new_df['Date'], errors='coerce')
            new_df['NAAIM'] = pd.to_numeric(new_df['NAAIM'], errors='coerce')
            new_df = new_df.dropna(subset=['Date', 'NAAIM'])[['Date', 'NAAIM']]
            
            full_df = pd.concat([base_df, new_df]).drop_duplicates(subset=['Date'], keep='last').sort_values('Date')
        except:
            full_df = base_df
    else:
        full_df = base_df

    if full_df.empty:
        return

    # 3. 計算 MA20
    full_df['NAAIM_MA20'] = full_df['NAAIM'].rolling(window=20).mean()

    # 4. 補上 S&P 500 收盤價
# 4. 補上 S&P 500 收盤價
    start_date = full_df['Date'].min()
    try:
        sp500 = yf.download("^GSPC", start=start_date, progress=False, auto_adjust=False)['Close']
        if not sp500.empty:
            if isinstance(sp500, pd.DataFrame):
                sp500 = sp500.iloc[:, 0]
            sp500 = sp500.reset_index()
            sp500.columns = ['Date', 'SP500_Price']
            
            # 🔥 修正 2：合併前先刪除舊有的 SP500_Price
            if 'SP500_Price' in full_df.columns:
                full_df = full_df.drop(columns=['SP500_Price'])
                
            full_df = pd.merge_asof(full_df.sort_values('Date'), 
                                    sp500.sort_values('Date'), 
                                    on='Date', 
                                    direction='backward')
    except Exception as e:
        print(f"      [Error] S&P 500 下載失敗: {e}")

    # 5. 存檔
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    full_df.to_csv(NAAIM_FILE, index=False)
    print(f"   ✅ [NAAIM Exposure] 儲存成功，最新日期: {full_df['Date'].iloc[-1].strftime('%Y-%m-%d')}")