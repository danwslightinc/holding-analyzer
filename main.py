import pandas as pd
from datetime import datetime
from tabulate import tabulate
from data_loader import load_portfolio_holdings
from market_data import get_current_prices
from analysis import calculate_metrics, analyze_restructuring

# Constants
CSV_PATH = "/Users/mingli/Documents/Ming/Investment/Yahoo/portfolio.csv"
TARGET_CAGR = 0.10

def main():
    print("Loading portfolio...")
    df = load_portfolio_holdings(CSV_PATH)
    
    if df.empty:
        print("No valid holdings found.")
        return

    # Get unique symbols
    symbols = df['Symbol'].unique().tolist()
    
    # Fetch live prices
    # Note: Dealing with caching or failures? For MVP, just fetch.
    prices = get_current_prices(symbols)
    
    # Add Current Price to DataFrame
    # Use map to fill prices
    df['Current Price'] = df['Symbol'].map(prices)
    
    # Handle missing prices (e.g. if API failed for some)
    # Fill with 0 or keep as NaN? Better to alert.
    missing_price = df[df['Current Price'].isna()]
    if not missing_price.empty:
        print(f"Warning: Could not fetch prices for: {missing_price['Symbol'].unique()}")
    
    df['Current Price'] = df['Current Price'].fillna(0.0)

    # --- Calculations ---
    df = calculate_metrics(df, TARGET_CAGR)

    # --- Formatting for Output ---
    
    # Create a summary view
    # Group by Symbol? Or show individual lots?
    # User asked for "Stock holding analysis", usually by Ticker.
    # But CAGR is per lot. 
    # Let's show specific lots first (detailed view).
    
    output_df = df.copy()
    
    # Format columns
    output_df['Trade Date'] = output_df['Trade Date'].dt.strftime('%Y-%m-%d')
    output_df['P&L'] = output_df['P&L'].apply(lambda x: f"${x:,.2f}")
    output_df['Market Value'] = output_df['Market Value'].apply(lambda x: f"${x:,.2f}")
    output_df['Cost Basis'] = output_df['Cost Basis'].apply(lambda x: f"${x:,.2f}")
    output_df['CAGR'] = output_df['CAGR'].apply(lambda x: f"{x:.2%}")
    output_df['Goal Diff'] = output_df['Goal Diff'].apply(lambda x: f"{x:+.2%}")
    
    # Status column based on Goal
    output_df['Status'] = df['Goal Diff'].apply(lambda x: "✅" if x >= 0 else "❌")

    cols_to_show = ['Symbol', 'Trade Date', 'Quantity', 'Cost Basis', 'Market Value', 'P&L', 'CAGR', 'Status']
    
    print("\nPortfolio Summary:")
    print(tabulate(output_df[cols_to_show], headers='keys', tablefmt='psql', showindex=False))

    # Total Portfolio Stats
    total_cost = df['Cost Basis'].sum()
    total_value = df['Market Value'].sum()
    total_pnl = total_value - total_cost
    print(f"\nTotal Portfolio Value: ${total_value:,.2f}")
    print(f"Total Cost Basis: ${total_cost:,.2f}")
    print(f"Total P&L: ${total_pnl:,.2f}")

    # --- Restructuring Analysis ---
    analyze_restructuring(df, TARGET_CAGR)

if __name__ == "__main__":
    main()
