import sys
import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import json
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_portfolio_from_db
from market_data import get_current_prices, get_fundamental_data, get_technical_data, get_dividend_calendar, get_usd_to_cad_rate, get_portfolio_history, get_latest_news
from analysis import calculate_metrics
from backend.ticker_performance import get_ticker_performance
from backend.cache import clear_all_caches
from backend.database import engine, get_session, create_db_and_tables
from backend.models import Holding, Transaction as DBTransaction, RealizedPnL
from sqlmodel import Session, select

app = FastAPI(title="Holding Analyzer API")

# Allow CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
   allow_methods=["*"],
    allow_headers=["*"],
)

TARGET_CAGR = float(os.getenv("TARGET_CAGR", 0.08))
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def read_root():
    return {"message": "Holding Analyzer API is running", "health": "ok"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/portfolio")
def get_portfolio():
    try:
        # Switch to database source
        df, _ = load_portfolio_from_db()
        if df.empty:
            return {"summary": {}, "holdings": []}
        
        # Get Market Data
        symbols = df['Symbol'].unique().tolist()
        prices = get_current_prices(symbols)
        usd_cad = get_usd_to_cad_rate()
        fundamentals = get_fundamental_data(symbols)
        
        # Basic calculations (similar to main.py logic)
        df['Current Price'] = df['Symbol'].map(prices).fillna(0.0)
        
        # Embed Sector & Country from Fundamentals
        def get_sector_data(sym):
            f_data = fundamentals.get(sym)
            sector = f_data.get('Sector', 'Unknown') if f_data else 'Unknown'
            country = f_data.get('Country', 'Unknown') if f_data else 'Unknown'
            
            # International ETF mappings (these trade in Canada but invest internationally)
            international_etfs = {
                'XEF.TO': 'International',  # EAFE - Europe, Asia, Far East
                'XEC.TO': 'International',  # Emerging Markets
                'XEE.TO': 'International',  # Emerging Markets Equity
                'XWD.TO': 'International',  # All World ex-Canada
            }
            
            # Check if symbol is an international ETF first
            if sym in international_etfs:
                country = international_etfs[sym]
            # Fallback Logic for Country if still Unknown
            elif country in ['Unknown', None]:
                if sym.endswith('.TO'):
                    country = 'Canada'
                elif sym in ['BTC-USD', 'ETH-USD']:
                    country = 'Global' # Crypto
                else:
                    country = 'United States' # Default assumption for others
                    
            return sector, country
            
        # Use explicit assignment to avoid pandas alignment issues
        sectors = []
        countries = []
        for sym in df['Symbol']:
            s, c = get_sector_data(sym)
            sectors.append(s)
            countries.append(c)
        
        df['Sector'] = sectors
        df['Country'] = countries
        
        # Currency
        df['Currency'] = df['Symbol'].apply(lambda s: 'CAD' if s.endswith('.TO') else 'USD')
        
        # FX rate column
        df['FX Rate'] = df['Currency'].apply(lambda c: 1.0 if c == 'CAD' else usd_cad)
        
        # Market Value in CAD
        df['Market_Value'] = df['Current Price'] * df['Quantity'] * df['FX Rate']
        
        # Cost basis in CAD
        df['Cost Basis'] = df['Purchase Price'] * df['Quantity'] * df['FX Rate']
        
        # P&L
        df['PnL'] = df['Market_Value'] - df['Cost Basis']
        
        # Convert prices to CAD for the response
        df['Price (CAD)'] = df['Current Price'] * df['FX Rate']
        
        # Get additional data for Quant-mental analysis
        technical_data = get_technical_data(symbols)
        news_data = get_latest_news(symbols)
        dividend_data = get_dividend_calendar(symbols)
        
        # Add Quant-mental fields to each holding
        holdings_list = []
        for _, row in df.iterrows():
            sym = row['Symbol']
            holding_dict = row.to_dict()
            
            # Thesis data is already in row from load_portfolio_from_db()
            
            # Add technical data
            tech = technical_data.get(sym, {})
            holding_dict['RSI'] = tech.get('RSI', 'N/A')
            holding_dict['Tech Scorecard'] = tech.get('Scorecard', 'N/A')
            
            # Add fundamental data
            fund = fundamentals.get(sym, {})
            holding_dict['PEG Ratio'] = fund.get('PEG Ratio', 'N/A')
            holding_dict['Growth'] = fund.get('Earnings Growth', 'N/A')
            holding_dict['Rec'] = fund.get('Recommendation', 'N/A')
            holding_dict['Next Earnings'] = fund.get('Earnings Date', 'N/A')
            
            # Add dividend data
            div = dividend_data.get(sym, {})
            holding_dict['Ex-Div'] = div.get('Last_Ex', 'N/A')
            holding_dict['Yield'] = f"{div.get('Yield', 0):.2f}%" if div.get('Yield') else '0.00%'
            
            # Add catalyst (latest news)
            news = news_data.get(sym, {})
            holding_dict['Catalyst'] = news.get('headline', '')
            holding_dict['CatalystLink'] = news.get('link', '')
            
            holdings_list.append(holding_dict)
        
        return {
            "summary": {
                "total_value": df['Market_Value'].sum(),
                "total_cost": df['Cost Basis'].sum(),
                "total_pnl": df['PnL'].sum(),
                "usd_cad_rate": usd_cad
            },
            "holdings": holdings_list
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dividends")
def get_dividends():
    try:
        df, _ = load_portfolio_from_db()
        if df.empty: return {}
        
        # Get Market Data
        symbols = df['Symbol'].unique().tolist()
        calendar_map = get_dividend_calendar(symbols)
        usd_cad = get_usd_to_cad_rate()
        
        # Process Portfolio Logic
        monthly_data = {i: [] for i in range(1, 13)} # 1..12
        holdings_summary = []
        total_annual = 0.0
        
        for _, row in df.iterrows():
            sym = row['Symbol']
            qty = row['Quantity']
            
            # Helper to get currency multiplier
            fx = usd_cad if not sym.endswith('.TO') else 1.0
            
            if sym in calendar_map and calendar_map[sym]:
                data = calendar_map[sym]
                rate = data['Rate'] # Per share
                freq = data['Frequency']
                months = data['Months']
                
                if rate > 0:
                    # Calculate annual based on months count if available
                    count = len(months) if months else (12 if freq == 'Monthly' else 4 if freq == 'Quarterly' else 1)
                    annual_payout_native = rate * qty * count
                    
                    annual_payout_cad = annual_payout_native * fx
                    total_annual += annual_payout_cad
                    
                    # Add to holdings summary
                    holdings_summary.append({
                        "symbol": sym,
                        "name": sym, # Placeholder
                        "quantity": qty,
                        "dividend_rate": rate,
                        "frequency": freq,
                        "annual_payout_cad": annual_payout_cad,
                        "months": months
                    })
                    
                    # Distribute to Calendar
                    payment_per_month = (rate * qty) * fx
                    for m in months:
                        monthly_data[m].append({
                            "symbol": sym,
                            "amount": payment_per_month
                        })
        
        # Format Calendar for Frontend
        calendar_list = []
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        for i in range(1, 13):
            month_pay = monthly_data[i]
            total_month = sum(x['amount'] for x in month_pay)
            calendar_list.append({
                "month": month_names[i-1],
                "month_index": i,
                "total": total_month,
                "breakdown": month_pay
            })
            
        return {
            "summary": {
                "total_annual_cad": total_annual,
                "monthly_average_cad": total_annual / 12
            },
            "calendar": calendar_list,
            "holdings": sorted(holdings_summary, key=lambda x: x['annual_payout_cad'], reverse=True)
        }
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/performance")
def get_performance_history():
    try:
        df, _ = load_portfolio_from_db()
        if df.empty: return []
        
        history = get_portfolio_history(df)
        if history.empty:
             return []
        
        # Convert date to string
        history['date'] = pd.to_datetime(history['date'], utc=True).dt.strftime('%Y/%m/%d')
        
        return history.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticker-performance")
def get_ticker_perf():
    """Get per-ticker performance over various timeframes"""
    try:
        df, _ = load_portfolio_from_db()
        if df.empty:
            return {}
        
        symbols = df['Symbol'].unique().tolist()
        performance = get_ticker_performance(symbols)
        
        return performance
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class Transaction(BaseModel):
    Symbol: str
    Purchase_Price: float
    Quantity: float
    Commission: float = 0.0
    Trade_Date: str  # Format: YYYY/MM/DD
    Transaction_Type: str = "Buy" # Buy, Sell, DRIP
    Comment: Optional[str] = ""

# Symbols excluded from realized PnL (pure FX instruments)
_NORBERT_GAMBIT_EXCLUDE = {"DLR", "DLR.TO"}

# Canonical action map (same as data_loader.py)
_TYPE_NORMALIZE = {
    'Buy': 'BUY', 'BUY': 'BUY',
    'Sell': 'SELL', 'SELL': 'SELL',
    'DRIP': 'BUY',
    'Dividend': 'DIV', 'DIV': 'DIV',
    'Transf In': 'BUY', 'Transfer In': 'BUY',
}

def _recalculate_realized_pnl_for_symbol(session: Session, symbol: str) -> None:
    """
    Runs an in-memory FIFO on all DB transactions for `symbol`,
    then upserts a RealizedPnL row (source="db_transaction").
    Skips Norbert's Gambit symbols.
    Called after any Sell is inserted or any transaction is deleted.
    """
    if symbol in _NORBERT_GAMBIT_EXCLUDE:
        return

    # Pull all transactions for this symbol (sorted by date)
    db_txs = session.exec(
        select(DBTransaction)
        .where(DBTransaction.symbol == symbol)
        .order_by(DBTransaction.date)
    ).all()

    if not db_txs:
        # No transactions left — clean up any existing DB-source rows
        existing = session.exec(
            select(RealizedPnL)
            .where(RealizedPnL.symbol == symbol)
            .where(RealizedPnL.source == "db_transaction")
        ).all()
        for r in existing:
            session.delete(r)
        session.commit()
        return

    # --- FIFO calculation ---
    lots: dict = {}       # symbol -> [{qty, cost, currency}]
    realized: dict = {}   # (currency,) -> {pnl, cost_basis}

    for db_tx in db_txs:
        action = _TYPE_NORMALIZE.get(db_tx.type, db_tx.type.upper())
        qty = db_tx.quantity or 0.0
        curr = db_tx.currency or ("CAD" if symbol.endswith(".TO") else "USD")

        if qty <= 0:
            continue

        if action == "BUY":
            amt = abs(db_tx.amount) if db_tx.amount else (qty * (db_tx.price or 0) + (db_tx.commission or 0))
            lots.setdefault(symbol, []).append({"qty": qty, "cost": amt, "currency": curr})

        elif action == "SELL":
            if symbol not in lots or not lots[symbol]:
                continue
            total_proceeds = db_tx.amount if db_tx.amount else (qty * (db_tx.price or 0) - (db_tx.commission or 0))
            remaining = qty
            key = curr

            while remaining > 0 and lots[symbol]:
                lot = lots[symbol][0]
                sold = min(lot["qty"], remaining)
                frac = sold / qty
                cost_piece = lot["cost"] * (sold / lot["qty"])
                proceeds_piece = total_proceeds * frac

                realized.setdefault(key, {"pnl": 0.0, "cost_basis": 0.0})
                realized[key]["pnl"] += proceeds_piece - cost_piece
                realized[key]["cost_basis"] += cost_piece

                lot["qty"] -= sold
                lot["cost"] -= cost_piece
                remaining -= sold
                if lot["qty"] <= 1e-6:
                    lots[symbol].pop(0)

    # --- Upsert results ---
    # Delete old db_transaction rows for this symbol
    existing = session.exec(
        select(RealizedPnL)
        .where(RealizedPnL.symbol == symbol)
        .where(RealizedPnL.source == "db_transaction")
    ).all()
    for r in existing:
        session.delete(r)

    for curr, vals in realized.items():
        pnl = vals["pnl"]
        cb  = vals["cost_basis"]
        if pd.isna(pnl) or cb == 0:
            continue
        session.add(RealizedPnL(
            symbol=symbol,
            currency=curr,
            pnl_amount=float(pnl),
            cost_basis_sold=float(cb),
            broker="Manual",
            account_type="Manual",
            source="db_transaction",
        ))

    session.commit()
    print(f"  [PnL] Recalculated realized P&L for {symbol}: {realized}")

@app.get("/api/transactions")
def get_transactions():
    """Fetch all transactions from DB formatted for frontend"""
    try:
        with Session(engine) as session:
            txs = session.exec(select(DBTransaction).order_by(DBTransaction.date.desc())).all()
            
            # Map DB fields to the format the frontend expects (Uppercase keys)
            formatted = []
            for tx in txs:
                formatted.append({
                    "id": tx.id,
                    "Symbol": tx.symbol,
                    "Purchase Price": tx.price,
                    "Quantity": tx.quantity,
                    "Commission": tx.commission,
                    "Trade Date": tx.date.strftime('%Y/%m/%d'),
                    "Transaction Type": tx.type,
                    "Comment": tx.description or ""
                })
            return formatted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transactions")
def add_transaction(tx: Transaction):
    """Add a new transaction to Database"""
    try:
        with Session(engine) as session:
            # 1. Ensure Holding exists
            existing_holding = session.exec(select(Holding).where(Holding.symbol == tx.Symbol)).first()
            if not existing_holding:
                new_h = Holding(symbol=tx.Symbol)
                session.add(new_h)
                session.commit()
                session.refresh(new_h)
                holding_id = new_h.id
            else:
                holding_id = existing_holding.id
            
            # 2. Add Transaction
            db_tx = DBTransaction(
                holding_id=holding_id,
                symbol=tx.Symbol,
                date=pd.to_datetime(tx.Trade_Date),
                type=tx.Transaction_Type,
                quantity=tx.Quantity,
                price=tx.Purchase_Price,
                commission=tx.Commission,
                amount=(tx.Purchase_Price * tx.Quantity) + tx.Commission,
                currency="CAD" if tx.Symbol.endswith(".TO") else "USD",
                description=tx.Comment,
                source="Manual"
            )
            session.add(db_tx)
            session.commit()

            # 3. If Sell, recalculate realized P&L for this symbol
            if tx.Transaction_Type in ("Sell", "SELL"):
                _recalculate_realized_pnl_for_symbol(session, tx.Symbol)
            
            clear_all_caches()
            return {"status": "success", "id": db_tx.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions/{id}")
def delete_transaction(id: int):
    """Delete a transaction from Database by ID"""
    try:
        with Session(engine) as session:
            tx = session.get(DBTransaction, id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            symbol = tx.symbol
            session.delete(tx)
            session.commit()

            # Recalculate realized P&L after any deletion (deleting a buy changes future sell PnL too)
            _recalculate_realized_pnl_for_symbol(session, symbol)

            clear_all_caches()
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/db/transactions")
def get_db_transactions():
    with Session(engine) as session:
        txs = session.exec(select(DBTransaction).order_by(DBTransaction.date.desc())).all()
        return txs

@app.get("/api/db/holdings")
def get_db_holdings():
    with Session(engine) as session:
        holdings = session.exec(select(Holding).order_by(Holding.symbol)).all()
        return holdings

@app.put("/api/holdings/{symbol}")
def update_holding(symbol: str, data: dict = Body(...)):
    """Update thesis/mental data for a holding"""
    try:
        with Session(engine) as session:
            h = session.exec(select(Holding).where(Holding.symbol == symbol)).first()
            if not h:
                h = Holding(symbol=symbol)
                session.add(h)
            
            if 'Thesis' in data: h.thesis = data['Thesis']
            if 'Conviction' in data: h.conviction = data['Conviction']
            if 'Timeframe' in data: h.timeframe = data['Timeframe']
            if 'Kill Switch' in data: h.kill_switch = data['Kill Switch']
            if 'Comment' in data: h.comment = data['Comment']
            
            session.add(h)
            session.commit()
            clear_all_caches()
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync")
def force_sync():
    """Clear all caches to force fresh data fetches"""
    clear_all_caches()
    return {"status": "success", "message": "All caches cleared"}

@app.get("/api/realized-pnl")
def get_realized_pnl():
    """Return all realized P&L rows from broker CSV history"""
    try:
        with Session(engine) as session:
            rows = session.exec(select(RealizedPnL).order_by(RealizedPnL.broker, RealizedPnL.symbol)).all()
            result = []
            for r in rows:
                cb = r.cost_basis_sold or 0
                pnl_pct = (r.pnl_amount / cb * 100) if cb != 0 else None
                result.append({
                    "symbol": r.symbol,
                    "currency": r.currency,
                    "pnl_amount": r.pnl_amount,
                    "cost_basis_sold": cb,
                    "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
                    "broker": r.broker,
                    "account_type": r.account_type,
                    "source": r.source,
                })
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symbol-accounts")
def get_symbol_accounts():
    """
    Returns a mapping of symbol -> list of {broker, account_type}
    read strictly from the Database (Transaction table broker/account columns).
    """
    result: dict = {}
    
    def add_entry(sym, broker, account_type):
        if not sym or not broker or not account_type: return
        entry = {"broker": broker, "account_type": account_type}
        if sym not in result:
            result[sym] = []
        if entry not in result[sym]:
            result[sym].append(entry)

    try:
        with Session(engine) as session:
            # Source of truth is the DB columns
            manual_txs = session.exec(select(DBTransaction).where(DBTransaction.source == "Manual")).all()
            for tx in manual_txs:
                if tx.broker and tx.account_type:
                    add_entry(tx.symbol, tx.broker, tx.account_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
