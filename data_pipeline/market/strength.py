"""
data_pipeline/market/strength.py
負責抓取美股各大板塊 (GICS + 戰術型) 的股價，存成 data/sector_strength.csv
"""
import yfinance as yf
import pandas as pd
import os

# 定義清單
BENCHMARK = "VTI"

# 定義全新 11大板塊與戰術型清單結構
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

def update():
    print("   ↳ 💪 [Sector Strength] 正在下載板塊強弱度資料...")
    
    # 1. 整理所有要下載的代號
    all_tickers = [BENCHMARK]
    for group in PORTFOLIO_STRUCTURE.values():
        all_tickers.extend(group.keys())
        
    all_tickers = list(set(all_tickers))
    
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

    # 新增：於 Pipeline 階段預先抓取所有 ETF 的前 15 大成分股並儲存為 JSON
    print("   ↳ 🔍 [Sector Strength] 正在掃描各板塊 ETF 最新成分股...")
    import requests
    from bs4 import BeautifulSoup
    import json
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    etf_holdings = {}
    for group in PORTFOLIO_STRUCTURE.values():
        for ticker in group.keys():
            url = f"https://stockanalysis.com/etf/{ticker.lower()}/holdings/"
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    table = soup.find("table", id="main-table")
                    if table:
                        tbody = table.find("tbody")
                        if tbody:
                            holdings = []
                            for row in tbody.find_all("tr"):
                                cols = row.find_all("td")
                                if len(cols) >= 2:
                                    sym = cols[1].text.strip()
                                    if sym and sym.upper() not in ["CASH", "USD", "-", "OTHER"]:
                                        holdings.append(sym)
                                        if len(holdings) >= 15:
                                            break
                            if holdings:
                                etf_holdings[ticker] = holdings
                                print(f"      - {ticker}: 成功 ({len(holdings)}檔)")
            except Exception as e:
                print(f"      - {ticker}: 失敗 ({e})")
                
    if etf_holdings:
        holdings_path = "data/etf_holdings.json"
        with open(holdings_path, "w", encoding="utf-8") as f:
            json.dump(etf_holdings, f, ensure_ascii=False, indent=4)
        print(f"   ✅ [Sector Strength] 成功儲存 {len(etf_holdings)} 檔 ETF 成分股: {holdings_path}")
    else:
        print("   ⚠️ [Sector Strength] 未能抓取到任何 ETF 成分股資料。")

if __name__ == "__main__":
    update()