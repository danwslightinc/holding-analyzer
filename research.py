import yfinance as yf
import pandas as pd
from datetime import datetime
import sys

def format_large_number(num):
    if not num: return "N/A"
    if num >= 1e12:
        return f"${num/1e12:.2f}T"
    elif num >= 1e9:
        return f"${num/1e9:.2f}B"
    elif num >= 1e6:
        return f"${num/1e6:.2f}M"
    return f"${num:,.0f}"

def format_pct(num):
    if num is None: return "N/A"
    return f"{num*100:.2f}%"

def generate_report(symbol=None):
    if not symbol:
        symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL" # Default to AAPL if no arg
        
    print(f"Fetching detailed data for {symbol}...")
    
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
    
    # --- 1. Key Metrics & Valuation ---
    current_price = info.get('currentPrice') or hist['Close'].iloc[-1]
    mkt_cap = info.get('marketCap')
    pe_trailing = info.get('trailingPE')
    pe_forward = info.get('forwardPE')
    peg_ratio = info.get('pegRatio') or "N/A"
    ps_ratio = info.get('priceToSalesTrailing12Months')
    pb_ratio = info.get('priceToBook')
    
    div_yield = info.get('dividendYield')
    payout_ratio = info.get('payoutRatio')
    
    # Profitability
    roe = info.get('returnOnEquity')
    profit_margin = info.get('profitMargins')
    op_margin = info.get('operatingMargins')
    
    # Growth
    rev_growth = info.get('revenueGrowth')
    earnings_growth = info.get('earningsGrowth')
    
    # Balance Sheet
    debt_to_equity = info.get('debtToEquity')
    curr_ratio = info.get('currentRatio')
    free_cashflow = info.get('freeCashflow')
    
    # Analyst Estimates
    target_mean = info.get('targetMeanPrice')
    target_low = info.get('targetLowPrice')
    target_high = info.get('targetHighPrice')
    recommendation = info.get('recommendationKey', 'N/A').replace('_', ' ').title()
    num_analysts = info.get('numberOfAnalystOpinions')

    long_name = info.get('longName', symbol)
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')
    summary = info.get('longBusinessSummary', 'No summary available.')
    
    # --- 2. Technical Analysis ---
    # SMA
    sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
    sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
    
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    # Trend
    if current_price > sma50 and current_price > sma200:
        trend = "Strong Uptrend 🟢"
    elif current_price < sma50 and current_price < sma200:
        trend = "Downtrend 🔴"
    else:
        trend = "Neutral / Consolidating 🟡"

    # --- 3. Returns Calculation ---
    returns = {}
    periods = {'1 Month': 21, '3 Months': 63, '6 Months': 126, '1 Year': 252}
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

    # --- Generate Report Markdown ---
    
    md_rows = "\n".join([f"| {k} | {v} |" for k, v in returns.items()])
    
    # Handle Analyst Targets
    upside = "N/A"
    if target_mean and current_price:
        upside_val = (target_mean - current_price) / current_price
        upside = f"{upside_val*100:.1f}%"

    report = f"""# 📊 Quantitative Research Report: {symbol}
**Company:** {long_name}
**Sector:** {sector} | **Industry:** {industry}
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Price:** ${current_price:,.2f}

## 1. Executive Summary
{summary}

## 2. Valuation & Financials
| Metric | Value | Reference |
|---|---|---|
| **Market Cap** | {format_large_number(mkt_cap)} | Size |
| **P/E (Trailing)** | {pe_trailing:.2f} | Avg ~20-25 |
| **P/E (Forward)** | {pe_forward:.2f} | Future Expectations |
| **PEG Ratio** | {peg_ratio} | < 1.0 is Undervalued |
| **Price/Book** | {pb_ratio} | Asset Value |
| **Dividend Yield** | {format_pct(div_yield)} | Income |
| **Payout Ratio** | {format_pct(payout_ratio)} | Safety of Div |

**Profitability & Growth:**
- **ROE:** {format_pct(roe)}
- **Profit Margin:** {format_pct(profit_margin)}
- **Revenue Growth (YoY):** {format_pct(rev_growth)}
- **Earnings Growth (YoY):** {format_pct(earnings_growth)}

**Balance Sheet:**
- **Debt/Equity:** {debt_to_equity} (Lower is better)
- **Current Ratio:** {curr_ratio} (> 1.0 is safe)
- **Free Cash Flow:** {format_large_number(free_cashflow)}

## 3. Analyst Consensus
- **Recommendation:** **{recommendation.upper()}** (Based on {num_analysts} Analysts)
- **Target Price:** ${target_mean:.2f} (Upside: {upside})
- **Range:** ${target_low} - ${target_high}

## 4. Technical Analysis
| Indicator | Value | Signal |
|---|---|---|
| **Trend** | - | {trend} |
| **RSI (14)** | {current_rsi:.1f} | { "Overbought (>70)" if current_rsi > 70 else "Oversold (<30)" if current_rsi < 30 else "Neutral" } |
| **SMA 50** | ${sma50:.2f} | Short-term Support |
| **SMA 200** | ${sma200:.2f} | Long-term Trend |

**Performance History:**
| Period | Return |
|---|---|
{md_rows}

---
*Generated by Auto-Research Tool*
"""
    
    filename = f"{symbol.replace('.','_')}_Quant_Report.md"
    with open(filename, "w", encoding='utf-8') as f:
        f.write(report)
    
    print(f"Quant Report generated: {filename}")
    # print(report)

if __name__ == "__main__":
    generate_report()
