# config.py
INDICATORS = {
    "rates": {
        "title": "利率市場 (Rates)",
        "items": [
            # module 代表它對應 data_engine/rates/treasury.py
            {"id": "DGS10", "name": "10 Years Yield", "ticker": "DGS10", "module": "treasury"},
            {"id": "DGS2", "name": "2 Years Yield", "ticker": "DGS2", "module": "treasury"},
            {"id": "SPREAD_10_2", "name": "10-2 Spread", "ticker": "SPREAD_10_2", "module": "treasury"},
        ],
    },
    "market": {  # 將 crypto 改名為 market，並可容納更多指標
        "title": "大盤與寬度 (Market)",
        "items": [
            {"id": "BREADTH_SP500", "name": "S&P 500 市場寬度", "ticker": "SP500_BREADTH", "module": "breadth"},
        ],
    },
    "oil": {
        "title": "能源 (Energy)",
        "items": [
            # 預留位置
            # {"id": "WTI", "name": "WTI 原油", "ticker": "CL=F", "module": "energy"},
        ]
    }
}
