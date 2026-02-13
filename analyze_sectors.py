import pandas as pd
import yfinance as yf
from data_loader import load_portfolio_holdings
from market_data import get_current_prices, get_usd_to_cad_rate
from tabulate import tabulate
import matplotlib.pyplot as plt

# Sector mapping for symbols
SECTOR_MAP = {
    'AC.TO': 'Industrials',
    'ACB.TO': 'Healthcare',
    'AVUV': 'Index Fund',
    'BTC-USD': 'Cryptocurrency',
    'CASH.TO': 'Cash',
    'CM.TO': 'Financial Services',
    'COST': 'Consumer Defensive',
    'MSFT': 'Technology',
    'NVDA': 'Technology',
    'SAVA': 'Healthcare',
    'SLV': 'Commodities',
    'TD.TO': 'Financial Services',
    'UNH': 'Healthcare',
    'V': 'Financial Services',
    'VDY.TO': 'Index Fund',
    'VOO': 'Index Fund',
    'WCP.TO': 'Energy',
    'XEI.TO': 'Index Fund',
    'XIU.TO': 'Index Fund',
    'XQQ.TO': 'Index Fund',
    'YGMZ': 'Industrials'
}

def analyze_sectors():
    """
    Analyzes portfolio sector distribution.
    """
    # Load portfolio
    df = load_portfolio_holdings('portfolio.csv')
    
    if df.empty:
        print("No valid holdings found.")
        return
    
    # Get prices
    symbols = df['Symbol'].unique().tolist()
    prices = get_current_prices(symbols)
    usd_cad_rate = get_usd_to_cad_rate()
    
    # Add current price
    df['Current Price'] = df['Symbol'].map(prices).fillna(0.0)
    
    # Currency conversion
    df['Currency'] = df['Symbol'].apply(lambda x: 'CAD' if x.endswith('.TO') else 'USD')
    df['FX Rate'] = df['Currency'].apply(lambda x: usd_cad_rate if x == 'USD' else 1.0)
    df['Price (CAD)'] = df['Current Price'] * df['FX Rate']
    df['Market Value (CAD)'] = df['Quantity'] * df['Price (CAD)']
    
    # Add sector information
    df['Sector'] = df['Symbol'].map(SECTOR_MAP).fillna('Unknown')
    
    # Group by sector
    sector_summary = df.groupby('Sector').agg({
        'Market Value (CAD)': 'sum'
    }).reset_index()
    
    sector_summary.columns = ['Sector', 'Market Value']
    sector_summary = sector_summary.sort_values('Market Value', ascending=False)
    
    # Calculate percentages
    total_value = sector_summary['Market Value'].sum()
    sector_summary['Percentage'] = (sector_summary['Market Value'] / total_value) * 100
    
    # Display results
    print("\n" + "="*60)
    print("SECTOR DISTRIBUTION ANALYSIS")
    print("="*60)
    
    # Format for display
    display_df = sector_summary.copy()
    display_df['Market Value'] = display_df['Market Value'].apply(lambda x: f"${x:,.2f}")
    display_df['Percentage'] = display_df['Percentage'].apply(lambda x: f"{x:.1f}%")
    
    print("\n" + tabulate(display_df, headers='keys', tablefmt='psql', showindex=False))
    print(f"\nTotal Portfolio Value: ${total_value:,.2f}")
    
    # Create pie chart
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.Set3(range(len(sector_summary)))
    
    wedges, texts, autotexts = ax.pie(
        sector_summary['Market Value'],
        labels=sector_summary['Sector'],
        autopct='%1.1f%%',
        startangle=90,
        colors=colors
    )
    
    # Enhance text
    for text in texts:
        text.set_fontsize(11)
        text.set_fontweight('bold')
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')
    
    ax.set_title('Portfolio Sector Distribution', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('sector_distribution.png', dpi=100, bbox_inches='tight')
    plt.close()
    print("\nSector distribution chart saved to: sector_distribution.png")
    
    # Diversification analysis
    print("\n" + "="*60)
    print("DIVERSIFICATION ANALYSIS")
    print("="*60)
    
    # Check concentration risk
    top_sector_pct = sector_summary['Percentage'].iloc[0]
    top_sector_name = sector_summary['Sector'].iloc[0]
    
    print(f"\nLargest Sector: {top_sector_name} ({top_sector_pct:.1f}%)")
    
    if top_sector_pct > 40:
        print("⚠️  HIGH CONCENTRATION RISK: Over 40% in one sector")
        print("   Consider diversifying to reduce sector-specific risk")
    elif top_sector_pct > 30:
        print("⚠️  MODERATE CONCENTRATION: 30-40% in one sector")
        print("   Acceptable but monitor for over-concentration")
    else:
        print("✅ WELL DIVERSIFIED: No single sector dominates")
    
    # Count sectors
    num_sectors = len(sector_summary)
    print(f"\nNumber of Sectors: {num_sectors}")
    
    if num_sectors < 5:
        print("⚠️  LIMITED DIVERSIFICATION: Consider adding more sectors")
    else:
        print("✅ GOOD SECTOR COVERAGE")

if __name__ == "__main__":
    analyze_sectors()
