import os
import pandas as pd
from datetime import datetime
from tabulate import tabulate
from dotenv import load_dotenv
from data_loader import load_portfolio_holdings, load_portfolio_from_db
from market_data import get_current_prices, get_weekly_changes, get_usd_to_cad_rate, get_market_indices_change, get_fundamental_data, get_technical_data, get_latest_news, get_dividend_calendar
from analysis import calculate_metrics, analyze_restructuring, analyze_pnl, get_top_movers, get_market_summary, analyze_sector_exposure
from visualize import generate_dashboard, generate_static_preview

# Load environment variables
load_dotenv()

# Constants
TARGET_CAGR = float(os.getenv("TARGET_CAGR", 0.08))

def main():
    print("Loading portfolio from Database...")
    df, realized_pnl = load_portfolio_from_db()
    
    if df.empty:
        print("No valid holdings found.")
        return ""

    # Get unique symbols
    symbols = df['Symbol'].unique().tolist()
    
    # Fetch live prices and FX rate
    prices = get_current_prices(symbols)
    usd_cad_rate = get_usd_to_cad_rate()
    print(f"USD/CAD Rate: {usd_cad_rate:.4f}")
    
    # Fetch Fundamentals (Quant-Mental)
    fundamentals = get_fundamental_data(symbols)
    technicals = get_technical_data(symbols)
    news = get_latest_news(symbols)
    div_calendar = get_dividend_calendar(symbols)

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
    
    # CRITICAL: Overwrite columns with CAD values BEFORE calling calculate_metrics
    # calculate_metrics re-computes Cost Basis and Market Value from Price/Qty/Commission
    # So we must convert the input columns to CAD.
    
    # 1. Update Prices to CAD
    df['Current Price'] = df['Price (CAD)']
    df['Purchase Price'] = df['Purchase Price'] * df['FX Rate']
    
    # 2. Update Commission to CAD
    df['Commission'] = df['Commission'] * df['FX Rate']
    
    # 3. Explicitly set derived columns (just to be safe, though calculate_metrics will re-do roughly same)
    df['Cost Basis'] = df['Cost Basis (CAD)']
    df['Market Value'] = df['Market Value (CAD)']
    df['P&L'] = df['P&L (CAD)']

    df = calculate_metrics(df, TARGET_CAGR)

    # --- Formatting for Output ---
    output_df = df.copy()
    
    # Format columns
    output_df['Trade Date'] = output_df['Trade Date'].dt.strftime('%Y/%m/%d')
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
    
    # --- Market Benchmarks ---
    print("Fetching Market Benchmarks...")
    indices_changes = get_market_indices_change()
    market_summary = get_market_summary(indices_changes)
    print(market_summary)

    # Update restructuring analysis to output CAD context explicitly if needed, but since df values are now CAD, it should just work.
    
    # --- Restructuring Analysis ---
    analyze_restructuring(df, TARGET_CAGR)
    
    # --- P&L Analysis ---
    pnl_summary = analyze_pnl(df, realized_pnl=realized_pnl, usd_to_cad=usd_cad_rate)
    
    # --- Sector Exposure & Rebalancing ---
    _, sector_summary = analyze_sector_exposure(df, fundamentals)

    # --- Visualization ---
    print("\nGenerating interactive dashboard with Quant-Mental view...")
    from visualize import generate_dashboard, generate_static_preview
    generate_dashboard(df, TARGET_CAGR, fundamentals=fundamentals, technicals=technicals, news=news, 
                       dividend_calendar=div_calendar, realized_pnl=realized_pnl, usd_to_cad=usd_cad_rate)
    generate_static_preview(df, TARGET_CAGR, fundamentals, realized_pnl=realized_pnl, usd_to_cad=usd_cad_rate)
    
    return movers_summary + "\n" + market_summary + "\n" + pnl_summary + "\n" + sector_summary

if __name__ == "__main__":
    main()
