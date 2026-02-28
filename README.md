# Stock Holding Analysis Tool

A powerful "Quant-Mental" portfolio analyzer and management system that combines quantitative metrics (CAGR, P&L, RSI) with qualitative insights (Thesis, Conviction, Kill Switch).

## 🚀 Key Features

### 📊 Advanced Analytics
*   **Look-Through Sector Analysis**: Mathematically unbundles ETFs (like VOO or XQQ) into their underlying sectors to reveal your *true* portfolio exposure.
*   **Intelligent Data Merging**: Primary source of truth uses the **Holding Table** for active positions, enriched by **Transaction History** for FIFO-based cost basis and realized P&L.
*   **Deduplication & Normalization**: Robust logic filters duplicate transactions between manual entries and CSV imports, preferring manual data while normalizing account labels (TFSA, RRSP, etc.).
*   **Performance Metrics**:
    *   **CAGR Analysis**: Time-adjusted returns to compare long-term holdings.
    *   **Realized P&L**: Accurate FIFO tracking of closed trades with currency normalization (USD -> CAD).
    *   **Momentum**: Tracks RSI (14-day) to identify overbought/oversold technical levels.

### 🧠 Quant-Mental Framework
*   **Three-Column Thesis**: Track your rationale for every trade structure:
    *   **Thesis**: Why did you buy?
    *   **Catalyst**: What event will unlock value?
    *   **Kill Switch**: When should you abort?
*   **Persistent Database**: Your rationale and trade history are stored in a structured **PostgreSQL (Supabase)** or **SQLite** database via SQLModel, ensuring data integrity across the web interface and automated scripts.

### 📉 Modern Web Interface
*   **Interactive Dashboard**: A premium Next.js frontend with:
    *   **Live Portfolio Value**: Real-time market value tracking in CAD.
    *   **Sector Exposure**: Glassmorphism-styled charts for visible vs. look-through allocation.
    *   **Performance Tracking**: Visualized CAGR, unrealized gains, and realized performance.
    *   **Transaction Management**: Add, delete, and import transactions directly through the UI.

---

## 🛠️ Installation & Setup

### 1. Backend Setup (FastAPI)
```bash
# Clone the repository
git clone https://github.com/your-repo/holding-analyzer.git
cd holding-analyzer

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (.env)
Create a `.env` file in the root directory:
```env
# Database (Defaults to local sqlite if not provided)
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Email Configuration (For weekly reports)
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=target-email@gmail.com

# Market Data
# (Add any specific API keys here)
```

### 3. Frontend Setup (Next.js)
```bash
cd frontend
npm install
```

### 4. Data Migration
If you have data in legacy `portfolio.csv` or `thesis.json` files:
```bash
python scripts/migrate_to_db.py
```

---

## 🖥️ Usage

### Running Locally
1.  **Start the Backend**:
    ```bash
    uvicorn backend.api:app --reload --port 8000
    ```
2.  **Start the Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```
3.  **Access the App**: Open [http://localhost:3000](http://localhost:3000)

### Automated Reporting
The system is integrated with **GitHub Actions** to:
*   Sync portfolio data weekly.
*   Generate fresh performance reports.
*   Email a PDF-quality summary with "Top Movers" and sector alerts.

---

## 📂 Project Structure

*   `backend/`: FastAPI core, `models.py` (SQLModel), and `database.py`.
*   `frontend/`: React components and Dashboard UI (Next.js).
*   `data_loader.py`: The "Brain" – handles deduplication, account normalization, and data merging logic.
*   `transaction_parser.py`: FIFO lot tracking and realized P&L calculations.
*   `market_data.py`: Fetches real-time prices, fundamentals, and ETF look-through weights.
*   `analysis.py`: Logic for CAGR, restructuring opportunities, and portfolio health.
*   `scripts/`: Utility scripts for database migrations and one-off analyses.
*   `portfolio.db`: (Optional) Local SQLite fallback database.
