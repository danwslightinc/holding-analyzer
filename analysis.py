import pandas as pd
from datetime import datetime
from tabulate import tabulate

def calculate_metrics(df, target_cagr=0.10):
    """
    Calculates P&L, Market Value, Days Held, and CAGR for the dataframe.
    """
    # Cost Basis = (Purchase Price * Quantity) + Commission
    df['Cost Basis'] = (df['Purchase Price'] * df['Quantity']) + df['Commission']
    
    # Market Value = Current Price * Quantity (Current Price must be populated before calling this)
    df['Market Value'] = df['Current Price'] * df['Quantity']
    
    # P&L ($)
    df['P&L'] = df['Market Value'] - df['Cost Basis']
    
    # Days Held
    today = datetime.now()
    df['Days Held'] = (today - df['Trade Date']).dt.days
    # Avoid division by zero or negative days
    df['Days Held'] = df['Days Held'].apply(lambda x: max(x, 1))
    
    # CAGR
    # Formula: (End / Start) ^ (365 / Days) - 1
    def calculate_cagr_row(row):
        if row['Cost Basis'] <= 0: return 0.0
        if row['Market Value'] <= 0: return -1.0 
        return (row['Market Value'] / row['Cost Basis']) ** (365.0 / row['Days Held']) - 1

    df['CAGR'] = df.apply(calculate_cagr_row, axis=1)

    # Goal Check (Diff from Target)
    df['Goal Diff'] = df['CAGR'] - target_cagr
    
    return df

def analyze_restructuring(df, target_cagr=0.10):
    """
    Analyzes portfolio to suggest restructuring moves.
    Excludes CASH.TO from analysis.
    """
    print("\n" + "="*50)
    print("RESTRUCTURING ANALYSIS")
    print("="*50)

    # Filter out CASH.TO
    # Note: Case sensitive check usually, but good to be robust.
    equity_df = df[~df['Symbol'].str.contains('CASH.TO', case=False, na=False)].copy()
    
    if equity_df.empty:
        print("No equity holdings found (non-CASH.TO).")
        return

    # Identify Laggards
    laggards = equity_df[equity_df['CAGR'] < target_cagr].copy()
    winners = equity_df[equity_df['CAGR'] >= target_cagr].copy()

    if laggards.empty:
        print(f"🎉 Amazing! All your equity holdings are meeting the {target_cagr:.1%} target.")
        return

    print(f"\n1. IDENTIFIED UNDERPERFORMERS (< {target_cagr:.1%} CAGR)")
    print("-" * 50)
    
    laggards_summary = laggards[['Symbol', 'Trade Date', 'Cost Basis', 'Market Value', 'CAGR']].copy()
    laggards_summary['Trade Date'] = laggards_summary['Trade Date'].dt.strftime('%Y-%m-%d')
    laggards_summary['Cost Basis'] = laggards_summary['Cost Basis'].apply(lambda x: f"${x:,.2f}")
    laggards_summary['Market Value'] = laggards_summary['Market Value'].apply(lambda x: f"${x:,.2f}")
    laggards_summary['CAGR'] = laggards_summary['CAGR'].apply(lambda x: f"{x:.2%}")
    
    print(tabulate(laggards_summary, headers='keys', tablefmt='psql', showindex=False))

    # Calculate Capital to Reallocate
    capital_tied_up = laggards['Market Value'].sum()
    opportunity_cost = laggards['P&L'].sum() # This is realized loss if sold today (unrealized currently)
    
    print(f"\n2. CAPITAL ANALYSIS")
    print("-" * 50)
    print(f"Capital tied up in underperformers: ${capital_tied_up:,.2f}")
    print(f"Unrealized P&L in these positions:  ${opportunity_cost:,.2f}")

    # Simulation
    # Calculate weighted CAGR of entire portfolio (excluding CASH)
    def get_portfolio_cagr(d):
        total_mv = d['Market Value'].sum()
        total_cb = d['Cost Basis'].sum()
        if total_cb <= 0: return 0
        # This is a rough approximation of "Portfolio CAGR". 
        # A true portfolio CAGR is hard with different time periods.
        # We will use Total Return % for simplicity to show 'Efficiency'.
        # Or simpler: What if we take that $Capital and it earns 10%?
        return (total_mv - total_cb)

    print(f"\n3. REALLOCATION SCENARIO")
    print("-" * 50)
    print(f"If you sell these positions and reinvest the ${capital_tied_up:,.0f}...")
    
    # Scenario A: Reinvest at Target CAGR (10%)
    # Let's project 1 year forward
    projected_val_target = capital_tied_up * (1 + target_cagr)
    gain_target = projected_val_target - capital_tied_up
    
    print(f"A) At target return ({target_cagr:.0%}):")
    print(f"   You would generate +${gain_target:,.2f} in profit over the next year.")
    
    # Scenario B: Reinvest in your Top Winner
    if not winners.empty:
        # Find top winner by CAGR
        top_winner = winners.loc[winners['CAGR'].idxmax()]
        winner_cagr = top_winner['CAGR']
        winner_sym = top_winner['Symbol']
        
        # Cap unreasonable CAGRs for projection (e.g. if > 100%, maybe scale back?)
        # But user wants to see "what if".
        projected_val_winner = capital_tied_up * (1 + winner_cagr)
        gain_winner = projected_val_winner - capital_tied_up
        
        print(f"B) At your best asset's current run rate ({winner_sym} @ {winner_cagr:.1%}):")
        print(f"   You would generate +${gain_winner:,.2f} in profit over the next year.")
        print(f"   (Warning: Past performance doesn't guarantee future results!)")

    print("\nRecommendation:")
    print("Consider liquidating the underperformers listed above and re-allocating")
    print("to your winning positions or an index fund tracking your target.")

def get_top_movers(changes_dict):
    """
    Returns a formatted string summarizing Top 3 Gainers and Losers.
    """
    if not changes_dict: return ""

    sorted_changes = sorted(changes_dict.items(), key=lambda x: x[1], reverse=True)
    
    # Top 3 Gainers
    gainers = sorted_changes[:3]
    # Top 3 Losers (reverse end)
    losers = sorted_changes[-3:]
    losers.reverse() # Sort worst first
    
    summary = "\nWeekly Top Gainers:\n"
    for sym, change in gainers:
        summary += f"  🟢 {sym}: {change:+.2%}\n"
        
    summary += "\nWeekly Top Losers:\n"
    for sym, change in losers:
        summary += f"  🔴 {sym}: {change:+.2%}\n"
        
    return summary

def get_market_summary(indices_dict):
    """
    Returns a formatted string for market indices.
    """
    if not indices_dict: return ""
    
    summary = "\n🌍 Market Benchmarks (Weekly):\n"
    for name, change in indices_dict.items():
        icon = "🟢" if change >= 0 else "🔴"
        summary += f"  {icon} {name}: {change:+.2%}\n"
        
    return summary
