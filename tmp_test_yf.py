import yfinance as yf

def test_holdings(ticker):
    tkr = yf.Ticker(ticker)
    try:
        holdings = tkr.funds_data.top_holdings
        print(f"Funds Data Holdings for {ticker}:")
        print(holdings)
    except Exception as e:
        print(f"funds_data failed: {e}")

test_holdings("XLK")
