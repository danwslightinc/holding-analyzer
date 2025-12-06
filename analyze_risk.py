import pandas as pd
import yfinance as yf
from data_loader import load_portfolio_holdings
from tabulate import tabulate

MSG_DEAD = "Likely 'Dead' (Loss > 90%)"
MSG_FISHY_DROP = "Fishy: Big Recent Drop"
MSG_FISHY_VOL = "Fishy: Extreme Volatility"
MSG_FISHY_TREND = "Fishy: Broken Trend"
MSG_SAFE = "Seemingly Normal"

def check_fishy_stocks():
    # Load Portfolio
    csv_path = "/Users/mingli/Documents/Ming/Investment/Yahoo/portfolio.csv"
    df = load_portfolio_holdings(csv_path)
    
    if df.empty: return

    # Exclude known 'dead' ones slightly (losses > 80%? or just SAVA/ACB/YGMZ)
    # Actually, let's scan ALL, but flag the 'fishy' characteristics.
    # Exclude CASH.TO
    df = df[~df['Symbol'].astype(str).str.contains('CASH.TO')]
    
    symbols = df['Symbol'].unique()
    
    # We will fetch data and check:
    # 1. Beta (Volatility) > 2.0?
    # 2. Trading well below 200 SMA?
    # 3. Recent 1-month drop > 20%?
    
    scan_results = []
    
    print(f"Scanning {len(symbols)} tickers for anomalies...\n")
    
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="6mo")
            info = ticker.info # Can be slow one by one, but fine for small portfolio
            
            if hist.empty:
                continue
                
            current_price = hist['Close'].iloc[-1]
            
            # --- Checks ---
            flags = []
            
            # 1. Trend Check (vs 200 Day if poss, or just 50 day from 6mo data)
            # We only have 6mo loaded here for speed, so approx 126 days.
            sma_50 = hist['Close'].tail(50).mean()
            
            if current_price < sma_50 * 0.85:
                flags.append("📉 Down >15% vs 50d Avg")

            # 2. Recent Drop (Last 30 days)
            month_ago_price = hist['Close'].iloc[-20] if len(hist) > 20 else hist['Close'].iloc[0]
            month_return = (current_price / month_ago_price) - 1
            if month_return < -0.15:
                flags.append(f"🩸 Dropped {month_return:.1%} in 30d")

            # 3. Fundamental "Fishiness" (High Value but losing money?)
            # Or Beta
            beta = info.get('beta')
            if beta and beta > 2.5:
                flags.append(f"⚡ High Beta ({beta:.2f})")
                
            # 4. Trailing PE (detect bubbles or loss-makers)
            # If 'trailingPE' is None, usually means negative earnings (loss maker)
            pe = info.get('trailingPE')
            if pe is None:
                # flags.append("⚠️ Earnings Negative (Unprofitable)")
                # Too common, maybe just filter for non-tech?
                pass
            elif pe > 100:
                flags.append(f"🎈 High P/E ({pe:.1f})")

            # Classify
            status = "OK"
            if flags:
                status = "FISHY? 🐟"
            
            # Reconstruct row
            scan_results.append({
                "Symbol": sym,
                "Price": f"${current_price:.2f}",
                "Status": status,
                "Flags": ", ".join(flags) if flags else "Stable"
            })
            
        except Exception as e:
            print(f"Skipping {sym}: {e}")

    # Build DataFrame
    results_df = pd.DataFrame(scan_results)
    
    # Filter to show only Fishy ones + maybe interesting metrics?
    fishy_df = results_df[results_df['Status'].str.contains("FISHY")]
    
    print("\n" + "="*50)
    print("FISHY STOCK REPORT")
    print("="*50)
    
    if fishy_df.empty:
        print("Good news! Aside from the known dead ones, nothing else looks visibly 'broken' or highly volatile right now.")
    else:
        print(tabulate(fishy_df, headers="keys", tablefmt="psql"))
        print("\nNOTE: Large drops or broken trends might indicate trouble ahead.")

if __name__ == "__main__":
    check_fishy_stocks()
