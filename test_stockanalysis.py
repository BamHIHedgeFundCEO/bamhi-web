import requests
from bs4 import BeautifulSoup

def get_etf_holdings_stockanalysis(ticker):
    url = f"https://stockanalysis.com/etf/{ticker.lower()}/holdings/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", id="main-table")
        if not table: return []
        tbody = table.find("tbody")
        if not tbody: return []
        
        holdings = []
        for row in tbody.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                sym = cols[1].text.strip()
                if sym and sym.upper() not in ["CASH", "USD", "-", "OTHER"]:
                    holdings.append(sym)
                    if len(holdings) >= 15: break
        return holdings
    except Exception as e:
        print("error", e)
        return []

print(get_etf_holdings_stockanalysis("XLK"))
