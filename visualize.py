import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import pandas as pd

ETF_SECTOR_WEIGHTS = {
    'VOO': {
        'Technology': 0.31, 'Financial Services': 0.13, 'Healthcare': 0.12, 
        'Consumer Cyclical': 0.10, 'Communication Services': 0.09, 'Industrials': 0.08, 
        'Consumer Defensive': 0.06, 'Energy': 0.04, 'Real Estate': 0.02, 'Basic Materials': 0.02, 'Utilities': 0.03
    },
    'XQQ.TO': {
        'Technology': 0.51, 'Communication Services': 0.16, 'Consumer Cyclical': 0.13, 
        'Healthcare': 0.06, 'Consumer Defensive': 0.04, 'Industrials': 0.04, 'Utilities': 0.01,
        'Financial Services': 0.01
    },
    # Assumption for XIU (TSX 60)
    'XIU.TO': {
        'Financial Services': 0.35, 'Energy': 0.18, 'Industrials': 0.12, 
        'Basic Materials': 0.12, 'Technology': 0.09, 'Utilities': 0.05, 
        'Communication Services': 0.05, 'Consumer Defensive': 0.03, 'Consumer Cyclical': 0.01
    },
    # Assumption for XEI (High Div)
    'XEI.TO': {
        'Energy': 0.30, 'Financial Services': 0.30, 'Utilities': 0.15, 
        'Communication Services': 0.10, 'Real Estate': 0.05, 'Basic Materials': 0.05, 'Industrials': 0.05
    }
}

def generate_static_preview(df, target_cagr, save_path='dashboard_preview.png'):
    """
    Generates a static PNG summary for email embedding (since HTML/JS is blocked in emails).
    Includes: Allocation (pie), CAGR (bar), and P&L (horizontal bar).
    """
    if df.empty: return

    # Allocation Data (Sorted for Bar Chart)
    alloc_s = df.groupby('Symbol')['Market Value'].sum().sort_values(ascending=True)
    
    # CAGR Data (Filter out Crypto/BTC to fix scaling)
    # Using case-insensitive check for 'BTC'
    cagr_df = df[~df['Symbol'].str.contains('BTC', case=False, na=False)].copy()
    cagr_df['CAGR_Visual'] = cagr_df['CAGR'].clip(upper=3.0, lower=-1.0)
    cagr_colors = ['green' if x >= target_cagr else 'red' for x in cagr_df['CAGR']]
    
    # P&L Data
    pnl_df = df.copy()
    pnl_df['Return %'] = (pnl_df['P&L'] / pnl_df['Cost Basis']) * 100
    pnl_df = pnl_df.sort_values('P&L', ascending=True)
    pnl_colors = ['green' if x > 0 else 'red' for x in pnl_df['P&L']]

    # Create 2x2 grid
    fig = plt.figure(figsize=(16, 12))  # Taller figure
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.3, wspace=0.3)
    
    # Row 1, Col 1: Allocation (Horizontal Bar) - Improved Readability
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.barh(alloc_s.index, alloc_s.values, color='#4facfe')
    ax1.set_title('Portfolio Allocation ($)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Market Value')
    ax1.grid(axis='x', alpha=0.3, linestyle='--')
    
    # Row 1, Col 2: CAGR Bar Chart (No BTC)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(cagr_df['Symbol'], cagr_df['CAGR_Visual'], color=cagr_colors)
    ax2.axhline(y=target_cagr, color='blue', linestyle='--', label=f'Target {target_cagr:.0%}')
    ax2.set_title('CAGR vs Target (Excl. BTC)', fontsize=14, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # Row 2: P&L Horizontal Bar Chart (spanning both columns)
    ax3 = fig.add_subplot(gs[1, :])
    ax3.barh(pnl_df['Symbol'], pnl_df['P&L'], color=pnl_colors)
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax3.set_title('P&L by Holding ($)', fontsize=14, fontweight='bold')
    ax3.set_xlabel('P&L ($)')
    ax3.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"Static preview saved to: {save_path}")

def generate_dashboard(df, target_cagr, fundamentals=None, technicals=None, save_path='portfolio_dashboard.html'):
    """
    Generates an interactive HTML dashboard with:
    1. Portfolio Allocation (Pie) and CAGR Performance (Bar) - Top Row
    2. P&L Performance (Bar) - Middle Row
    3. Quant-Mental Analysis (Table) - Bottom Row (if fundamentals provided)
    """
    if df.empty: return

    # --- Prepare Data ---
    
    # Allocation Data
    alloc_df = df.groupby('Symbol')['Market Value'].sum().reset_index()
    total_val = alloc_df['Market Value'].sum()

    # Sector Allocation Data
    if fundamentals:
        # Look-Through Sector Analysis
        sector_map = {}
        for _, row in df.iterrows():
            sym = row['Symbol']
            val = row['Market Value']
            # Get base sector from fundamentals
            base_sector = fundamentals.get(sym, {}).get('Sector', 'Unknown')
            
            if sym in ETF_SECTOR_WEIGHTS:
                # Distribute value for known ETFs
                weights = ETF_SECTOR_WEIGHTS[sym]
                remaining_weight = 1.0
                for sec, w in weights.items():
                    amount = val * w
                    sector_map[sec] = sector_map.get(sec, 0) + amount
                    remaining_weight -= w
                
                if remaining_weight > 0.001:
                    sector_map['Other'] = sector_map.get('Other', 0) + (val * remaining_weight)
            else:
                # Standard Stock or Unmapped ETF
                sector_map[base_sector] = sector_map.get(base_sector, 0) + val
                
        sector_df = pd.DataFrame(list(sector_map.items()), columns=['Sector', 'Market Value'])
        sector_df = sector_df.sort_values('Market Value', ascending=False)
    else:
        sector_df = pd.DataFrame({'Sector': ['Unknown'], 'Market Value': [total_val]})
    
    # CAGR Data (Cleaned)
    cagr_df = df.copy()
    cagr_df['CAGR_Visual'] = cagr_df['CAGR'].clip(upper=3.0, lower=-1.0) 
    cagr_df['Color'] = cagr_df['CAGR'].apply(lambda x: 'green' if x >= target_cagr else 'red')
    
    # P&L Data
    pnl_df = df.copy()
    pnl_df['Return %'] = (pnl_df['P&L'] / pnl_df['Cost Basis']) * 100
    pnl_df['PnL_Color'] = pnl_df['P&L'].apply(lambda x: 'green' if x > 0 else 'red')
    pnl_df = pnl_df.sort_values('P&L', ascending=True)
    
    # Quant-Mental Table Data
    table_rows = []
    if fundamentals:
        # Prepare table data
        qm_df = df.copy().sort_values('Symbol')
        
        symbols = []
        theses = []
        catalysts = []
        kill_switches = []
        convictions = []
        timeframes = []
        rsis = []
        earnings = []
        ex_divs = []
        yields = []
        pes = []
        growths = []
        recs = []
        
        for _, row in qm_df.iterrows():
            sym = row['Symbol']
            symbols.append(sym)
            theses.append(row.get('Thesis', ''))
            catalysts.append(row.get('Catalyst', ''))
            kill_switches.append(row.get('Kill Switch', ''))
            convictions.append(row.get('Conviction', ''))
            timeframes.append(row.get('Timeframe', ''))
            
            # Technicals
            if technicals and sym in technicals:
                rsi_val = technicals[sym].get('RSI', 'N/A')
                if isinstance(rsi_val, (int, float)):
                    rsis.append(f"{rsi_val:.1f}")
                else:
                    rsis.append(str(rsi_val))
            else:
                rsis.append('N/A')
            
            fund = fundamentals.get(sym, {})
            earnings.append(fund.get('Next Earnings', 'N/A'))
            ex_divs.append(fund.get('Ex-Dividend', 'N/A'))
            yields.append(fund.get('Yield', 'N/A'))
            pes.append(fund.get('Trailing P/E', 'N/A'))
            
            g = fund.get('Rev Growth', 'N/A')
            if isinstance(g, (int, float)):
                growths.append(f"{g*100:.1f}%")
            else:
                growths.append(str(g))
                
            recs.append(fund.get('Recommendation', 'N/A'))
            
        table_data = [symbols, theses, catalysts, kill_switches, convictions, rsis, earnings, ex_divs, yields, timeframes, pes, growths, recs]
        table_headers = ["Symbol", "Thesis", "Catalyst", "Kill Switch", "Conviction", "RSI", "Next Earnings", "Ex-Div", "Yield", "Timeframe", "P/E", "Growth", "Rec"]
    
    # --- Create Subplots ---
    # We use a cleaner 2-row layout for charts. The table will be external HTML.
    rows_count = 2 
    
    if fundamentals:
        # Layout:
        # Row 1: Holdings Pie | Sector Pie
        # Row 2: CAGR Bar     | P&L Bar
        specs = [
            [{"type": "domain"}, {"type": "domain"}],
            [{"type": "xy"}, {"type": "xy"}]
        ]
        titles = (
            f"Holdings (Total: ${total_val:,.0f})", 
            "Sector Allocation",
            f"CAGR Performance (Target: {target_cagr:.0%})",
            "P&L by Holding"
        )
        row_heights = [0.45, 0.55]
    else:
        specs = [
            [{"type": "domain"}, {"type": "xy"}],
            [{"type": "xy", "colspan": 2}, None]
        ]
        titles = (
            f"Portfolio Allocation (Total: ${total_val:,.0f})", 
            f"CAGR Performance (Target: {target_cagr:.0%})",
            "P&L by Holding"
        )
        row_heights = [0.5, 0.5]

    fig = make_subplots(
        rows=rows_count, cols=2,
        specs=specs,
        subplot_titles=titles,
        row_heights=row_heights,
        vertical_spacing=0.1
    )
    
    # 1. Pie Chart (Holdings) - (Row 1, Col 1)
    fig.add_trace(
        go.Pie(
            labels=alloc_df['Symbol'], 
            values=alloc_df['Market Value'],
            name="Holdings",
            hole=0.4,
            hoverinfo="label+percent+value"
        ),
        row=1, col=1
    )
    
    # 2. Sector Pie Chart - (Row 1, Col 2) [New]
    if fundamentals:
        fig.add_trace(
            go.Pie(
                labels=sector_df['Sector'], 
                values=sector_df['Market Value'],
                name="Sector",
                hole=0.4,
                hoverinfo="label+percent+value",
                textinfo="percent+label"
            ),
            row=1, col=2
        )

    # 3. CAGR Bar Chart - (Row 2, Col 1)
    cagr_row = 2 if fundamentals else 1
    cagr_col = 1 if fundamentals else 2
    
    fig.add_trace(
        go.Bar(
            x=cagr_df['Symbol'],
            y=cagr_df['CAGR_Visual'],
            text=cagr_df['CAGR'].apply(lambda x: f"{x:.1%}"),
            marker_color=cagr_df['Color'],
            name="CAGR",
            hovertemplate="<b>%{x}</b><br>CAGR: %{text}<extra></extra>"
        ),
        row=cagr_row, col=cagr_col
    )
    
    fig.add_shape(
        type="line",
        x0=-0.5, x1=len(cagr_df)-0.5,
        y0=target_cagr, y1=target_cagr,
        line=dict(color="blue", width=2, dash="dash"),
        row=cagr_row, col=cagr_col
    )
    
    # 4. P&L Bar Chart - (Row 2, Col 2)
    pnl_row = 2
    pnl_col = 2 if fundamentals else 1
    
    fig.add_trace(
        go.Bar(
            y=pnl_df['Symbol'],
            x=pnl_df['P&L'],
            text=pnl_df['Return %'].apply(lambda x: f"{x:.1f}%"),
            marker_color=pnl_df['PnL_Color'],
            name="P&L",
            orientation='h',
            hovertemplate="<b>%{y}</b><br>P&L: $%{x:,.2f}<br>Return: %{text}<extra></extra>"
        ),
        row=pnl_row, col=pnl_col
    )
    
    fig.add_shape(
        type="line",
        y0=-0.5, y1=len(pnl_df)-0.5,
        x0=0, x1=0,
        line=dict(color="white", width=1, dash="dot"),
        row=pnl_row, col=pnl_col
    )
    
    # --- Layout / Styling ---
    # Update axes labels
    cagr_row = 2 if fundamentals else 1
    cagr_col = 1 if fundamentals else 2
    pnl_row = 2
    pnl_col = 2 if fundamentals else 1
    
    fig.update_xaxes(title_text="Symbol", row=cagr_row, col=cagr_col)
    fig.update_yaxes(title_text="CAGR", row=cagr_row, col=cagr_col)
    fig.update_xaxes(title_text="P&L ($)", row=pnl_row, col=pnl_col)
    
    fig.update_layout(
        title_text="Stock Portfolio Analysis",
        template="plotly_dark",
        height=800, 
        showlegend=True,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    # --- Generate Custom HTML ---
    # 1. Charts
    fig_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 2. Table
    qm_html = ""
    if fundamentals and table_data:
         # Construct DataFrame from lists
         qm_display_df = pd.DataFrame()
         for i, col_name in enumerate(table_headers):
             qm_display_df[col_name] = table_data[i]
             
         qm_html = qm_display_df.to_html(index=False, classes="fl-table", border=0)

    # 3. Full Template (Rich Aesthetics)
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Portfolio Analysis</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
            
            body {{ 
                font-family: 'Inter', sans-serif; 
                background-color: #121212; 
                color: #e0e0e0; 
                margin: 0; 
                padding: 20px; 
            }}
            .container {{ max_width: 1600px; margin: 0 auto; }}
            .chart-card {{ 
                background: #1e1e1e; 
                border-radius: 12px; 
                padding: 20px; 
                margin-bottom: 30px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
                border: 1px solid #333;
            }}
            
            h2 {{ 
                border-bottom: 1px solid #333; 
                padding-bottom: 15px; 
                margin-top: 0;
                margin-bottom: 20px; 
                color: #fff; 
                font-weight: 600;
            }}
            
            /* Table Styling */
            .table-wrapper {{ 
                overflow-x: auto; 
                border-radius: 8px; 
            }}
            .fl-table {{ 
                border-collapse: collapse; 
                width: 100%; 
                background: #1e1e1e; 
                min-width: 1000px; 
            }}
            .fl-table thead th {{ 
                background: #2b2b2b; 
                color: #ffffff; 
                padding: 16px; 
                text-align: left; 
                cursor: pointer; 
                position: sticky; 
                top: 0; 
                font-weight: 600;
                user-select: none;
            }}
            .fl-table thead th:hover {{ background: #333; color: #4facfe; }}
            .fl-table thead th::after {{ content: ' ↕'; opacity: 0.3; font-size: 0.8em; }}
            
            .fl-table tbody td {{ 
                padding: 14px 16px; 
                border-bottom: 1px solid #2a2a2a; 
                color: #ccc; 
                font-size: 0.95em;
            }}
            .fl-table tbody tr:hover {{ background: #262626; }}
            
            /* Highlight specific columns if needed */
            .fl-table tbody td:nth-child(1) {{ font-weight: bold; color: #fff; }} /* Symbol */
        </style>
    </head>
    <body>
        <div class="container">
            <div class="chart-card">
                {fig_html}
            </div>
            
            {'<div class="chart-card"><h2>Quant-Mental Analysis</h2><div class="table-wrapper">' + qm_html + '</div></div>' if qm_html else ''}
        </div>
        
        <script>
            // Simple Sort Logic
            document.querySelectorAll('.fl-table th').forEach(header => {{
                header.addEventListener('click', () => {{
                    const table = header.closest('table');
                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    const index = Array.from(header.parentNode.children).indexOf(header);
                    const isAsc = header.dataset.order === 'asc';
                    
                    // Improved Sort Logic
                    rows.sort((a, b) => {{
                        let aVal = a.children[index].innerText.trim();
                        let bVal = b.children[index].innerText.trim();
                        
                        if (aVal === bVal) return 0;
                        if (aVal === 'N/A' || aVal === '') return 1; // Push N/A to bottom
                        if (bVal === 'N/A' || bVal === '') return -1;
                        
                        // Numeric Check (Strict)
                        // using Number() instead of parseFloat avoids "2024-05" being parsed as 2024
                        let cleanA = aVal.replace(/[$,%]/g, '');
                        let cleanB = bVal.replace(/[$,%]/g, '');
                        
                        if (!isNaN(cleanA) && !isNaN(parseFloat(cleanA)) && !isNaN(cleanB) && !isNaN(parseFloat(cleanB))) {{
                            return isAsc ? cleanA - cleanB : cleanB - cleanA;
                        }}
                        
                        // Fallback to String Sort (Handles ISO Dates correctly)
                        return isAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                    }});
                    
                    rows.forEach(row => tbody.appendChild(row));
                    header.dataset.order = isAsc ? 'desc' : 'asc';
                    
                    // Reset visual indicators
                    header.parentNode.querySelectorAll('th').forEach(th => th.style.color = '');
                    header.style.color = '#4facfe';
                }});
            }});
        </script>
    </body>
    </html>
    """
    
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Interactive dashboard saved to: {save_path}")


