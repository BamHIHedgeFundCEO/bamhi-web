"""
data_pipeline/market/world_sectors.py
負責抓取龜族世界觀 (全球板塊與資產) 的日線收盤價
"""
import yfinance as yf
import pandas as pd
import os

DATA_DIR = "data"
FILE_PATH = os.path.join(DATA_DIR, "world_sectors.csv")

PORTFOLIO_STRUCTURE = {
    "🌐 全球與美國大盤 (Global & US Broad)": {
        "VT": "全球全市場", "ACWI": "全球市場(ACWI)", "ACWX": "全球(除美國)",
        "VTI": "美股全市場", "SPY": "標普500", "QQQ": "納斯達克", "DIA": "道瓊工業",
        "IWM": "羅素2000", "MDY": "中型股", 
        "XLK": "科技板塊", "XLF": "金融板塊", "XLV": "醫療保健"
    },
    "🌏 亞洲與太平洋 (Asia & Pacific)": {
        "EWA": "澳洲", "EWH": "香港", "EWM": "馬來西亞", "EWS": "新加坡",
        "EWT": "台灣", "EWY": "南韓", "IFN": "印度(IFN)", "INDA": "印度(INDA)", 
        "EWJ": "日本", "EPP": "亞洲(不含日本)", "AAXJ": "亞洲(除日本)",
        "FXI": "中國大型股(H股)", "MCHI": "中國全市場", "ASHR": "中國滬深300(A股)", 
        "KWEB": "中國互聯網", "VNM": "越南", "EIDO": "印尼", "THD": "泰國", "EPHE": "菲律賓"
    },
    "🌎 美洲與新興市場 (Americas & EM)": {
        "EEM": "新興市場", "EMXC": "新興市場(除中國)", "VWO": "新興市場(Vanguard)",
        "ILF": "拉丁美洲", "EWC": "加拿⼤", "EWW": "墨西哥", "EWZ": "巴西",
        "ARS": "阿根廷", "ARGT": "阿根廷(ARGT)", "ECH": "智利", "EPU": "秘魯", "GXG": "哥倫比亞"
    },
    "🌍 歐洲板塊 (Europe)": {
        "EFA": "歐澳遠東", "EZU": "歐元區", "IEUR": "歐洲全市場", "VGK": "歐洲(Vanguard)",
        "EWD": "瑞典", "EWG": "德國", "EWK": "比利時", "EWL": "瑞士",
        "EWN": "荷蘭", "EWO": "奧地利", "EWP": "西班牙", "EWQ": "法國", 
        "EWU": "英國", "EWI": "義大利", "GREK": "希臘", "EPOL": "波蘭"
    },
    "🐫 中東與非洲 (Middle East & Africa)": {
        "EZA": "南非", "TUR": "土耳其", "KSA": "沙烏地阿拉伯", 
        "EIS": "以色列", "AFK": "非洲全市場"
    },
    "🏢 房地產與抵押債 (Real Estate)": {
        "VNQ": "美國房地產", "VNQI": "全球房地產(除美國)", "REET": "全球REITs", 
        "REM": "抵押貸款REITs", "MBB": "MBS抵押債券"
    },
    "💰 高股息與進階收益 (Dividend & Income)": {
        "PFF": "特別股與收益", "DVY": "精選高股息", "SCHD": "美國紅利", "IDV": "國際高股息", 
        "AMLP": "能源MLP", "JEPI": "標普掩護性買權", "JEPQ": "納指掩護性買權", 
        "QQQI": "納斯達克高收益", "DIVO": "增強型股息", "QDVO": "成長與收益", 
        "QYLD": "納指Covered Call", "XYLD": "標普Covered Call"
    },
    "🛡️ 固定收益與債券 (Fixed Income)": {
        "BND": "全市場債券", "AGG": "美國總體債", "BNDX": "國際債券", 
        "TIP": "抗通膨債", "VTIP": "短期抗通膨債", 
        "TLT": "20年期公債", "TLH": "10-20年公債", "IEF": "7-10年公債", 
        "IEI": "3-7年公債", "SHY": "1-3年公債", "BILS": "3-12個月國庫券", 
        "BIL": "1-3個月國庫券", "SGOV": "0-3個月國庫券", 
        "LQD": "投資級公司債", "HYG": "高收益債", "BINC": "主動型彈性收益", 
        "JAAA": "AAA級CLO", "JBBB": "BBB級CLO", "EMB": "新興市場債", "EMHY": "新興市場高收債"
    },
    "🛢️ 大宗商品與加密資產 (Commodities & Crypto)": {
        "DBC": "廣泛大宗商品", "PDBC": "大宗商品(PDBC)", "DBB": "基本金屬", "DBA": "農產品", 
        "GLD": "黃金", "SLV": "白銀", "CPER": "銅礦指數",
        "USO": "美國原油", "UNG": "天然氣", 
        "UUP": "美元指數", "IBIT": "比特幣"
    }
}

def update():
    print("   ↳ 🐢 [World Sectors] 正在更新龜族世界觀資產報價...")
    
    TICKERS = []
    for group in PORTFOLIO_STRUCTURE.values():
        TICKERS.extend(group.keys())
    TICKERS = list(set(TICKERS))
    
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
