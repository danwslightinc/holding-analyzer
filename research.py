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

# Representative Peers for Industry Averages
SECTOR_PEERS = {
    'Technology': ['AAPL', 'MSFT', 'NVDA', 'ORCL', 'ADBE'],
    'Financial Services': ['JPM', 'BAC', 'V', 'MA', 'GS'],
    'Healthcare': ['LLY', 'JNJ', 'UNH', 'ABBV', 'MRK'],
    'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE'],
    'Consumer Defensive': ['WMT', 'PG', 'KO', 'PEP', 'COST'],
    'Energy': ['XOM', 'CVX', 'SHEL', 'COP', 'SLB'],
    'Industrials': ['CAT', 'UNP', 'HON', 'GE', 'UPS'],
    'Communication Services': ['GOOGL', 'META', 'NFLX', 'DIS', 'TMUS'],
    'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP'],
    'Real Estate': ['PLD', 'AMT', 'EQIX', 'PSA', 'CCI'],
    'Basic Materials': ['LIN', 'BHP', 'RIO', 'SHW', 'FCX']
}

def get_industry_averages(sector):
    """Fetches simple average metrics for a given sector."""
    peers = SECTOR_PEERS.get(sector, [])
    if not peers: return {}
    
    print(f"Fetching industry data for {sector} ({len(peers)} peers)...")
    metrics = {
        'forwardPE': [], 'pegRatio': [], 'dividendYield': [], 
        'returnOnEquity': [], 'profitMargins': [], 'debtToEquity': []
    }
    
    # Quick fetch (limit to 5 peers max to speed up)
    for p in peers[:5]:
        try:
            p_info = yf.Ticker(p).info
            for k in metrics.keys():
                val = p_info.get(k)
                if val is not None:
                    metrics[k].append(val)
        except: pass
        
    averages = {}
    for k, v in metrics.items():
        if v:
            averages[k] = sum(v) / len(v)
        else:
            averages[k] = None
            
    return averages

def format_float(num, pattern="{:.2f}"):
    if num is None: return "N/A"
    try:
        return pattern.format(num)
    except:
        return "N/A"

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
        hist = ticker.history(period="max")
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
    pe_forward = info.get('forwardPE')
    
    # PEG Logic (Match market_data.py)
    peg_ratio = info.get('pegRatio') or info.get('trailingPegRatio')
    if peg_ratio is None and info.get('quoteType') == 'EQUITY':
        try:
            # Synthetic Fallback
            estimates = ticker.growth_estimates
            if estimates is not None and not estimates.empty:
                growth_rate = None
                if '+1y' in estimates.index:
                    growth_rate = estimates.loc['+1y', 'stockTrend']
                elif 'LTG' in estimates.index:
                    growth_rate = estimates.loc['LTG', 'stockTrend']
                
                if growth_rate and growth_rate > 0:
                     pe_val = pe_forward or pe_trailing
                     if pe_val:
                         peg_ratio = pe_val / (growth_rate * 100)
        except:
            pass
            
    peg_display = f"{peg_ratio:.2f}" if isinstance(peg_ratio, (int, float)) else "N/A"
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
    
    # Industry Averages
    ind_avg = get_industry_averages(sector)
    
    # Helper for formatting benchmark comparison
    def fmt_bench(key, fmt_func=format_float):
        val = ind_avg.get(key)
        if val is None: return "N/A"
        return f"{fmt_func(val)}"
    
    # --- 2. Technical Analysis ---
    # SMA
    sma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
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

    # Support & Resistance / Ceiling
    ath = hist['High'].max()
    ceilings = []
    
    if current_price >= ath * 0.99: # At or near ATH (within 1%)
        ceilings.append(f"ATH: ${ath:.2f} (Price Discovery)")
        # Fib Extensions from 52w range
        last_year = hist.iloc[-252:]
        low_52w = last_year['Low'].min()
        high_52w = last_year['High'].max()
        diff = high_52w - low_52w
        fib_1272 = high_52w + (diff * 0.272)
        ceilings.append(f"Fib 1.272: ${fib_1272:.2f}")
        ceilings.append(f"Psych: ${int(current_price/5)*5 + 5}")
    else:
        # Find historical resistance (weekly highs above current)
        # Resample to weekly to reduce noise
        weekly = hist['High'].resample('W').max()
        above_current = weekly[weekly > current_price * 1.01] # 1% buffer
        if not above_current.empty:
            next_levels = sorted(above_current.unique())[:3]
            # Simple clustering - pick first and then ones far enough apart
            clusters = []
            if next_levels:
                clusters.append(next_levels[0])
                for l in next_levels[1:]:
                    if l - clusters[-1] > (current_price * 0.02): # 2% gap
                        clusters.append(l)
            
            for c in clusters[:2]:
                ceilings.append(f"${c:.2f}")
            ceilings.append(f"ATH: ${ath:.2f}")
        else:
            ceilings.append(f"ATH: ${ath:.2f}")
            
    resistance_str = ", ".join(ceilings)

    # Floor / Support
    floors = []
    # Find historical supports (weekly lows below current)
    weekly_lows = hist['Low'].resample('W').min()
    # Filter for lows below current price (with 1% buffer to avoid immediate noise)
    below_current = weekly_lows[weekly_lows < current_price * 0.99]
    
    if not below_current.empty:
        # Sort descending (nearest first)
        next_levels = sorted(below_current.unique(), reverse=True)
        
        # Simple clustering - pick first and then ones far enough apart
        clusters = []
        if next_levels:
            clusters.append(next_levels[0])
            for l in next_levels[1:]:
                if clusters[-1] - l > (current_price * 0.02): # 2% gap
                    clusters.append(l)
        
        for f in clusters[:3]: # Show top 3 supports
            floors.append(f"${f:.2f}")
    else:
        floors.append("N/A")
        
    floor_str = ", ".join(floors)

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

    # --- Financial History (Income Statement) ---
    fin_table = ""
    try:
        stmt = ticker.income_stmt
        if not stmt.empty:
            # Select key rows and last 3 years
            cols = stmt.columns[:3] # Last 3 years
            
            # Helper to get row safely
            def get_row(name):
                if name in stmt.index:
                    return stmt.loc[name, cols]
                return None
            
            headers = ["Metric"] + [d.strftime('%Y') for d in cols]
            rows = []
            
            # Metrics to show
            metrics = {
                'Total Revenue': 'Revenue',
                'Gross Profit': 'Gross Profit', 
                'Operating Income': 'Op Income', 
                'Net Income': 'Net Income',
                'Basic EPS': 'EPS'
            }
            
            for key, label in metrics.items():
                data = get_row(key)
                if data is not None:
                    row_vals = [f"**{label}**"]
                    for val in data:
                        if key == 'Basic EPS':
                            row_vals.append(f"${val:.2f}")
                        else:
                            row_vals.append(format_large_number(val))
                    rows.append(f"| {' | '.join(row_vals)} |")
            
            fin_table = f"| {' | '.join(headers)} |\n| {' | '.join(['---']*len(headers))} |\n" + "\n".join(rows)
    except Exception as e:
        print(f"Error fetching financials: {e}") 


    # --- 4. Morningstar-Style Analysis ---
    # Fair Value Proxy = Mean Target Price
    fair_value = target_mean if target_mean else current_price
    price_to_fv = current_price / fair_value if fair_value else 1.0
    
    # Star Rating Logic (Approximate)
    # < 0.7 = 5 Stars, < 0.85 = 4 Stars, 0.85-1.15 = 3 Stars, > 1.15 = 2 Stars, > 1.30 = 1 Star
    if price_to_fv < 0.70: stars = "⭐⭐⭐⭐⭐"
    elif price_to_fv < 0.85: stars = "⭐⭐⭐⭐"
    elif price_to_fv > 1.30: stars = "⭐"
    elif price_to_fv > 1.15: stars = "⭐⭐"
    else: stars = "⭐⭐⭐"
    
    # Economic Moat Proxy
    # ROE > 15% + Net Margin > 15% -> Wide?
    moat = "None"
    if roe and roe > 0.15:
        if profit_margin and profit_margin > 0.10:
            moat = "Wide"
        else:
            moat = "Narrow"
            
    # Bulls Say / Bears Say (Dynamic Generation)
    bulls = []
    bears = []
    
    # Growth
    if rev_growth and rev_growth > 0.10: bulls.append(f"Strong top-line growth of {rev_growth:.1%} indicates gaining market share.")
    elif rev_growth and rev_growth < 0: bears.append(f"Revenue is contracting ({rev_growth:.1%}), signaling headwinds.")
    else: 
        growth_val = f"{rev_growth:.1%}" if rev_growth else "N/A"
        bears.append(f"Revenue growth is tepid ({growth_val}), lagging high-growth peers.")
    
    # Valuation
    if price_to_fv < 0.85: bulls.append(f"Trading at a discount to Fair Value (${fair_value:,.2f}), offering a margin of safety.")
    if peg_ratio != "N/A" and isinstance(peg_ratio, float) and peg_ratio > 2.0: bears.append(f"Valuation is rich (PEG {peg_ratio:.2f}), pricing in perfection.")
    
    # Profitability
    if roe and roe > 0.20: bulls.append(f"Exceptional Return on Equity ({roe:.1%}) demonstrates superior capital allocation.")
    if profit_margin and profit_margin < 0.05: bears.append(f"Thin profit margins ({profit_margin:.1%}) leave little room for error.")
    elif profit_margin and profit_margin > 0.15: bulls.append(f"Healthy profit margins ({profit_margin:.1%}) define a strong competitive position.")
    
    # Financial Health
    if debt_to_equity and debt_to_equity > 150: bears.append(f"High leverage (Debt/Equity: {debt_to_equity}) poses risk in high-rate environments.")
    if curr_ratio and curr_ratio < 1.0: bears.append(f"Weak liquidity (Current Ratio {curr_ratio}) could limit operational flexibility.")
    
    # Technicals
    if "Uptrend" in trend: bulls.append("Technical momentum is positive, trading above key moving averages.")
    if current_rsi < 30: bulls.append(f"RSI is oversold ({current_rsi:.1f}), suggesting a potential mean-reversion bounce.")
    if current_rsi > 70: bears.append(f"RSI is overbought ({current_rsi:.1f}), suggesting a pullback is imminent.")
    
    bulls_str = "\n".join([f"- {b}" for b in bulls])
    bears_str = "\n".join([f"- {b}" for b in bears])

    # --- Generate Report Markdown ---
    
    md_rows = "| Period | Return |\n|---|---|\n" + "\n".join([f"| {k} | {v} |" for k, v in returns.items()])
    
    # Handle Analyst Targets (ensure format)
    upside = "N/A"
    if target_mean and current_price:
        upside_val = (target_mean - current_price) / current_price
        upside = f"{upside_val*100:.1f}%"

    report = f"""# 📑 Equity Research: {symbol}
**{long_name}** | {stars} ({price_to_fv:.2f} P/FV)
**Last Close:** ${current_price:,.2f} | **Fair Value:** ${fair_value:,.2f} | **Moat:** {moat}

---

## 🚀 Investment Thesis
**Bulls Say:**
{bulls_str if bulls else "- Solid fundamentals with no major red flags."}

**Bears Say:**
{bears_str if bears else "- Valuation appears reasonable with no major structural risks."}

---

## 📊 Key Statistics
| Metric | Value | Ind. Avg |
|---|---|---|
| **Market Cap** | {format_large_number(mkt_cap)} | - |
| **P/E (Fwd)** | {format_float(pe_forward)} | {fmt_bench('forwardPE')} |
| **PEG Ratio** | {peg_display} | {fmt_bench('pegRatio')} |
| **Div Yield** | {div_yield}% | {fmt_bench('dividendYield', format_pct)} |
| **ROE** | {format_pct(roe)} | {fmt_bench('returnOnEquity', format_pct)} |
| **Net Margin** | {format_pct(profit_margin)} | {fmt_bench('profitMargins', format_pct)} |

## 🏗 Financial Health & Valuation
**Balance Sheet:**
| Metric | Value | Ind. Avg |
|---|---|---|
| **Debt/Equity** | {format_float(debt_to_equity)} | {fmt_bench('debtToEquity')} |
| **Current Ratio** | {format_float(curr_ratio)} | > 1.0 (Safe) |
| **Free Cash Flow** | {format_large_number(free_cashflow)} | - |

**Analyst Consensus:**
| Metric | Value | Detail |
|---|---|---|
| **Recommendation** | **{recommendation.upper()}** | Based on {num_analysts} Analysts |
| **Target Price** | ${format_float(target_mean)} | Upside: {upside} |
| **Range** | ${format_float(target_low)} - ${format_float(target_high)} | Low - High |

## 📅 Financial Trends (Annual)
{fin_table if fin_table else "No financial history available."}

---

## 📉 Technical Analysis
| Indicator | Value | Signal |
|---|---|---|
| **Trend** | {trend} | Market Phase |
| **RSI (14)** | {current_rsi:.1f} | Momentum |
| **SMA 20** | ${format_float(sma20)} | Short-term Trend |
| **SMA 50** | ${format_float(sma50)} | Medium-term Trend |
| **SMA 200** | ${format_float(sma200)} | Long-term Trend |
| **Support** | **{floor_str}** | Buy Zones |
| **Resistance** | **{resistance_str}** | Sell Zones |

**Trailing Returns:**
{md_rows}

---
*Analyst Note: This report was auto-generated based on quantitative and technical data points intentionally mimicking professional equity research standards.*
"""
    
    filename = f"{symbol.replace('.','_')}_Quant_Report.md"
    with open(filename, "w", encoding='utf-8') as f:
        f.write(report)
    
    print(f"Quant Report generated: {filename}")
    # print(report)

if __name__ == "__main__":
    generate_report()
