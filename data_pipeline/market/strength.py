"""
data_pipeline/market/strength.py
負責抓取美股各大板塊的股價，並使用「三引擎」無死角獲取 ETF 最新成分股
"""
import yfinance as yf
import pandas as pd
import os
import json
import time

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

def get_etf_holdings_triple_engine(ticker):
    """三引擎獲取成分股，保證絕對抓得到"""
    
    # 【引擎 1】Yfinance 原生方法 (需要最新版 yfinance)
    try:
        h = yf.Ticker(ticker).funds_data.top_holdings
        if h is not None and not h.empty:
            syms = [str(s).replace(".", "-") for s in h.index if str(s).upper() not in ["CASH", "USD", "OTHER", "PROSPECTUS"]]
            if syms: return syms[:15], "YFinance API"
    except:
        pass

    # 【引擎 2】urllib 底層繞過 StockAnalysis 的 Cloudflare 防火牆
    try:
        import urllib.request
        from bs4 import BeautifulSoup
        url = f"https://stockanalysis.com/etf/{ticker.lower()}/holdings/"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
        )
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="main-table")
        if table:
            syms = []
            for row in table.find("tbody").find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 2:
                    sym = cols[1].text.strip()
                    if sym and sym.upper() not in ["CASH", "USD", "-", "OTHER"]:
                        syms.append(sym.replace(".", "-"))
            if syms: return syms[:15], "StockAnalysis"
    except:
        pass

    # 【引擎 3】Yahoo 隱藏 JSON API
    try:
        import requests
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=topHoldings"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            result = data.get("quoteSummary", {}).get("result", [])
            if result and result[0].get("topHoldings"):
                h = result[0]["topHoldings"].get("holdings", [])
                valid = [item["symbol"].replace(".", "-") for item in h if item.get("symbol") and item.get("symbol").upper() not in ["CASH", "USD", "OTHER", "PROSPECTUS"]]
                if valid: return valid[:15], "Yahoo JSON"
    except:
        pass
    
    return [], "All Failed"

def update():
    print("   ↳ 💪 [Sector Strength] 正在下載板塊強弱度歷史股價...")
    all_tickers = [BENCHMARK]
    for group in PORTFOLIO_STRUCTURE.values():
        all_tickers.extend(group.keys())
    all_tickers = list(set(all_tickers))
    
    try:
        yf_data = yf.download(all_tickers, start="2006-01-01", progress=False, auto_adjust=True, threads=True)
        data = yf_data['Close'] if 'Close' in yf_data.columns else yf_data
        data = data.ffill().dropna(how='all')
        
        df_result = data.reset_index()
        if "Date" in df_result.columns: df_result.rename(columns={"Date": "date"}, inplace=True)
        if not os.path.exists("data"): os.makedirs("data")
        
        df_result.to_csv("data/sector_strength.csv", index=False)
        print("   ✅ [Sector Strength] 歷史股價儲存成功")
    except Exception as e:
        print(f"   ❌ [Sector Strength] 股價下載失敗: {e}")

    # ==========================================
    # 執行成分股掃描
    # ==========================================
    print("   ↳ 🔍 [Sector Strength] 三引擎啟動：正在掃描最新成分股...")
    etf_holdings = {}
    
    for group in PORTFOLIO_STRUCTURE.values():
        for ticker in group.keys():
            top_15, source = get_etf_holdings_triple_engine(ticker)
            
            if top_15:
                etf_holdings[ticker] = top_15
                print(f"      - {ticker}: 成功 ({len(top_15)}檔) [via {source}]")
            else:
                print(f"      - {ticker}: ❌ 抓取失敗 (三種引擎皆被擋)")
                
            time.sleep(0.5) # 保護 IP，暫停 0.5 秒
            
    if etf_holdings:
        with open("data/etf_holdings.json", "w", encoding="utf-8") as f:
            json.dump(etf_holdings, f, ensure_ascii=False, indent=4)
        print(f"   ✅ [Sector Strength] 成功儲存 {len(etf_holdings)} 檔 ETF 的成分股清單")
    else:
        print("   ⚠️ [Sector Strength] 嚴重錯誤：三引擎皆未能抓取資料。")

if __name__ == "__main__":
    update()