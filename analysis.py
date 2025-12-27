import pandas as pd
from datetime import datetime
from tabulate import tabulate

def calculate_metrics(df, target_cagr=0.10):
    """
    Calculates P&L, Market Value, Days Held, and CAGR for the dataframe.
    Uses transaction dates from CSV.
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
    
    # CAGR vs Simple Return
    # If held < 1 year, return Simple Return to avoid extreme annualized volatility.
    # Otherwise, return CAGR.
    def calculate_cagr_row(row):
        if row['Cost Basis'] <= 0: return 0.0
        if row['Market Value'] <= 0: return -1.0 
        
        if row['Days Held'] < 365:
            return (row['Market Value'] / row['Cost Basis']) - 1
            
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
    
    # Top 3 Gainers (Strictly Positive)
    gainers = [x for x in sorted_changes if x[1] > 0][:3]
    
    # Top 3 Losers (Strictly Negative)
    # We want the absolute bottom of the list, provided they are negative
    losers = [x for x in sorted_changes if x[1] < 0]
    # Take the worst 3 (last 3 of the descending list)
    losers = losers[-3:]
    losers.reverse() # Sort worst first (most negative at top)
    
    summary = "\nWeekly Top Gainers:\n"
    if gainers:
        for sym, change in gainers:
            summary += f"  🟢 {sym}: {change:+.2%}\n"
    else:
        summary += "  (None)\n"
        
    summary += "\nWeekly Top Losers:\n"
    if losers:
        for sym, change in losers:
            summary += f"  🔴 {sym}: {change:+.2%}\n"
    else:
        summary += "  (None)\n"
        
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

def analyze_pnl(df):
    """
    Analyzes portfolio P&L (Profit & Loss) showing absolute dollar gains/losses.
    Excludes CASH.TO from analysis.
    Returns a formatted summary string for email reports.
    """
    print("\n" + "="*50)
    print("P&L ANALYSIS (Profit & Loss) - All values in CAD")
    print("="*50)

    # Filter out CASH.TO
    equity_df = df[~df['Symbol'].str.contains('CASH.TO', case=False, na=False)].copy()
    
    if equity_df.empty:
        print("No equity holdings found (non-CASH.TO).")
        return ""

    # Calculate simple return percentage
    equity_df['Return %'] = (equity_df['P&L'] / equity_df['Cost Basis']) * 100
    
    # Sort by Return % for ranking
    equity_df_sorted = equity_df.sort_values('Return %', ascending=False)
    
    # Winners and Losers
    winners = equity_df_sorted[equity_df_sorted['P&L'] > 0].copy()
    losers = equity_df_sorted[equity_df_sorted['P&L'] < 0].sort_values('Return %', ascending=True).copy()
    
    # Build email summary
    email_summary = "\n💰 P&L SUMMARY\n"
    email_summary += "-" * 30 + "\n"
    
    print(f"\n💰 WINNERS (Profitable Positions)")
    print("-" * 50)
    if not winners.empty:
        winners_summary = winners[['Symbol', 'Cost Basis', 'Market Value', 'P&L', 'Return %']].copy()
        winners_summary['Cost Basis'] = winners_summary['Cost Basis'].apply(lambda x: f"${x:,.2f}")
        winners_summary['Market Value'] = winners_summary['Market Value'].apply(lambda x: f"${x:,.2f}")
        winners_summary['P&L'] = winners_summary['P&L'].apply(lambda x: f"${x:,.2f}")
        winners_summary['Return %'] = winners_summary['Return %'].apply(lambda x: f"{x:.2f}%")
        print(tabulate(winners_summary, headers='keys', tablefmt='psql', showindex=False))
        
        total_gains = winners['P&L'].sum()
        print(f"\nTotal Gains: ${total_gains:,.2f}")
        
        # Add top 3 winners to email
        email_summary += "Top Winners:\n"
        for idx, (_, row) in enumerate(winners.head(3).iterrows(), 1):
            email_summary += f"  {idx}. {row['Symbol']}: ${row['P&L']:,.2f} ({row['Return %']:.1f}%)\n"
    else:
        print("No profitable positions.")
    
    print(f"\n📉 LOSERS (Loss Positions)")
    print("-" * 50)
    if not losers.empty:
        losers_summary = losers[['Symbol', 'Cost Basis', 'Market Value', 'P&L', 'Return %']].copy()
        losers_summary['Cost Basis'] = losers_summary['Cost Basis'].apply(lambda x: f"${x:,.2f}")
        losers_summary['Market Value'] = losers_summary['Market Value'].apply(lambda x: f"${x:,.2f}")
        losers_summary['P&L'] = losers_summary['P&L'].apply(lambda x: f"${x:,.2f}")
        losers_summary['Return %'] = losers_summary['Return %'].apply(lambda x: f"{x:.2f}%")
        print(tabulate(losers_summary, headers='keys', tablefmt='psql', showindex=False))
        
        total_losses = losers['P&L'].sum()
        print(f"\nTotal Losses: ${total_losses:,.2f}")
        
        # Add top 3 losers to email
        email_summary += "\nTop Losers:\n"
        for idx, (_, row) in enumerate(losers.head(3).iterrows(), 1):
            email_summary += f"  {idx}. {row['Symbol']}: ${row['P&L']:,.2f} ({row['Return %']:.1f}%)\n"
    else:
        print("No loss positions.")
    
    # Overall Summary
    total_pnl = equity_df['P&L'].sum()
    total_cost = equity_df['Cost Basis'].sum()
    total_value = equity_df['Market Value'].sum()
    overall_return = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
    
    print(f"\n📊 OVERALL P&L SUMMARY")
    print("-" * 50)
    print(f"Total Cost Basis:    ${total_cost:,.2f}")
    print(f"Total Market Value:  ${total_value:,.2f}")
    print(f"Total P&L:           ${total_pnl:,.2f}")
    print(f"Overall Return:      {overall_return:.2f}%")
    
    # Add overall to email
    email_summary += f"\nOverall P&L: ${total_pnl:,.2f} ({overall_return:.1f}%)\n"
    
    return email_summary


from market_data import ETF_SECTOR_WEIGHTS

def analyze_sector_exposure(df, fundamentals):
    """
    Calculates look-through sector exposure and prints a summary table.
    Helps identifying rebalancing needs.
    """
    print("\n" + "="*50)
    print("SECTOR EXPOSURE ANALYSIS (Look-Through) - All values in CAD")
    print("="*50)
    
    if not fundamentals:
        print("No fundamentals data available.")
        return

    sector_map = {}
    total_val = df['Market Value'].sum()
    
    for _, row in df.iterrows():
        sym = row['Symbol']
        val = row['Market Value']
        base_sector = fundamentals.get(sym, {}).get('Sector', 'Unknown')
        
        if sym in ETF_SECTOR_WEIGHTS:
            weights = ETF_SECTOR_WEIGHTS[sym]
            remaining_weight = 1.0
            for sec, w in weights.items():
                amt = val * w
                sector_map[sec] = sector_map.get(sec, 0) + amt
                remaining_weight -= w
            
            if remaining_weight > 0.001:
                 sector_map['Other'] = sector_map.get('Other', 0) + (val * remaining_weight)
        else:
            sector_map[base_sector] = sector_map.get(base_sector, 0) + val
            
    # Convert to DF
    sector_df = pd.DataFrame(list(sector_map.items()), columns=['Sector', 'Market Value (CAD)'])
    sector_df['Allocation %'] = (sector_df['Market Value (CAD)'] / total_val) * 100
    sector_df = sector_df.sort_values('Market Value (CAD)', ascending=False)
    
    # Format for printing
    print_df = sector_df.copy()
    print_df['Market Value (CAD)'] = print_df['Market Value (CAD)'].apply(lambda x: f"${x:,.2f}")
    print_df['Allocation %'] = print_df['Allocation %'].apply(lambda x: f"{x:.1f}%")
    
    output_str = "\n" + "="*50 + "\nSECTOR EXPOSURE ANALYSIS (Look-Through)\n" + "="*50 + "\n"
    output_str += tabulate(print_df, headers='keys', tablefmt='psql', showindex=False)
    
    # Rebalancing Alerts
    if not sector_df.empty:
        top_sector = sector_df.iloc[0]
        if top_sector['Allocation %'] > 30:
            output_str += f"\n\n⚠️ Concentration Alert: {top_sector['Sector']} is {top_sector['Allocation %']:.1f}% of portfolio."
            output_str += "\nAction: Consider trimming winners if this exceeds your maximum sector allocation (Default Alert > 30%)."

    print(output_str)
    return sector_df, output_str
