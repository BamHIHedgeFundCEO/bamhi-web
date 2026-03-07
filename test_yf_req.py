import requests

url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/XLK?modules=topHoldings"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}
try:
    response = requests.get(url, headers=headers)
    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text[:500])
except Exception as e:
    print("ERROR:", e)
