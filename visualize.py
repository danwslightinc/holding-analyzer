import matplotlib.pyplot as plt
import pandas as pd
import os

def plot_portfolio_allocation(df, save_path='portfolio_allocation.png'):
    """
    Generates a pie chart of the portfolio allocation by Market Value.
    """
    if df.empty: return

    # Aggregate by Symbol
    allocation = df.groupby('Symbol')['Market Value'].sum()
    
    # Filter out very small positions for cleaner chart
    total_val = allocation.sum()
    if total_val == 0: return

    # Sort and keep top N, group others?
    # For now, just plot all.
    
    plt.figure(figsize=(10, 8))
    plt.pie(allocation, labels=allocation.index, autopct='%1.1f%%', startangle=140)
    plt.title(f'Portfolio Allocation (Total: ${total_val:,.2f})')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    plt.savefig(save_path)
    plt.close()
    print(f"Saved allocation chart to {save_path}")

def plot_cagr_performance(df, target_cagr, save_path='cagr_performance.png'):
    """
    Generates a bar chart comparing asset CAGR to the target.
    """
    if df.empty: return

    # Filter out CASH.TO or weird outliers if requested? 
    # Let's keep everything but cap visual range if needed.
    # Group by Symbol? (Simpler if we assume one row per symbol for this chart)
    # The main DF might have multiple rows per symbol if loaded that way, 
    # but our current analysis tends to keep lots separate. 
    # Let's aggregate weighted CAGR or just plot individual lots.
    # To be safe, let's plot individual lots with Date info if needed, 
    # OR better: Plot by Symbol (taking weighted avg if multiple).
    
    # Let's just plot the DataFrame rows directly, labeled by Symbol + Date maybe?
    # Or just Symbol if unique.
    
    plot_data = df.copy()
    plot_data['Label'] = plot_data['Symbol'] # + " (" + plot_data['Trade Date'].dt.strftime('%Y-%m') + ")"
    
    # Clamp extreme CAGRs for visualization (e.g. BTC's huge number)
    # Maybe limit to [-100%, +200%] for readability?
    # Let's just plot raw for now, user can see the craziness.
    # Actually, huge outliers break charts. 
    # Let's filter out anything > 500% or < -100% just for the chart scaling?
    # Or use log scale?
    # Let's just apply a cap for the visual.
    
    cap = 5.0 # 500%
    plot_data['CAGR_Visual'] = plot_data['CAGR'].clip(upper=cap, lower=-1.0)
    
    plt.figure(figsize=(12, 6))
    
    colors = ['green' if x >= target_cagr else 'red' for x in plot_data['CAGR']]
    
    plt.bar(plot_data['Label'], plot_data['CAGR_Visual'], color=colors)
    
    # Add target line
    plt.axhline(y=target_cagr, color='blue', linestyle='--', label=f'Target ({target_cagr:.0%})')
    
    plt.title('Asset CAGR vs Target (Capped at 500% for visibility)')
    plt.xlabel('Asset')
    plt.ylabel('CAGR')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    
    plt.savefig(save_path)
    plt.close()
    print(f"Saved performance chart to {save_path}")
