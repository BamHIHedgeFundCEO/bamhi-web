# config.py
INDICATORS = {
    "rates": {
        "title": "利率 (Rates)",
        "items": [
            {"id": "DGS10", "name": "10 Years Yield", "ticker": "DGS10"},
            {"id": "DGS2", "name": "2 Years Yield", "ticker": "DGS2"},
            {"id": "SPREAD_10_2", "name": "10-2 Spread", "ticker": "SPREAD_10_2"},
        ],
    },
    "equity": {
        "title": "股市 (Equity)",
        "items": [
            {"id": "SPX", "name": "S&P 500", "ticker": "^GSPC"},
            {"id": "DJI", "name": "道瓊工業指數", "ticker": "^DJI"},
            {"id": "IXIC", "name": "納斯達克指數", "ticker": "^IXIC"},
            {"id": "SOX", "name": "費城半導體", "ticker": "^SOX"},
        ],
    },
    "crypto": {
        "title": "加密貨幣 (Crypto)",
        "items": [
            {"id": "BTC", "name": "比特幣", "ticker": "BTC-USD"},
            {"id": "ETH", "name": "以太幣", "ticker": "ETH-USD"},
        ],
    },
}
