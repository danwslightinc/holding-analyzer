import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import pandas as pd
import squarify
import numpy as np

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

def generate_static_preview(df, target_cagr, fundamentals=None, save_path='dashboard_preview.png'):
    """
    Generates a static PNG summary for email embedding.
    Includes: Sector Allocation (H-Bar), CAGR (bar, excl BTC), and P&L (H-Bar).
    """
    if df.empty: return

    # Sector Allocation Data (Look-Through) or Fallback
    if fundamentals:
        sector_map = {}
        for _, row in df.iterrows():
            sym = row['Symbol']
            val = row['Market Value']
            base_sector = fundamentals.get(sym, {}).get('Sector', 'Other')
            if not base_sector: base_sector = 'Other'
            
            if sym in ETF_SECTOR_WEIGHTS:
                weights = ETF_SECTOR_WEIGHTS[sym]
                remaining_weight = 1.0
                for sec, w in weights.items():
                    amount = val * w
                    sector_map[sec] = sector_map.get(sec, 0) + amount
                    remaining_weight -= w
                if remaining_weight > 0.001:
                    sector_map['Other'] = sector_map.get('Other', 0) + (val * remaining_weight)
            else:
                sector_map[base_sector] = sector_map.get(base_sector, 0) + val
        
        plot_data = pd.Series(sector_map).sort_values(ascending=False)
        title_text = 'Sector Exposure (Look-Through)'
    else:
        # Fallback to Holdings if no fundamentals
        plot_data = df.groupby('Symbol')['Market Value'].sum().sort_values(ascending=False)
        title_text = 'Portfolio Allocation (Holdings)'
    
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

    # Create grid
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.3, wspace=0.3)
    
    # Row 1, Col 1: Sector Donut Chart
    ax1 = fig.add_subplot(gs[0, 0])
    # Re-use plot_data (Sector Series)
    wedges, texts, autotexts = ax1.pie(plot_data, labels=plot_data.index, autopct='%1.1f%%', startangle=90, pctdistance=0.85)
    plt.setp(texts, size=8)
    plt.setp(autotexts, size=8, weight="bold")
    # Donut Circle
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    ax1.add_artist(centre_circle)
    ax1.set_title("Sector Allocation", fontsize=14, fontweight='bold')
    ax1.axis('equal')

    # Row 1, Col 2: CAGR Bar Chart
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(cagr_df['Symbol'], cagr_df['CAGR_Visual'], color=cagr_colors)
    ax2.axhline(y=target_cagr, color='blue', linestyle='--', label=f'Target {target_cagr:.0%}')
    ax2.set_title('CAGR vs Target (Excl. BTC)', fontsize=14, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # Row 2, Col 1: Sector/Allocation (Treemap)
    ax3 = fig.add_subplot(gs[1, 0])
    
    # Generate colors (Blue gradient)
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(plot_data)))
    
    # Labels with %
    total_val = plot_data.sum()
    labels = [f"{i}\n{v/total_val:.1%}" if v/total_val > 0.03 else "" for i, v in zip(plot_data.index, plot_data.values)]
    
    try:
        squarify.plot(sizes=plot_data.values, label=labels, 
                      color=colors, alpha=0.8, ax=ax3, 
                      text_kwargs={'fontsize':9, 'weight':'bold', 'color':'white'})
    except Exception as e:
        print(f"Treemap error: {e}")
        ax3.text(0.5, 0.5, "Treemap Error", ha='center')
        
    ax3.set_title('Sector Look-Through (Treemap)', fontsize=14, fontweight='bold')
    ax3.axis('off')
    
    # Row 2, Col 2: P&L (Horizontal Bar)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.barh(pnl_df['Symbol'], pnl_df['P&L'], color=pnl_colors)
    ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax4.set_title('P&L by Holding ($)', fontsize=14, fontweight='bold')
    ax4.set_xlabel('P&L ($)')
    ax4.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"Static preview saved to: {save_path}")

def generate_dashboard(df, target_cagr, fundamentals=None, technicals=None, news=None, save_path='portfolio_dashboard.html'):
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

    # --- Treemap Data Preparation (Look-Through) ---
    if fundamentals:
        tm_ids = ["Portfolio"]
        tm_labels = ["Portfolio"]
        tm_parents = [""]
        tm_values = [total_val]
        tm_text = ["Total Value"]
        
        # 1. Aggregate Value by Sector for Parents
        # We need this to ensure parent values match sum of children (Plotly requirement)
        # Re-using sector_map logic from static generation or recalculating here
        
        # We need to build the list of children first to sum them up perfectly?
        # Actually Plotly can sum children if branchvalues='total'.
        # Let's generate the detailed list of fragments first.
        
        fragments = [] # list of (Sector, Label, Value)
        
        for _, row in df.iterrows():
            sym = row['Symbol']
            val = row['Market Value']
            base_sector = fundamentals.get(sym, {}).get('Sector', 'Other')
            if not base_sector: base_sector = 'Other'
            
            if sym in ETF_SECTOR_WEIGHTS:
                # Split ETF
                weights = ETF_SECTOR_WEIGHTS[sym]
                remaining_weight = 1.0
                for sec, w in weights.items():
                    amount = val * w
                    fragments.append((sec, f"{sym} ({sec[:4]})", amount))
                    remaining_weight -= w
                
                if remaining_weight > 0.001:
                    amount = val * remaining_weight
                    fragments.append(('Other', f"{sym} (Other)", amount))
            else:
                # Single Stock
                fragments.append((base_sector, sym, val))
        
        # Convert to DataFrame to group by Sector
        frag_df = pd.DataFrame(fragments, columns=['Sector', 'Label', 'Value'])
        frag_df = frag_df[frag_df['Value'] > 0.01] # Filter noise
        
        # Add Sectors (Parents)
        sector_group = frag_df.groupby('Sector')['Value'].sum()
        for sector, val in sector_group.items():
            tm_ids.append(sector)
            tm_labels.append(sector)
            tm_parents.append("Portfolio")
            tm_values.append(val)
            tm_text.append(f"{val:,.0f}")
            
        # Add Holdings (Children)
        for _, row in frag_df.iterrows():
            # ID must be unique. Label can be same.
            # ID: Sector + Label to be unique (e.g. Technology - VOO (Tech))
            unique_id = f"{row['Sector']} - {row['Label']}"
            tm_ids.append(unique_id)
            tm_labels.append(row['Label']) # Visible Label
            tm_parents.append(row['Sector'])
            tm_values.append(row['Value'])
            tm_text.append(f"${row['Value']:,.0f}")
            
    # CAGR Data (Cleaned)
    cagr_df = df.copy()
    cagr_df['CAGR_Visual'] = cagr_df['CAGR'].clip(upper=3.0, lower=-1.0) 
    cagr_df['Color'] = cagr_df['CAGR'].apply(lambda x: 'green' if x >= target_cagr else 'red')
    
    # P&L Data
    pnl_df = df.copy()
    pnl_df['Return %'] = (pnl_df['P&L'] / pnl_df['Cost Basis']) * 100
    pnl_df['PnL_Color'] = pnl_df['P&L'].apply(lambda x: 'green' if x > 0 else 'red')
    pnl_df = pnl_df.sort_values('P&L', ascending=True)
    pnl_df['Text'] = pnl_df.apply(lambda x: f"${x['P&L']:,.0f} ({x['Return %']:.1f}%)", axis=1)
    
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
            cat_val = row.get('Catalyst', '')
            if not cat_val and news and sym in news:
                cat_val = news[sym]
            catalysts.append(cat_val)
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
    # --- Create Subplots ---
    rows_count = 2 
    
    if fundamentals:
        # Layout:
        # Row 1: Holdings Pie | CAGR Bar
        # Row 2: Treemap      | P&L Bar
        specs = [
            [{"type": "domain"}, {"type": "xy"}],
            [{"type": "treemap"}, {"type": "xy"}]
        ]
        titles = (
            f"Holdings (Total: ${total_val:,.0f})", 
            f"CAGR Performance (Target: {target_cagr:.0%})",
            "Sector Exposure (Look-Through)",
            "P&L by Holding"
        )
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

    fig = make_subplots(
        rows=rows_count, cols=2,
        specs=specs,
        subplot_titles=titles,
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    # 1. Pie Chart (Holdings) - (Row 1, Col 1)
    fig.add_trace(
        go.Pie(
            labels=alloc_df['Symbol'], 
            values=alloc_df['Market Value'],
            name="Holdings",
            hole=0.4,
            hoverinfo="label+percent+value",
            showlegend=False
        ),
        row=1, col=1
    )
    
    # 2. CAGR Bar Chart - (Row 1, Col 2)
    cagr_row = 1
    cagr_col = 2
    
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
    
    # 3. Sector Treemap - (Row 2, Col 1)
    if fundamentals:
        fig.add_trace(
            go.Treemap(
                ids=tm_ids,
                labels=tm_labels,
                parents=tm_parents,
                values=tm_values,
                text=tm_text,
                textinfo="label+text+percent parent",
                branchvalues="total",
                marker=dict(colorscale='Blues'), # Professional Blue theme
                hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Share: %{percentParent:.1%}<extra></extra>'
            ),
            row=2, col=1
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
    
    # --- Layout / Styling ---
    # Update axes labels
    fig.update_xaxes(title_text="Symbol", row=cagr_row, col=cagr_col)
    fig.update_yaxes(title_text="CAGR", row=cagr_row, col=cagr_col)
    fig.update_xaxes(title_text="P&L ($)", row=pnl_row, col=pnl_col)
    
    fig.update_layout(
        title_text="Stock Portfolio Analysis",
        template="plotly_dark",
        height=900, 
        showlegend=False,
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


