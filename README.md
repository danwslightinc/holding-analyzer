# Stock Holding Analysis Tool

A powerful Python-based portfolio analyzer that tracks your performance, identifies underperforming assets, and automates weekly reporting.

## 🚀 Key Features

*   **Portfolio Import**: Reads your holdings from a local CSV file.
*   **Live Market Data**: Fetches real-time prices via `yfinance`.
*   **Currency Support**: Automatically converts USD holdings (e.g., NVDA, MSFT) to **CAD** for accurate total portfolio value.
*   **Performance Metrics**: Calculates P&L, Market Value, and CAGR for each position.
*   **Risk Analysis ("Fishy Stock" Scan)**: Identifies broken trends, crashes (>15% drop), and extreme volatility.
*   **Restructuring Suggestions**: Highlights "Dead Money" (underperformers) and calculates potential gains from reallocating.
*   **Visualization**:
    *   **Interactive Dashboard**: HTML dashboard with Zoomable Bar Charts and Pie Charts (powered by Plotly).
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
*   Print a summary table to the console.
*   Print the "Weekly Top Gainers/Losers".
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
To automate the report (runs every Friday at 5 PM), use the setup script:
```bash
./setup_cron.sh
```
*   This sets up a cron job on your Mac.
*   The email includes:
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
