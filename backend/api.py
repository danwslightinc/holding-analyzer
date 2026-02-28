import sys
import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
import json
import numpy as np
import math
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_portfolio_from_db, get_processed_transactions
from market_data import get_current_prices, get_fundamental_data, get_technical_data, get_dividend_calendar, get_usd_to_cad_rate, get_portfolio_history, get_latest_news, get_daily_changes
from analysis import calculate_metrics
from backend.ticker_performance import get_ticker_performance
from backend.cache import clear_all_caches
from backend.database import engine, get_session, create_db_and_tables
from backend.models import Holding, Transaction as DBTransaction
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

def sanitize_val(val):
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.strftime('%Y/%m/%d')
    try:
        # Check for numeric types specifically using numpy to catch all variants
        if isinstance(val, (float, np.floating, int, np.integer)):
            if not np.isfinite(val):
                return None
            return float(val)
    except:
        pass
    return val
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
        daily_changes = get_daily_changes(symbols)
        
        # Add Quant-mental fields to each holding

        # Add Quant-mental fields to each holding
        holdings_list = []
        for _, row in df.iterrows():
            sym = row['Symbol']
            # Convert row to dict and sanitize all values
            holding_dict = {k: sanitize_val(v) for k, v in row.to_dict().items()}
            
            # Add daily change
            holding_dict['Day Change'] = float(daily_changes.get(sym, 0.0))
            
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
                "total_value": sanitize_val(df['Market_Value'].sum()),
                "total_cost": sanitize_val(df['Cost Basis'].sum()),
                "total_pnl": sanitize_val(df['PnL'].sum()),
                "usd_cad_rate": sanitize_val(usd_cad)
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
    Broker: str = "Manual"
    Account_Type: str = "Manual"
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

# _recalculate_realized_pnl_for_symbol removed in favor of dynamic calculation

@app.get("/api/transactions")
def get_transactions():
    """Fetch all transactions from DB formatted for frontend"""
    try:
        with Session(engine) as session:
            txs = session.exec(select(DBTransaction).order_by(DBTransaction.date.desc())).all()
            
            # Map DB fields to the format the frontend expects (Uppercase keys)
            return [
                {
                    "id": tx.id,
                    "Symbol": tx.symbol,
                    "Purchase Price": sanitize_val(tx.price),
                    "Quantity": sanitize_val(tx.quantity),
                    "Commission": sanitize_val(tx.commission),
                    "Trade Date": sanitize_val(tx.date),
                    "Transaction Type": tx.type,
                    "Broker": tx.broker or "Manual",
                    "Account Type": tx.account_type or "Unknown",
                    "Comment": tx.description or ""
                }
                for tx in txs
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/closed-trades")
def get_closed_trades():
    """Fetch individually matched closed trades from full broker CSV history (FIFO basis)"""
    try:
        # Fetch entirely from database transactions instead of CSV
        with Session(engine) as session:
            df_tx = get_processed_transactions(session)
            
        if df_tx.empty:
            return []
            
        # Ensure chronological order
        df_tx = df_tx.sort_values(by=['Date'])
        
        lots = {}
        closed_trades = []
        
        for _, tx in df_tx.iterrows():
            sym = tx['Symbol']
            action = str(tx['Action']).upper()
            qty = tx['Quantity']
            price = tx['Price']
            comm = tx['Commission']
            date = tx['Date']
            curr = tx['Currency']
            amt = tx['Amount']
            desc = str(tx.get('Description', '')).upper()
            
            if pd.isna(qty) or qty <= 0:
                continue
            
            # Exclude Norbert's Gambit currency conversions
            if str(sym).upper() in ["DLR.TO", "DLR.U.TO", "DLR"]:
                continue
                
            if action in ['BUY', 'DIV', 'DRIP'] or 'TRANSF' in action or ('RECEIVED' in desc and ('MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc)):
                if sym not in lots: lots[sym] = []
                cost = abs(amt) if amt != 0 and pd.notna(amt) else ((qty * price) + comm)
                lots[sym].append({'qty': float(qty), 'cost': float(cost), 'date': date, 'currency': curr})
                
            elif action == 'SELL':
                if sym not in lots or len(lots[sym]) == 0:
                    continue
                    
                remaining_sell = float(qty)
                total_proceeds = float(amt) if amt != 0 and pd.notna(amt) else ((remaining_sell * price) - comm)
                
                trade_cost = 0.0
                trade_qty = 0.0
                first_buy_date = None
                
                while remaining_sell > 0 and len(lots[sym]) > 0:
                    lot = lots[sym][0]
                    sold_qty = min(lot['qty'], remaining_sell)
                    frac = sold_qty / lot['qty']
                    cost_portion = lot['cost'] * frac
                    
                    if first_buy_date is None:
                        first_buy_date = lot['date']
                        
                    trade_cost += cost_portion
                    trade_qty += sold_qty
                    
                    lot['qty'] -= sold_qty
                    lot['cost'] -= cost_portion
                    remaining_sell -= sold_qty
                    
                    if lot['qty'] <= 1e-4:
                        lots[sym].pop(0)
                        
                if trade_qty > 0:
                    frac_of_sell = trade_qty / float(qty)
                    proceeds = total_proceeds * frac_of_sell
                    pnl = proceeds - trade_cost
                    return_pct = (pnl / trade_cost * 100) if trade_cost > 0 else 0
                    
                    if pd.notna(date) and pd.notna(first_buy_date):
                        days = max(1, (date - first_buy_date).days)
                    else:
                        days = 1
                        
                    # Filter out Merger Surrenders so they aren't marked as 100% loss trades
                    is_merger_surrender = 'SURRENDERED' in desc and ('MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc)
                        
                    ann_ret = 0.0
                    if days > 0 and trade_cost > 0:
                        raw_ret = pnl / trade_cost
                        if raw_ret > -1:
                            if days < 30:
                                # For extremely short trades (e.g. 1 day flips), compounding `(1+r)^365` 
                                # artificially inflates returns to +1000% or -99.9%. 
                                # Just default to the raw return to keep averages realistic.
                                ann_ret = return_pct
                            else:
                                ann_ret = ((1 + raw_ret) ** (365/days) - 1) * 100
                        else:
                            ann_ret = -100
                    
                    def safe_float(v):
                        return float(v) if math.isfinite(v) else 0.0
                    
                    def safe_str(v, fallback="Unknown"):
                        return str(v) if pd.notna(v) and str(v).lower() != 'nan' else fallback
                    
                    if not is_merger_surrender:
                        closed_trades.append({
                            'symbol': str(sym),
                            'buyDate': first_buy_date.strftime('%Y/%m/%d') if pd.notna(first_buy_date) else 'Unknown',
                            'sellDate': date.strftime('%Y/%m/%d') if pd.notna(date) else 'Unknown',
                            'quantity': safe_float(trade_qty),
                            'costBasis': safe_float(trade_cost),
                            'proceeds': safe_float(proceeds),
                            'pnl': safe_float(pnl),
                            'returnPct': safe_float(return_pct),
                            'holdingDays': int(days),
                            'annualizedReturn': safe_float(ann_ret),
                            'isWin': bool(pnl >= 0) if math.isfinite(pnl) else False,
                            'currency': str(curr) if pd.notna(curr) else 'CAD',
                            'broker': safe_str(tx.get('Broker'), "Manual"),
                            'account_type': safe_str(tx.get('Account_Type'), "Manual")
                        })
        
        # Sort descending by sellDate
        closed_trades.sort(key=lambda x: x['sellDate'], reverse=True)
        return closed_trades
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

@app.post("/api/transactions")
def add_transaction(tx: Transaction):
    """Add a new transaction to Database and update Holding quantity"""
    try:
        with Session(engine) as session:
            # 1. Match Holding by Symbol, Broker, and Account_Type
            h_q = select(Holding).where(
                Holding.symbol == tx.Symbol,
                Holding.broker == (tx.Broker or "Manual"),
                Holding.account_type == (tx.Account_Type or "Unknown")
            )
            h = session.exec(h_q).first()
            
            if not h:
                h = Holding(
                    symbol=tx.Symbol,
                    broker=tx.Broker or "Manual",
                    account_type=tx.Account_Type or "Unknown",
                    quantity=0.0
                )
                session.add(h)
                session.commit()
                session.refresh(h)
            
            # 2. Add Transaction
            action = str(tx.Transaction_Type).upper()
            qty = float(tx.Quantity or 0.0)
            price = float(tx.Purchase_Price or 0.0)
            comm = float(tx.Commission or 0.0)
            
            # For Sells, amount is usually positive proceeds
            if action == 'SELL':
                amt = (price * qty) - comm
            else:
                amt = (price * qty) + comm
                
            db_tx = DBTransaction(
                holding_id=h.id,
                symbol=tx.Symbol,
                date=pd.to_datetime(tx.Trade_Date),
                type=action,
                quantity=qty,
                price=price,
                commission=comm,
                amount=amt,
                currency="CAD" if tx.Symbol.endswith(".TO") else "USD",
                description=tx.Comment,
                broker=tx.Broker or "Manual",
                account_type=tx.Account_Type or "Unknown",
                source="Manual"
            )
            session.add(db_tx)
            
            # 3. Update Holding quantity
            if action == 'BUY' or 'ADD' in action:
                h.quantity = (h.quantity or 0.0) + qty
            elif action == 'SELL' or 'REDUCE' in action:
                h.quantity = (h.quantity or 0.0) - qty
            
            # Update trade date to latest
            h.trade_date = pd.to_datetime(tx.Trade_Date)
            
            session.add(h)
            session.commit()

            # 4. Cache clearing
            clear_all_caches()
            return {"status": "success", "id": db_tx.id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions/{id}")
def delete_transaction(id: int):
    """Delete a transaction from Database and revert Holding quantity"""
    try:
        with Session(engine) as session:
            tx = session.get(DBTransaction, id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            # Revert Holding quantity
            if tx.holding_id:
                h = session.get(Holding, tx.holding_id)
                if h:
                    action = str(tx.type).upper()
                    qty = float(tx.quantity or 0.0)
                    if action == 'BUY' or 'ADD' in action:
                        h.quantity = (h.quantity or 0.0) - qty
                    elif action == 'SELL' or 'REDUCE' in action:
                        h.quantity = (h.quantity or 0.0) + qty
                    session.add(h)
            
            session.delete(tx)
            session.commit()
            clear_all_caches()
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/db/transactions")
def get_db_transactions():
    with Session(engine) as session:
        txs = session.exec(select(DBTransaction).order_by(DBTransaction.date.desc())).all()
        return [
            {
                "id": tx.id,
                "symbol": tx.symbol,
                "date": sanitize_val(tx.date),
                "type": tx.type,
                "quantity": sanitize_val(tx.quantity),
                "price": sanitize_val(tx.price),
                "commission": sanitize_val(tx.commission),
                "amount": sanitize_val(tx.amount),
                "currency": tx.currency,
                "broker": tx.broker,
                "account_type": tx.account_type,
                "source": tx.source,
                "description": tx.description
            }
            for tx in txs
        ]

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
            # 1. Update the Thesis data
            it = session.exec(select(InvestmentThesis).where(InvestmentThesis.symbol == symbol)).first()
            if not it:
                it = InvestmentThesis(symbol=symbol)
                session.add(it)
            
            if 'Thesis' in data: it.thesis = data['Thesis']
            if 'Conviction' in data: it.conviction = data['Conviction']
            if 'Timeframe' in data: it.timeframe = data['Timeframe']
            if 'Kill Switch' in data: it.kill_switch = data['Kill Switch']
            session.add(it)
            
            # 2. Update Holding comment if provided (rare now, but keeping for compatibility)
            if 'Comment' in data:
                h = session.exec(select(Holding).where(Holding.symbol == symbol)).first()
                if h:
                    h.comment = data['Comment']
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
    """Return all realized P&L rows aggregated dynamically from trades"""
    try:
        trades = get_closed_trades()
        if isinstance(trades, dict) and "error" in trades:
            raise HTTPException(status_code=500, detail=trades["error"])
            
        realized_map = {}
        for t in trades:
            key = (t['symbol'], t['currency'], t['broker'], t['account_type'])
            if key not in realized_map:
                realized_map[key] = {
                    "symbol": t['symbol'],
                    "currency": t['currency'],
                    "pnl_amount": 0.0,
                    "cost_basis_sold": 0.0,
                    "broker": t['broker'],
                    "account_type": t['account_type'],
                    "source": "dynamic_fifo"
                }
            realized_map[key]["pnl_amount"] += t['pnl']
            realized_map[key]["cost_basis_sold"] += t['costBasis']
            
        result = []
        for v in realized_map.values():
            cb = v["cost_basis_sold"]
            pnl_pct = (v["pnl_amount"] / cb * 100) if cb > 0 else 0
            v["pnl_pct"] = round(pnl_pct, 2)
            result.append(v)
            
        # Sort by broker then symbol
        result.sort(key=lambda x: (x['broker'], x['symbol']))
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
            # 1. From Holding table (primary source for current positions)
            holdings = session.exec(select(Holding)).all()
            for h in holdings:
                if h.broker and h.account_type:
                    add_entry(h.symbol, h.broker, h.account_type)
                    
            # 2. From all Transactions history
            all_txs = session.exec(select(DBTransaction)).all()
            for tx in all_txs:
                if tx.broker and tx.account_type:
                    add_entry(tx.symbol, tx.broker, tx.account_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
