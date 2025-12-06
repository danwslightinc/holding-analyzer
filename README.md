# Stock Holding Analysis

A Python-based tool to analyze your stock portfolio holdings. It reads your transaction history from a CSV file, fetches real-time market prices, and calculates key performance metrics such as Profit & Loss (P&L) and Compound Annual Growth Rate (CAGR).

## Features

*   **Portfolio Import**: Reads holdings from a local CSV file.
*   **Live Market Data**: Fetches real-time stock prices using `yfinance` (Yahoo Finance).
*   **Performance Metrics**:
    *   **Cost Basis**: Function of Purchase Price, Quantity, and Commission.
    *   **Market Value**: Current value of holdings.
    *   **P&L**: Absolute gain/loss per holding and total portfolio.
    *   **CAGR**: Annualized return rate for each holding.
    *   **Goal Tracking**: Visual indicators checking if holdings meet a 10% target CAGR.
*   **Detailed Output**: Displays a formatted table with analysis and a portfolio summary.

## Prerequisites

*   Python 3.8 or higher
*   Internet connection (for fetching market data)

## Installation

1.  **Clone the repository** (or navigate to the project directory):
    ```bash
    cd /path/to/stock_analysis
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Prepare your Portfolio CSV**:
    Create a CSV file (e.g., `portfolio.csv`) with the following headers:
    *   `Symbol`: Ticker symbol (e.g., AAPL, MSFT, VOO).
    *   `Trade Date`: Date of purchase in `YYYYMMDD` format (e.g., 20230115).
    *   `Purchase Price`: Price per share at time of purchase.
    *   `Quantity`: Number of shares bought.
    *   `Commission`: Transaction fees (optional, defaults to 0).

    **Example CSV (`portfolio.csv`):**
    ```csv
    Symbol,Trade Date,Purchase Price,Quantity,Commission
    AAPL,20230115,135.00,10,0.0
    MSFT,20230220,250.50,5,4.95
    VOO,20220610,350.00,2,0.0
    ```

2.  **Update File Path**:
    Open `main.py` and update the `CSV_PATH` variable to point to your CSV file:
    ```python
    CSV_PATH = "/path/to/your/portfolio.csv"
    ```

## Usage

Run the main script:
```bash
python main.py
```

### Output Example

```text
Portfolio Summary:
+----------+--------------+------------+--------------+----------------+-----------+--------+----------+
| Symbol   | Trade Date   |   Quantity | Cost Basis   | Market Value   | P&L       | CAGR   | Status   |
|----------+--------------+------------+--------------+----------------+-----------+--------+----------|
| AAPL     | 2023-01-15   |         10 | $1,350.00    | $1,750.00      | $400.00   | 25.10% | ✅       |
...
Total Portfolio Value: $10,500.00
Total P&L: $2,500.00
```

## Project Structure

*   `main.py`: Entry point. Orchestrates data loading, price fetching, and analysis.
*   `data_loader.py`: Handles CSV reading and data cleaning.
*   `market_data.py`: Interacts with the `yfinance` API to retrieve stock prices.
*   `requirements.txt`: List of Python dependencies.

## License

This project is for personal use. Market data is provided by Yahoo Finance and may be delayed.
