import yfinance as yf
import pandas as pd
import numpy as np

def analyze_ticker(symbol):
    print(f"Fetching 1 year of data for {symbol}...")
    # Fetch 1 year of data
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y")
    
    if df.empty:
        print("No data found.")
        return

    # Current stats
    current_price = df['Close'].iloc[-1]
    
    # 52-week Stats
    high_52 = df['High'].max()
    low_52 = df['Low'].min()
    mean_price = df['Close'].mean()
    
    # Moving Averages
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    sma_50 = df['SMA_50'].iloc[-1]
    sma_200 = df['SMA_200'].iloc[-1]
    
    # Recent Trend (Last 30 days)
    recent_df = df.tail(30).copy()
    recent_high = recent_df['High'].max()
    recent_low = recent_df['Low'].min()
    recent_avg = recent_df['Close'].mean()
    
    print("\n" + "="*40)
    print(f"ANALYSIS FOR {symbol}")
    print("="*40)
    print(f"Current Price:       ${current_price:.2f}")
    print("-" * 40)
    print(f"52-Week Range:       ${low_52:.2f} - ${high_52:.2f}")
    print(f"50-Day SMA:          ${sma_50:.2f}")
    print(f"200-Day SMA:         ${sma_200:.2f}")
    print("-" * 40)
    print(f"Last 30 Days Range:  ${recent_low:.2f} - ${recent_high:.2f}")
    print(f"Last 30 Days Avg:    ${recent_avg:.2f}")
    print("="*40)
    
    # Fundamental Info (if available)
    try:
        info = ticker.info
        target_mean = info.get('targetMeanPrice')
        target_high = info.get('targetHighPrice')
        target_low = info.get('targetLowPrice')
        rec = info.get('recommendationKey')
        
        print("\nANALYST ESTIMATES (Yahoo Finance)")
        print(f"Recommendation:      {rec}")
        print(f"Target Mean Price:   ${target_mean}")
        print(f"Target High:         ${target_high}")
        print(f"Target Low:          ${target_low}")
    except Exception as e:
        print(f"Could not fetch analyst info: {e}")

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    else:
        symbol = "ACB.TO" # Default
    analyze_ticker(symbol)
