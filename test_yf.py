import yfinance as yf

def test_yfinance():
    print("Testing yfinance...")
    try:
        # Test download
        print("Testing yf.download('AAPL')...")
        data = yf.download("AAPL", period="1d")
        print(f"Download success: {not data.empty}")
        
        print("Testing yf.download('SHOP.TO')...")
        data_to = yf.download("SHOP.TO", period="1d")
        print(f"Download SHOP.TO success: {not data_to.empty}")

        # Test Ticker info
        print("Testing yf.Ticker('AAPL').info...")
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        print(f"Ticker info success: {'symbol' in info}")

        print("Testing yf.Ticker('SHOP.TO').info...")
        ticker_to = yf.Ticker("SHOP.TO")
        info_to = ticker_to.info
        print(f"Ticker info SHOP.TO success: {'symbol' in info_to}")
        
        # Test dividends (often uses crumb)
        print("Testing yf.Ticker('AAPL').dividends...")
        divs = ticker.dividends
        print(f"Dividends success: {True}")

        # Test news
        print("Testing yf.Ticker('AAPL').news...")
        news = ticker.news
        print(f"News success: {len(news) > 0}")

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_yfinance()
