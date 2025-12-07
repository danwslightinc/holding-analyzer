import pandas as pd
from datetime import datetime
from tabulate import tabulate
from data_loader import load_portfolio_holdings
from market_data import get_current_prices, get_weekly_changes, get_usd_to_cad_rate
from analysis import calculate_metrics, analyze_restructuring, get_top_movers
from visualize import generate_dashboard, generate_static_preview

# Constants
CSV_PATH = "/Users/mingli/Documents/Ming/Investment/Yahoo/portfolio.csv"
TARGET_CAGR = 0.10

def main():
    print("Loading portfolio...")
    df = load_portfolio_holdings(CSV_PATH)
    
    if df.empty:
        print("No valid holdings found.")
        return ""

    # Get unique symbols
    symbols = df['Symbol'].unique().tolist()
    
    # Fetch live prices and FX rate
    prices = get_current_prices(symbols)
    usd_cad_rate = get_usd_to_cad_rate()
    print(f"USD/CAD Rate: {usd_cad_rate:.4f}")
    
    # Add Current Price to DataFrame
    df['Current Price'] = df['Symbol'].map(prices)
    df['Current Price'] = df['Current Price'].fillna(0.0)

    # --- Calculations ---
    # Convert USD Prices to CAD for proper P&L calculation
    # Heuristic: If symbol ends with '.TO', it's CAD. Else USD (BTC-USD is USD).
    # BTC-USD is usually returned in USD by yahoo.
    
    def get_currency(sym):
        return 'CAD' if sym.endswith('.TO') else 'USD'
        
    df['Currency'] = df['Symbol'].apply(get_currency)
    
    # Normalize Cost Basis to CAD (Assuming input CSV has original currency)
    # Actually, usually brokers export in local currency.
    # If the user bought NVDA in a CAD account, the cost basis might be CAD.
    # But usually 'Purchase Price' is in transaction currency.
    # Let's assume Purchase Price is in the stock's currency.
    
    # We will create a 'CAD Market Value' column
    df['FX Rate'] = df['Currency'].apply(lambda x: usd_cad_rate if x == 'USD' else 1.0)
    
    # Adjust Current Price for 'Current Value (CAD)'
    df['Price (CAD)'] = df['Current Price'] * df['FX Rate']
    
    # Adjust Cost Basis for 'Cost Basis (CAD)'
    # Note: Cost Basis = Quantity * Purchase Price + Commission
    # We assume 'Purchase Price' and 'Commission' in CSV are in the asset's currency.
    df['Cost Basis (Native)'] = (df['Quantity'] * df['Purchase Price']) + df['Commission']
    df['Cost Basis (CAD)'] = df['Cost Basis (Native)'] * df['FX Rate']
    
    df['Market Value (CAD)'] = df['Quantity'] * df['Price (CAD)']
    df['P&L (CAD)'] = df['Market Value (CAD)'] - df['Cost Basis (CAD)']
    
    # CAGR Calculation needs consistent currency. Using the normalized CAD values is safest.
    # We must patch analysis.py logic? 
    # Actually, calculate_metrics uses 'Cost Basis' and 'Market Value' column names.
    # We should overwrite them with CAD values so analysis.py works on normalized data.
    
    df['Cost Basis'] = df['Cost Basis (CAD)']
    df['Market Value'] = df['Market Value (CAD)']
    df['P&L'] = df['P&L (CAD)']

    df = calculate_metrics(df, TARGET_CAGR)

    # --- Formatting for Output ---
    output_df = df.copy()
    
    # Format columns
    output_df['Trade Date'] = output_df['Trade Date'].dt.strftime('%Y-%m-%d')
    output_df['P&L'] = output_df['P&L'].apply(lambda x: f"${x:,.2f}")
    output_df['Market Value'] = output_df['Market Value'].apply(lambda x: f"${x:,.2f}")
    output_df['Cost Basis'] = output_df['Cost Basis'].apply(lambda x: f"${x:,.2f}")
    output_df['CAGR'] = output_df['CAGR'].apply(lambda x: f"{x:.2%}")
    output_df['Goal Diff'] = output_df['Goal Diff'].apply(lambda x: f"{x:+.2%}")
    # Add currency flag for clarity
    output_df['Curr'] = df['Currency']
    
    # Status column based on Goal
    output_df['Status'] = df['Goal Diff'].apply(lambda x: "✅" if x >= 0 else "❌")

    cols_to_show = ['Symbol', 'Curr', 'Trade Date', 'Quantity', 'Cost Basis', 'Market Value', 'P&L', 'CAGR', 'Status']
    
    print("\nPortfolio Summary (All values converted to CAD):")
    print(tabulate(output_df[cols_to_show], headers='keys', tablefmt='psql', showindex=False))

    # Total Portfolio Stats
    total_cost = df['Cost Basis'].sum()
    total_value = df['Market Value'].sum()
    total_pnl = total_value - total_cost
    print(f"\nTotal Portfolio Value: CAD ${total_value:,.2f}")
    print(f"Total Cost Basis:    CAD ${total_cost:,.2f}")
    print(f"Total P&L:           CAD ${total_pnl:,.2f}")

    # --- Weekly Performance ---
    print("\nCalculating Weekly Performance...")
    weekly_changes = get_weekly_changes(symbols)
    movers_summary = get_top_movers(weekly_changes)
    print(movers_summary)
    
    # Update restructuring analysis to output CAD context explicitly if needed, but since df values are now CAD, it should just work.
    
    # --- Restructuring Analysis ---
    analyze_restructuring(df, TARGET_CAGR)

    # --- Visualization ---
    print("\nGenerating interactive dashboard...")
    from visualize import generate_dashboard, generate_static_preview
    generate_dashboard(df, TARGET_CAGR)
    generate_static_preview(df, TARGET_CAGR)
    
    return movers_summary

if __name__ == "__main__":
    main()
