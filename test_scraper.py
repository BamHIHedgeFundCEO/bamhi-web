from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

def get_etf_top_holdings(ticker: str):
    print(f"Scraping holdings for {ticker}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        url = f"https://stockanalysis.com/etf/{ticker.lower()}/holdings/"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(2) # Give it a moment to render any JS table
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # Find the holdings table
            table = soup.find("table", id="main-table")
            if not table:
                print("Table not found")
                return []
                
            tbody = table.find("tbody")
            if not tbody:
                return []
                
            rows = tbody.find_all("tr")
            holdings = []
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    sym = cols[1].text.strip()
                    # Filter out Cash/USD/Other
                    if sym and sym.upper() not in ["CASH", "USD", "-", "OTHER"]:
                        holdings.append(sym)
                        if len(holdings) >= 15:
                            break
                            
            return holdings
        except Exception as e:
            print(f"Error scraping {ticker}: {e}")
            return []
        finally:
            browser.close()

if __name__ == "__main__":
    print(get_etf_top_holdings("XLK"))
    print(get_etf_top_holdings("ARKG"))
