# Stock Holding Analysis Tool

A powerful Python-based portfolio analyzer that tracks your performance, identifies underperforming assets, and automates weekly reporting.

## 🚀 Key Features

*   **Portfolio Import**: Reads your holdings from a local CSV file.
*   **Smart Aggregation**: Automatically combines duplicate symbol entries with weighted average costs for accurate returns.
*   **Live Market Data**: Fetches real-time prices via `yfinance`.
*   **Currency Support**: Automatically converts USD holdings (e.g., NVDA, MSFT) to **CAD** for accurate total portfolio value.
*   **Performance Metrics**: 
    *   **CAGR Analysis**: Time-adjusted returns to compare holdings with different purchase dates.
    *   **P&L Analysis**: Absolute dollar gains/losses and simple percentage returns (matches broker statements).
*   **Risk Analysis ("Fishy Stock" Scan)**: Identifies broken trends, crashes (>15% drop), and extreme volatility.
*   **Restructuring Suggestions**: Highlights "Dead Money" (underperformers) and calculates potential gains from reallocating.
*   **Visualization**:
    *   **Interactive Dashboard**: 2-row HTML dashboard with:
        *   Top Row: Portfolio Allocation (Pie) | CAGR Performance (Bar)
        *   Bottom Row: P&L Performance (Horizontal Bar)
    *   **Email Reports**: Weekly email with embedded metric summaries and static charts.

## 🛠️ Installation

1.  **Clone & Setup**:
    ```bash
    git clone https://github.com/your-repo/stock_analysis.git
    cd stock_analysis
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configuration (.env)**:
    Create a `.env` file for email capability (required for weekly reports):
    ```bash
    cp .env.example .env
    # Edit .env and add your Gmail App Password
    ```

3.  **Data Setup**:
    Ensure your `portfolio.csv` follows the format:
    `Symbol, Trade Date, Purchase Price, Quantity, Commission`

## 🖥️ Usage

### Manual Run
Run the main analysis script to see the table output and generate the dashboard:
```bash
python main.py
```
This will:
*   Print a portfolio summary table to the console.
*   Print the "Weekly Top Gainers/Losers".
*   Print CAGR-based restructuring analysis.
*   Print P&L analysis (winners/losers by dollar amount).
*   Generate `portfolio_dashboard.html` (interactive).
*   Generate `dashboard_preview.png` (static).

### Detailed Stock Deep Dives
Analyze a specific ticker (fundamentals, moving averages, analyst ratings):
```bash
python analyze_stock_detail.py MSFT
```

### Risk Scan
Quickly scan for "Fishy" stocks (crashing or broken trends):
```bash
python analyze_risk.py
```

### 📧 Weekly Email Automation
To automate the report (runs every Friday at 5 PM EST), use GitHub Actions:
*   Configure secrets in your GitHub repository settings:
    *   `SENDER_EMAIL`: Your Gmail address
    *   `SENDER_PASSWORD`: Gmail app password
    *   `RECIPIENT_EMAIL`: Email to receive reports
*   The workflow (`.github/workflows/weekly_report.yml`) will:
    *   Run analysis automatically every Friday
    *   Send email with:
        *   **Inline Chart**: A snapshot of your allocation and performance.
        *   **Weekly Movers**: Top 3 Gainers & Losers text summary.
        *   **Attachment**: The full interactive HTML dashboard.

## 📂 Project Structure

*   `main.py`: Core logic for data loading, calculation, and reporting.
*   `market_data.py`: Handles `yfinance` API calls and currency conversion.
*   `analysis.py`: Logic for CAGR, restructuring, and top movers.
*   `visualize.py`: Generates Plotly (HTML) and Matplotlib (PNG) charts.
*   `email_report.py`: Handles email composition and sending.
*   `analyze_stock_detail.py`: Standalone script for deep-dive analysis.
*   `analyze_risk.py`: Standalone script for risk scanning.
