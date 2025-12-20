# Stock Holding Analysis Tool

A powerful "Quant-Mental" portfolio analyzer that combines quantitative metrics (CAGR, P&L, RSI) with qualitative insights (Thesis, Conviction) to automate your investment decision-making.

## 🚀 Key Features

### 📊 Advanced Analytics
*   **Look-Through Sector Analysis**: Mathematically unbundles ETFs (like VOO or XQQ) into their underlying sectors to reveal your *true* portfolio exposure.
*   **Catalyst Calendar**: Automatically tracks **Next Earnings**, **Ex-Dividend Dates**, and **Yields** for all holdings.
*   **Performance Metrics**:
    *   **CAGR Analysis**: Time-adjusted returns to compare long-term holdings.
    *   **P&L Analysis**: Absolute dollar gains/losses with currency normalization (USD -> CAD).
    *   **Momentum**: Tracks RSI (14-day) to identify overbought/oversold conditions.

### 🧠 Quant-Mental Framework
*   **Three-Column Thesis**: Track your rationale for every trade structure:
    *   **Thesis**: Why did you buy?
    *   **Catalyst**: What event will unlock value?
    *   **Kill Switch**: When should you abort?
*   **Persistent Metadata**: Your notes (Thesis, Conviction) are saved in `thesis.json` and automatically merged with your weekly CSV updates.

### 📈 Visualization
*   **Interactive Dashboard**: A premium 2x2 grid layout + Data Table:
    *   **Holdings & Sector Pies**: Visualizes visible vs look-through allocation.
    *   **Performance Bars**: Benchmarks CAGR and realized P&L.
    *   **Sortable Analysis Table**: A glassmorphism-styled table to rank stocks by RSI, P/E, Conviction, or Yield.
*   **Weekly Reports**: Automated email summaries with embedded charts and "Weekly Top Movers".

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
    *   **CSV**: Place your `portfolio.csv` in the root (Exported from Yahoo Finance or broker).
    *   **Metadata**: The first time you run the tool, logic can extract notes. Subsequently, manage your notes in `thesis.json` or update your CSV—the system syncs them.

## 🖥️ Usage

### Dashboard Generation
Run the master script to generate the full analysis:
```bash
python main.py
```
This will:
*   Print a **Look-Through Sector Exposure** table.
*   Identify **Restructuring Opportunities** (Dead Money).
*   Generate `portfolio_dashboard.html` (Interactive).
*   Generate `dashboard_preview.png` (Static).

### Automated Reporting
The system is designed to run via **GitHub Actions** every Friday at 5:00 PM EST.
*   It fetches fresh prices.
*   It merges your persistent notes.
*   It emails you a PDF-quality report.

## 📂 Project Structure

*   `main.py`: Orchestrator for data loading, analysis, and reporting.
*   `market_data.py`: Fetches prices, fundamentals, catalyst dates, and ETF look-through weights.
*   `data_loader.py`: Handles CSV loading and intelligent JSON metadata merging.
*   `analysis.py`: Logic for Rebalancing, CAGR, and P&L.
*   `visualize.py`: Generates the HTML5 Interactive Dashboard.
*   `thesis.json`: Storage for your qualitative investment notes.
