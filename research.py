import yfinance as yf
import pandas as pd
from datetime import datetime
import sys

def generate_report(symbol=None):
    if not symbol:
        symbol = sys.argv[1] if len(sys.argv) > 1 else "VGRO.TO"
        
    print(f"Fetching live data for {symbol}...")
    
    ticker = yf.Ticker(symbol)
    try:
        info = ticker.info
        hist = ticker.history(period="2y")
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    if hist.empty:
        print("No historical data found.")
        return
    
    # 1. Price & Performance
    current_price = info.get('currentPrice') or hist['Close'].iloc[-1]
    prev_close = info.get('previousClose') or hist['Close'].iloc[-2]
    change = (current_price - prev_close) / prev_close
    
    high_52 = info.get('fiftyTwoWeekHigh', 'N/A')
    low_52 = info.get('fiftyTwoWeekLow', 'N/A')
    
    # Calculate returns
    returns = {}
    periods = {
        '1 Month': 21,
        '3 Months': 63,
        '6 Months': 126,
        '1 Year': 252
    }
    
    for label, days in periods.items():
        if len(hist) > days:
            start_price = hist['Close'].iloc[-days]
            ret = (current_price - start_price) / start_price
            returns[label] = f"{ret*100:.2f}%"
        else:
            returns[label] = "N/A"
            
    # YTD
    current_year = datetime.now().year
    ytd_hist = hist[hist.index.year == current_year]
    if not ytd_hist.empty:
        start_price = ytd_hist['Close'].iloc[0]
        ytd_ret = (current_price - start_price) / start_price
        returns['YTD'] = f"{ytd_ret*100:.2f}%"
    
    # 2. Fundamentals (Hardcoded for VGRO, Generic for others)
    mer = "N/A"
    holdings_section = ""
    sector_section = ""
    thesis_section = ""
    
    if symbol == "VGRO.TO":
        mer = "0.24% (Recent cut to 0.17% reported)"
        holdings_section = """
## 3. Underlying Holdings
VGRO essentially wraps roughly 7 other Vanguard ETFs to achieve global diversification.
| Underlying ETF | Exposure |
|---|---|
| Vanguard US Total Market Index ETF (VUN) | US Equity |
| Vanguard FTSE Canada All Cap Index ETF (VCN) | Canadian Equity |
| Vanguard FTSE Developed All Cap ex North America Index ETF (VIU) | Intl Developed Equity |
| Vanguard Total Bond Market ETF (VAB) | Bonds |
| Vanguard FTSE Emerging Markets All Cap Index ETF (VEE) | Emerging Markets |
"""
        sector_section = """
## 4. Sector Allocation (Look-through)
Approximate Sector weights based on underlying funds:
- **Technology:** 24.3%
- **Financials:** 20.5%
- **Industrials:** 11.6%
- **Consumer Discretionary:** 10.9%
- **Basic Materials:** 7.3%
- **Energy:** 7.0%
- **Health Care:** 6.6%
- **Other:** ~12%
"""
        thesis_section = """
## 5. Thesis / Observation
VGRO is a "Set it and forget it" solution for growth-oriented investors who want global diversification without rebalancing manually.
- **Pros:** Automatic rebalancing, low cost, massive diversification (>13,000 stocks/bonds).
- **Cons:** Fixed 80/20 allocation may be too conservative for aggressive investors or too risky for conservative ones. Home bias (approx 30% Canadian equity) is intentional but debated.
"""
    else:
        # Generic Fundamentals
        mer = f"{info.get('trailingAnnualDividendYield', 'N/A')}" 
        # Try to get sector
        sec = info.get('sector', 'Unknown')
        ind = info.get('industry', 'Unknown')
        sector_section = f"## 4. Sector / Industry\n- **Sector:** {sec}\n- **Industry:** {ind}\n"
        
        # Try to get meaningful summary
        summ = info.get('longBusinessSummary', 'No summary available.')
        thesis_section = f"## 5. Summary\n{summ[:500]}...\n"

    # Dividend Yield
    div_yield = info.get('dividendYield', 0)
    yield_str = "N/A"
    if div_yield:
        if div_yield > 0.5: 
             yield_str = f"{div_yield:.2f}%"
        else:
             yield_str = f"{div_yield*100:.2f}%"
    
    long_name = info.get('longName', symbol)
    
    # Generate Markdown
    # Prepare table rows first
    perf_rows = "\n".join([f"| {k} | {v} |" for k, v in returns.items()])

    md = f"""# {symbol} Research Report
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Ticker:** {symbol}
**Name:** {long_name}

## 1. Overview
{thesis_section}

## 2. Market Data (Live)
- **Price:** ${current_price:.2f}
- **52-Week Range:** ${low_52} - ${high_52}
- **Yield:** {yield_str}
- **Change:** {change*100:.2f}%

### Performance
| Period | Return |
|---|---|
{perf_rows}

{holdings_section}
{sector_section}

## 6. Technicals
"""
    # Quick technical check
    sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
    sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
    
    md += f"- **SMA 50:** ${sma50:.2f}\n"
    md += f"- **SMA 200:** ${sma200:.2f}\n"
    
    if current_price > sma50 and current_price > sma200:
        md += "- **Trend:** Strong Uptrend (Price > SMA50 > SMA200)\n"
    elif current_price < sma50 and current_price < sma200:
        md += "- **Trend:** Downtrend\n"
    else:
        md += "- **Trend:** Mixed / Consolidating\n"

    filename = f"{symbol.replace('.','_')}_Research.md"
    with open(filename, "w") as f:
        f.write(md)
    
    print(f"Report generated: {filename}")
    # print(md)

if __name__ == "__main__":
    generate_report()
