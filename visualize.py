import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import pandas as pd

def generate_static_preview(df, target_cagr, save_path='dashboard_preview.png'):
    """
    Generates a static PNG summary for email embedding (since HTML/JS is blocked in emails).
    """
    if df.empty: return

    # Allocation Data
    alloc_df = df.groupby('Symbol')['Market Value'].sum()
    
    # CAGR Data
    cagr_df = df.copy()
    cagr_df['CAGR_Visual'] = cagr_df['CAGR'].clip(upper=3.0, lower=-1.0)
    colors = ['green' if x >= target_cagr else 'red' for x in cagr_df['CAGR']]

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 1. Pie
    ax1.pie(alloc_df, labels=alloc_df.index, autopct='%1.1f%%', startangle=140)
    ax1.set_title('Portfolio Allocation')
    
    # 2. Bar
    ax2.bar(cagr_df['Symbol'], cagr_df['CAGR_Visual'], color=colors)
    ax2.axhline(y=target_cagr, color='blue', linestyle='--', label='Target')
    ax2.set_title('CAGR vs Target (Capped)')
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Static preview saved to: {save_path}")

def generate_dashboard(df, target_cagr, save_path='portfolio_dashboard.html'):
    """
    Generates an interactive HTML dashboard with:
    1. Portfolio Allocation (Pie)
    2. CAGR Performance (Bar)
    """
    if df.empty: return

    # --- Prepare Data ---
    
    # Allocation Data
    alloc_df = df.groupby('Symbol')['Market Value'].sum().reset_index()
    total_val = alloc_df['Market Value'].sum()
    
    # CAGR Data (Cleaned)
    cagr_df = df.copy()
    # Cap visual outliers for the chart so it doesn't break
    cagr_df['CAGR_Visual'] = cagr_df['CAGR'].clip(upper=3.0, lower=-1.0) 
    cagr_df['Color'] = cagr_df['CAGR'].apply(lambda x: 'green' if x >= target_cagr else 'red')
    
    # --- Create Subplots ---
    # Row 1, Col 1: Pie Chart
    # Row 1, Col 2: Bar Chart
    
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "domain"}, {"type": "xy"}]],
        subplot_titles=(f"Portfolio Allocation (Total: ${total_val:,.0f})", f"CAGR Performance (Target: {target_cagr:.0%})")
    )
    
    # 1. Pie Chart
    fig.add_trace(
        go.Pie(
            labels=alloc_df['Symbol'], 
            values=alloc_df['Market Value'],
            name="Allocation",
            hole=0.4,
            hoverinfo="label+percent+value"
        ),
        row=1, col=1
    )
    
    # 2. Bar Chart
    # We color bars individually based on target
    fig.add_trace(
        go.Bar(
            x=cagr_df['Symbol'],
            y=cagr_df['CAGR_Visual'],
            text=cagr_df['CAGR'].apply(lambda x: f"{x:.1%}"),
            marker_color=cagr_df['Color'],
            name="CAGR",
            hovertemplate="<b>%{x}</b><br>CAGR: %{text}<extra></extra>"
        ),
        row=1, col=2
    )

    # Add Target Line to Bar Chart
    fig.add_shape(
        type="line",
        x0=-0.5, x1=len(cagr_df)-0.5,
        y0=target_cagr, y1=target_cagr,
        line=dict(color="blue", width=2, dash="dash"),
        row=1, col=2
    )

    # --- Layout / Styling ---
    fig.update_layout(
        title_text="Stock Portfolio Analysis Dashboard",
        template="plotly_dark",
        height=600,
        showlegend=True
    )
    
    # Save
    fig.write_html(save_path)
    print(f"Interactive dashboard saved to: {save_path}")
