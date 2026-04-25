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
from backend.alpha_vantage import get_av_call_count
from analysis import calculate_metrics
from backend.ticker_performance import get_ticker_performance
from backend.cache import clear_all_caches
from backend.database import engine, get_session, create_db_and_tables
from backend.models import Holding, Transaction as DBTransaction, InvestmentThesis, UserSettings
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
    # Handle cases where val might accidentally be a Series or array
    if isinstance(val, (pd.Series, np.ndarray)):
        try:
            val = val.iloc[0] if hasattr(val, 'iloc') else val[0] if len(val) > 0 else None
        except:
            return None

    if val is None or (not isinstance(val, (list, dict)) and pd.isna(val)):
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
def perform_daily_ai_update():
    """Perform a batch AI update for all holdings once per day"""
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        print("INFO: Skipping daily AI update (GOOGLE_API_KEY missing)")
        return

    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    with Session(engine) as session:
        # Check if we already did this today
        last_update = session.exec(select(UserSettings).where(UserSettings.key == "LAST_AI_UPDATE_DATE")).first()
        if last_update and last_update.value == today:
            print(f"INFO: Daily AI update already performed for {today}")
            return

        print(f"INFO: Starting daily AI batch update for {today}...")
        
        # 3. Call Gemini with retry logic
        import urllib.request
        import time
        
        max_retries = 3
        retry_delay = 5 # seconds
        
        for attempt in range(max_retries):
            try:
                # 1. Get all unique symbols (inside loop in case data changed, though unlikely)
                df, _ = load_portfolio_from_db(category="ALL")
                if df.empty: return
                symbols = df['Symbol'].unique().tolist()
                
                # 2. Gather context for all symbols
                fundamentals = get_fundamental_data(symbols)
                news = get_latest_news(symbols)
                
                holdings_context = []
                for sym in symbols:
                    f = fundamentals.get(sym, {})
                    n = news.get(sym, {})
                    holdings_context.append({
                        "symbol": sym,
                        "sector": f.get('Sector'),
                        "recommendation": f.get('Recommendation'),
                        "news": n.get('headline')
                    })
                
                prompt = f"""
                Objective: Provide a concise investment thesis and kill switch for each stock in the following list.
                
                Input Data:
                {json.dumps(holdings_context, indent=2)}
                
                Instructions:
                - Respond ONLY with a JSON object where keys are symbols and values are objects with "thesis" and "kill_switch".
                - Keep each thesis and kill switch under 150 characters.
                - Focus on core value and critical risks.
                
                Example Format:
                {{
                  "AAPL": {{ "thesis": "Dominant ecosystem...", "kill_switch": "Sustained revenue drop..." }}
                }}
                """

                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
                payload_gem = {"contents": [{"parts": [{"text": prompt}]}]}
                req = urllib.request.Request(
                    url, data=json.dumps(payload_gem).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'X-goog-api-key': gemini_key}, method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_data = json.loads(response.read().decode())
                    if 'candidates' in res_data and len(res_data['candidates']) > 0:
                        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                        # Clean markdown if AI included it
                        if "```json" in raw_text:
                            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in raw_text:
                            raw_text = raw_text.split("```")[1].split("```")[0].strip()
                        
                        batch_data = json.loads(raw_text)
                        
                        # 4. Update DB
                        for sym, info in batch_data.items():
                            it = session.exec(select(InvestmentThesis).where(InvestmentThesis.symbol == sym)).first()
                            if not it:
                                it = InvestmentThesis(symbol=sym)
                                session.add(it)
                            
                            # Update if current values are placeholder/empty
                            if not it.thesis or it.thesis.lower() in ["none", "", "--"]:
                                it.thesis = info.get("thesis")
                            if not it.kill_switch or it.kill_switch.lower() in ["none", "", "--"]:
                                it.kill_switch = info.get("kill_switch")
                            it.updated_at = datetime.utcnow()
                        
                        # Mark as done
                        if not last_update:
                            last_update = UserSettings(key="LAST_AI_UPDATE_DATE", value=today)
                            session.add(last_update)
                        else:
                            last_update.value = today
                        
                        session.commit()
                        print(f"INFO: Successfully updated {len(batch_data)} holdings with AI insights.")
                        return # Success!
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    print(f"WARNING: Gemini 429 during daily update. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                else:
                    print(f"ERROR: Daily AI update failed on attempt {attempt+1}: {e}")
                    break

@app.on_event("startup")
def on_startup():
    try:
        create_db_and_tables()
        print("INFO: Database connection established and tables verified.")
        perform_daily_ai_update()
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to the database. {e}")
        print("Backend starting in limited capacity mode.")


@app.get("/")
def read_root():
    return {
        "message": "Holding Analyzer API is running",
        "health": "ok",
        "alpha_vantage_calls": get_av_call_count()
    }

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "alpha_vantage_calls": get_av_call_count(),
        "database_connected": engine is not None,
        "file_status": {
            "portfolio_csv": os.path.exists("portfolio.csv"),
            "portfolio_resp_csv": os.path.exists("portfolio_resp.csv")
        },
        "env_check": {
            "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
            "ALPHA_VANTAGE_API_KEY_ENV": bool(os.getenv("ALPHA_VANTAGE_API_KEY")),
            "TARGET_CAGR": os.getenv("TARGET_CAGR", "0.08")
        }
    }

@app.get("/api/portfolio")
def get_portfolio(category: Optional[str] = None):
    try:
        # Switch to database source
        df, _ = load_portfolio_from_db(category=category)
        print(f"DEBUG: df columns: {df.columns.tolist()}")
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
        
        # Currency detection (TSX .TO symbols are usually CAD except for -U versions)
        def detect_currency(sym):
            if sym.endswith('-U.TO') or sym.endswith('-U'): return 'USD'
            return 'CAD' if sym.endswith('.TO') else 'USD'
            
        df['Currency'] = df['Symbol'].apply(detect_currency)
        
        # FX rate column
        df['FX Rate'] = df['Currency'].apply(lambda c: 1.0 if c == 'CAD' else usd_cad)
        
        # Calculate P&L, CAGR, and Goal metrics using standard analysis logic
        target_cagr = float(os.getenv("TARGET_CAGR", 0.08))
        df = calculate_metrics(df, target_cagr=target_cagr)
        
        # Market Value and Cost Basis in CAD for summary
        df['Market_Value_CAD'] = df['Market Value'] * df['FX Rate']
        df['Cost_Basis_CAD'] = df['Cost Basis'] * df['FX Rate']
        df['PnL_CAD'] = df['P&L'] * df['FX Rate']
        
        # Standardize column names for the response
        # Note: calculate_metrics already produces 'Market Value', 'Cost Basis', and 'P&L'
        
        # Convert prices to CAD for the response
        df['Price (CAD)'] = df['Current Price'] * df['FX Rate']
        
        # Add aliases for frontend compatibility
        df['Market_Value'] = df['Market Value']
        df['PnL'] = df['P&L']
        
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
            # Multiply by 100 because the frontend expects percentage (1.5 for 1.5%)
            holding_dict['Day Change'] = float(daily_changes.get(sym, 0.0)) * 100.0
            
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
        
        # Calculate weighted CAGR and exposures using CAD-equivalent values for accuracy across currencies
        total_mv_cad = df['Market_Value_CAD'].sum()
        weighted_cagr = (df['CAGR'] * df['Market_Value_CAD']).sum() / total_mv_cad if total_mv_cad > 0 else 0
        
        # Calculate exposures in CAD
        try:
            sector_exp = df.groupby('Sector')['Market_Value_CAD'].sum().to_dict()
        except: sector_exp = {}
        
        try:
            country_exp = df.groupby('Country')['Market_Value_CAD'].sum().to_dict()
        except: country_exp = {}
        
        try:
            account_exp = df.groupby('Account_Type')['Market_Value_CAD'].sum().to_dict()
        except: account_exp = {}
        
        try:
            broker_exp = df.groupby('Broker')['Market_Value_CAD'].sum().to_dict()
        except: broker_exp = {}
        
        # Calculate summary per portfolio category
        category_summaries = {}
        for cat in df['Portfolio_Category'].unique():
            cat_df = df[df['Portfolio_Category'] == cat]
            cat_mv = cat_df['Market_Value_CAD'].sum()
            cat_cost = cat_df['Cost_Basis_CAD'].sum()
            
            # Calculate USD equivalent for the category
            cat_mv_usd = 0
            for _, h in cat_df.iterrows():
                if h['Currency'] == 'USD':
                    cat_mv_usd += h['Market Value']
                else:
                    cat_mv_usd += h['Market Value'] / usd_cad
            
            category_summaries[cat] = {
                "total_value": sanitize_val(cat_mv),
                "total_value_usd": sanitize_val(cat_mv_usd),
                "total_cost": sanitize_val(cat_cost),
                "total_pnl": sanitize_val(cat_mv - cat_cost),
            }
        
        # Calculate total USD value
        total_mv_usd = 0
        for _, h in df.iterrows():
            if h['Currency'] == 'USD':
                total_mv_usd += h['Market Value']
            else:
                total_mv_usd += h['Market Value'] / usd_cad

        return {
            "summary": {
                "total_value": sanitize_val(total_mv_cad),
                "total_value_usd": sanitize_val(total_mv_usd),
                "total_cost": sanitize_val(df['Cost_Basis_CAD'].sum()),
                "total_pnl": sanitize_val(df['PnL_CAD'].sum()),
                "weighted_cagr": sanitize_val(weighted_cagr),
                "usd_cad_rate": sanitize_val(usd_cad),
                "categories": category_summaries
            },
            "holdings": holdings_list,
            "sector_exposure": {k: sanitize_val(v) for k, v in sector_exp.items()},
            "country_exposure": {k: sanitize_val(v) for k, v in country_exp.items()},
            "account_exposure": {k: sanitize_val(v) for k, v in account_exp.items()},
            "broker_exposure": {k: sanitize_val(v) for k, v in broker_exp.items()}
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dividends")
def get_dividends(category: Optional[str] = None):
    try:
        df, _ = load_portfolio_from_db(category=category)
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
        if df.empty: 
            print("DEBUG: performance df is empty")
            return []
        
        history = get_portfolio_history(df)
        if history.empty:
             print("DEBUG: history df is empty")
             return []
        
        # Convert date to string
        history['date'] = pd.to_datetime(history['date'], utc=True).dt.strftime('%Y/%m/%d')
        
        return history.to_dict(orient="records")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticker-performance")
def get_ticker_perf():
    """Get per-ticker performance over various timeframes"""
    try:
        df, _ = load_portfolio_from_db()
        if df.empty:
            print("DEBUG: ticker-perf df is empty")
            return {}
        
        symbols = df['Symbol'].unique().tolist()
        performance = get_ticker_performance(symbols)
        
        # Ensure it's a dict
        if not isinstance(performance, dict):
            print(f"DEBUG: performance is not a dict: {type(performance)}")
            return {}
            
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

class TransactionUpdate(BaseModel):
    Symbol: Optional[str] = None
    Purchase_Price: Optional[float] = None
    Quantity: Optional[float] = None
    Commission: Optional[float] = None
    Trade_Date: Optional[str] = None
    Transaction_Type: Optional[str] = None
    Broker: Optional[str] = None
    Account_Type: Optional[str] = None
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
def get_transactions(category: Optional[str] = None):
    """Fetch all transactions from DB formatted for frontend"""
    try:
        with Session(engine) as session:
            query = select(DBTransaction).order_by(DBTransaction.date.desc())
            if category and category.upper() != 'ALL':
                query = query.where(DBTransaction.portfolio_category == category)
            
            # session.exec(query) was not working for filtering in some environments
            txs = session.exec(query).all()
            
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
                    "Comment": tx.description or "",
                    "Amount": sanitize_val(tx.amount),
                    "Portfolio Category": tx.portfolio_category
                }
                for tx in txs
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/closed-trades")
def get_closed_trades(category: Optional[str] = None):
    """Fetch individually matched closed trades from full broker CSV history (FIFO basis)"""
    try:
        # Fetch entirely from database transactions instead of CSV
        with Session(engine) as session:
            df_tx = get_processed_transactions(session)
            
        if df_tx.empty:
            return []

        if category and category.upper() != 'ALL':
            df_tx = df_tx[df_tx['Portfolio_Category'].str.upper() == category.upper()]
            
        # Ensure chronological order
        df_tx = df_tx.sort_values(by=['Date'])
        
        lots = {}
        closed_trades = []
        
        for _, tx in df_tx.iterrows():
            sym = tx['Symbol']
            broker = tx.get('Broker', 'Unknown')
            account_type = tx.get('Account_Type', 'Unknown')
            action = str(tx['Action']).upper()
            date = tx['Date']
            curr = tx['Currency']
            desc = str(tx.get('Description', '')).upper()
            key = (sym, broker, account_type)
            
            # Use absolute values for quantity and numbers to handle different broker formats
            qty = abs(float(tx['Quantity']))
            price = abs(float(tx['Price']))
            comm = abs(float(tx.get('Commission', 0.0)))
            amt = abs(float(tx.get('Amount', 0.0)))
            
            if qty <= 0:
                continue
            
            # Exclude Norbert's Gambit currency conversions and specific mutual funds
            excluded_symbols = ["DLR.TO", "DLR.U.TO", "DLR", "RBF526", "RBF5662", "RBF266"]
            if str(sym).upper() in excluded_symbols:
                continue
                
            if action in ['BUY', 'DIV', 'DRIP'] or 'TRANSF' in action or ('RECEIVED' in desc and ('MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc)):
                if key not in lots: lots[key] = []
                cost = amt if amt != 0 else ((qty * price) + comm)
                
                # Extract BOOK VALUE from description for transfers
                if cost < 0.01:
                    import re
                    match = re.search(r"BOOK VALUE\s+([\d\.,]+)", desc)
                    if match:
                        bv_str = match.group(1).replace(',', '')
                        try: cost = float(bv_str)
                        except: pass
                    elif re.search(r"BV\s*:?\s*([\d\.,]+)", desc):
                        match = re.search(r"BV\s*:?\s*([\d\.,]+)", desc)
                        bv_str = match.group(1).replace(',', '')
                        try: cost = float(bv_str)
                        except: pass

                lots[key].append({
                    'qty': qty, 
                    'cost': cost, 
                    'date': date, 
                    'currency': curr,
                    'category': str(tx.get('Portfolio_Category', 'Retirement'))
                })
                
            elif action == 'SELL':
                if key not in lots or len(lots[key]) == 0:
                    continue
                    
                remaining_sell = qty
                total_proceeds = amt if amt != 0 else ((qty * price) - comm)
                
                trade_cost = 0.0
                trade_qty = 0.0
                first_buy_date = None
                
                while remaining_sell > 0 and len(lots[key]) > 0:
                    lot = lots[key][0]
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
                        lots[key].pop(0)
                        
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
                            'portfolio_category': str(tx.get('Portfolio_Category', 'Retirement')),
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

        # ---- NEW: Add Open Positions to Analysis ----
        # Remaining lots are open positions
        all_symbols = [key[0] for key in lots.keys()]
        current_prices = get_current_prices(all_symbols)
        
        for key, lot_list in lots.items():
            sym, broker, account = key
            for lot in lot_list:
                if lot['qty'] > 1e-4:
                    cp = current_prices.get(sym, 0.0)
                    if cp <= 0: continue
                    
                    trade_qty = lot['qty']
                    trade_cost = lot['cost']
                    proceeds = trade_qty * cp
                    pnl = proceeds - trade_cost
                    return_pct = (pnl / trade_cost * 100) if trade_cost > 0 else 0
                    
                    days = max(1, (datetime.utcnow() - lot['date']).days)
                    
                    ann_ret = 0.0
                    if days > 0 and trade_cost > 0:
                        raw_ret = pnl / trade_cost
                        if raw_ret > -1:
                            if days < 30: ann_ret = return_pct
                            else: ann_ret = ((1 + raw_ret) ** (365/days) - 1) * 100
                        else: ann_ret = -100

                    # Find portfolio category for this holding
                    # We might need to look back at the df_tx or just default
                    # In a real scenario, we'd have the category in the lot
                    
                    closed_trades.append({
                        'symbol': str(sym),
                        'portfolio_category': lot['category'], 
                        'buyDate': lot['date'].strftime('%Y/%m/%d') if pd.notna(lot['date']) else 'Unknown',
                        'sellDate': 'OPEN',
                        'quantity': float(trade_qty),
                        'costBasis': float(trade_cost),
                        'proceeds': float(proceeds),
                        'pnl': float(pnl),
                        'returnPct': float(return_pct),
                        'holdingDays': int(days),
                        'annualizedReturn': float(ann_ret),
                        'isWin': bool(pnl >= 0),
                        'currency': lot['currency'],
                        'broker': str(broker),
                        'account_type': str(account)
                    })

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
            # Map DRIP and Transfer In to BUY behavior (increase quantity)
            if action in ['BUY', 'DRIP', 'TRANSFER IN', 'TRANSF IN'] or 'ADD' in action:
                h.quantity = (h.quantity or 0.0) + qty
            elif action in ['SELL'] or 'REDUCE' in action:
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

@app.put("/api/transactions/{id}")
def update_transaction(id: int, tx: TransactionUpdate):
    """Update an existing transaction and adjust Holding quantity"""
    try:
        with Session(engine) as session:
            db_tx = session.get(DBTransaction, id)
            if not db_tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            # 1. Revert OLD Holding quantity
            if db_tx.holding_id:
                h_old = session.get(Holding, db_tx.holding_id)
                if h_old:
                    action_old = str(db_tx.type).upper()
                    qty_old = float(db_tx.quantity or 0.0)
                    if action_old in ['BUY', 'DRIP', 'TRANSFER IN', 'TRANSF IN'] or 'ADD' in action_old:
                        h_old.quantity = (h_old.quantity or 0.0) - qty_old
                    elif action_old in ['SELL'] or 'REDUCE' in action_old:
                        h_old.quantity = (h_old.quantity or 0.0) + qty_old
                    session.add(h_old)

            # 2. Update Transaction fields
            if tx.Symbol is not None: db_tx.symbol = tx.Symbol
            if tx.Purchase_Price is not None: db_tx.price = tx.Purchase_Price
            if tx.Quantity is not None: db_tx.quantity = tx.Quantity
            if tx.Commission is not None: db_tx.commission = tx.Commission
            if tx.Trade_Date is not None: db_tx.date = pd.to_datetime(tx.Trade_Date)
            if tx.Transaction_Type is not None: db_tx.type = tx.Transaction_Type.upper()
            if tx.Broker is not None: db_tx.broker = tx.Broker
            if tx.Account_Type is not None: db_tx.account_type = tx.Account_Type
            if tx.Comment is not None: db_tx.description = tx.Comment
            
            # Recalculate amount
            qty = float(db_tx.quantity or 0.0)
            price = float(db_tx.price or 0.0)
            comm = float(db_tx.commission or 0.0)
            if db_tx.type == 'SELL':
                db_tx.amount = (price * qty) - comm
            else:
                db_tx.amount = (price * qty) + comm
            
            # 3. Apply NEW Holding quantity
            # Find or create holding for new symbol/broker/account
            h_new_q = select(Holding).where(
                Holding.symbol == db_tx.symbol,
                Holding.broker == (db_tx.broker or "Manual"),
                Holding.account_type == (db_tx.account_type or "Unknown")
            )
            h_new = session.exec(h_new_q).first()
            if not h_new:
                h_new = Holding(
                    symbol=db_tx.symbol,
                    broker=db_tx.broker or "Manual",
                    account_type=db_tx.account_type or "Unknown",
                    quantity=0.0
                )
                session.add(h_new)
                session.commit()
                session.refresh(h_new)
            
            db_tx.holding_id = h_new.id
            action_new = str(db_tx.type).upper()
            qty_new = float(db_tx.quantity or 0.0)
            if action_new in ['BUY', 'DRIP', 'TRANSFER IN', 'TRANSF IN'] or 'ADD' in action_new:
                h_new.quantity = (h_new.quantity or 0.0) + qty_new
            elif action_new in ['SELL'] or 'REDUCE' in action_new:
                h_new.quantity = (h_new.quantity or 0.0) - qty_new
            
            h_new.trade_date = db_tx.date
            
            session.add(db_tx)
            session.add(h_new)
            session.commit()

            clear_all_caches()
            return {"status": "success"}
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
                    # Match the addition logic exactly to undo it properly
                    if action in ['BUY', 'DRIP', 'TRANSFER IN', 'TRANSF IN'] or 'ADD' in action:
                        h.quantity = (h.quantity or 0.0) - qty
                    elif action in ['SELL'] or 'REDUCE' in action:
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
            
            # 2. Update Holding comment if provided
            if 'Comment' in data:
                h_q = select(Holding).where(Holding.symbol == symbol)
                if 'Portfolio_Category' in data:
                    h_q = h_q.where(Holding.portfolio_category == data['Portfolio_Category'])
                
                h = session.exec(h_q).first()
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

@app.post("/api/ai/analyze")
def analyze_with_ai(payload: dict = Body(...)):
    """Analyze the portfolio using Google Gemini (if key exists) or local Ollama"""
    try:
        import json
        import os
        
        category = payload.get('category', 'ALL')
        
        # 1. Get portfolio data for context (respecting category filter)
        df, _ = load_portfolio_from_db(category=category)
        if df.empty:
            return {"analysis": f"Portfolio ({category}) is empty. Add some transactions first."}
        
        # 2. Get current prices and fundamental metrics
        symbols = df['Symbol'].unique().tolist()
        prices = get_current_prices(symbols)
        fundamentals = get_fundamental_data(symbols)
        
        # 3. Format context for LLM
        holdings_context = []
        for _, row in df.iterrows():
            sym = row['Symbol']
            qty = row['Quantity']
            price = prices.get(sym, 0.0)
            fund = fundamentals.get(sym, {})
            
            holdings_context.append({
                "symbol": sym,
                "quantity": qty,
                "current_price": price,
                "sector": fund.get('Sector', 'Unknown'),
                "industry": fund.get('Industry', 'Unknown'),
                "recommendation": fund.get('Recommendation', 'Unknown')
            })
        
        prompt = f"""
        Objective: Summarize the following list of stock holdings. Identify the most prominent sectors, concentration levels, and any noticeable trends in analyst recommendations.
        
        Input Data:
        {json.dumps(holdings_context, indent=2)}
        
        Specific Task: {payload.get('query', 'Provide a summary of the holdings.')}
        
        Instructions:
        - Provide 3-4 bullet points.
        - Be factual and objective based solely on the input data.
        - Use Markdown formatting.
        - Avoid phrases like 'I recommend' or 'You should'.
        """

        # 4. Check for Google Gemini API Key
        gemini_key = os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                import urllib.request
                # Use specified REST API format and model
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
                
                payload_gem = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload_gem).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'X-goog-api-key': gemini_key
                    },
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode())
                    if 'candidates' in res_data and len(res_data['candidates']) > 0:
                        gem_text = res_data['candidates'][0]['content']['parts'][0]['text']
                        return {"analysis": gem_text, "model": "gemini-flash-latest (REST)"}
                    else:
                        print(f"Gemini unexpected response structure: {res_data}")
            except Exception as gem_e:
                print(f"Gemini REST failed: {gem_e}")
                if hasattr(gem_e, 'read'):
                    print(f"Error details: {gem_e.read().decode()}")
                # Fall through to Ollama
        
        # 5. Fallback to local Ollama
        try:
            import urllib.request
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
            ollama_model = os.getenv("OLLAMA_MODEL", "functiongemma:latest")
            
            data = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False
            }
            
            req = urllib.request.Request(
                ollama_url, 
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode())
                return {"analysis": res_data.get("response", "No response from LLM."), "model": f"ollama:{ollama_model}"}
        except Exception as ollama_e:
            return {"analysis": f"AI Analysis failed. (Gemini key missing, and Ollama error: {str(ollama_e)})"}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"analysis": f"Critical AI system error: {str(e)}"}

@app.post("/api/ai/research-holding")
def research_holding_with_ai(payload: dict = Body(...)):
    """Deep dive research for a specific ticker using Gemini"""
    try:
        symbol = payload.get('symbol')
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
            
        # 1. Gather all possible context for this symbol
        prices = get_current_prices([symbol])
        fundamentals = get_fundamental_data([symbol])
        technical = get_technical_data([symbol])
        news = get_latest_news([symbol])
        
        # 2. Get existing thesis from DB
        with Session(engine) as session:
            it = session.exec(select(InvestmentThesis).where(InvestmentThesis.symbol == symbol)).first()
            
        # 3. Format the context
        f = fundamentals.get(symbol, {})
        t = technical.get(symbol, {})
        n = news.get(symbol, {})
        
        context = {
            "symbol": symbol,
            "current_price": prices.get(symbol, 0.0),
            "fundamentals": {
                "sector": f.get('Sector'),
                "industry": f.get('Industry'),
                "market_cap": f.get('Market Cap'),
                "trailing_pe": f.get('Trailing P/E'),
                "forward_pe": f.get('Forward P/E'),
                "peg_ratio": f.get('PEG Ratio'),
                "revenue_growth": f.get('Rev Growth'),
                "profit_margin": f.get('Profit Margin'),
                "recommendation": f.get('Recommendation')
            },
            "technical": {
                "rsi": t.get('RSI'),
                "scorecard": t.get('Scorecard')
            },
            "news": n.get('headline'),
            "existing_thesis": {
                "thesis": it.thesis if it else "None",
                "conviction": it.conviction if it else "None",
                "kill_switch": it.kill_switch if it else "None"
            }
        }
        
        prompt = f"""
        Objective: Perform a professional 'Quant-Mental' deep dive on {symbol}.
        
        Data Context:
        {json.dumps(context, indent=2)}
        
        Instructions:
        1. Summarize the current fundamental health and technical position.
        2. Evaluate the existing investment thesis (if any) against recent news and metrics.
        3. Identify 2-3 key catalysts or risks (Kill Switches) to watch.
        4. Provide an 'AI Sentiment' score (1-10) and a brief justification.
        
        Formatting:
        - Use clean Markdown with headers.
        - Be concise but insightful.
        - Avoid generic advice; be specific to {symbol}.
        """

        # 4. Call Gemini (same REST logic as above)
        gemini_key = os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                import urllib.request
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
                payload_gem = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload_gem).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'X-goog-api-key': gemini_key},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode())
                    if 'candidates' in res_data and len(res_data['candidates']) > 0:
                        return {"analysis": res_data['candidates'][0]['content']['parts'][0]['text'], "model": "gemini-flash-latest"}
            except Exception as e:
                print(f"Gemini failed for research: {e}")

        # Fallback to local Ollama
        try:
            import urllib.request
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
            ollama_model = os.getenv("OLLAMA_MODEL", "functiongemma:latest")
            
            data = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False
            }
            
            req = urllib.request.Request(
                ollama_url, 
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode())
                return {"analysis": res_data.get("response", "No response from local LLM."), "model": f"ollama:{ollama_model}"}
        except Exception as ollama_e:
            return {"analysis": f"AI Research unavailable. (Gemini: 429/Busy, Ollama: {str(ollama_e)})", "model": "Error"}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"analysis": f"Research failed: {str(e)}", "model": "Error"}

@app.post("/api/ai/draft-thesis")
def draft_thesis_with_ai(payload: dict = Body(...)):
    """Draft an investment thesis or kill switch using AI"""
    try:
        symbol = payload.get('symbol')
        field = payload.get('field', 'Thesis') # Thesis or Kill Switch
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
            
        # Gather context
        fundamentals = get_fundamental_data([symbol])
        news = get_latest_news([symbol])
        
        f = fundamentals.get(symbol, {})
        n = news.get(symbol, {})
        
        prompt = f"""
        Objective: Draft a concise, professional {field} for {symbol}.
        
        Company Context:
        - Sector: {f.get('Sector')}
        - Recommendation: {f.get('Recommendation')}
        - Latest News: {n.get('headline')}
        
        Field to draft: {field}
        
        Instructions:
        - If drafting 'Thesis': Focus on the core value proposition and why it's a good investment.
        - If drafting 'Kill Switch': Focus on what specific events or metrics would invalidate the thesis.
        - Keep it under 2 sentences.
        - Be direct and analytical.
        """

        gemini_key = os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                import urllib.request
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
                payload_gem = {"contents": [{"parts": [{"text": prompt}]}]}
                req = urllib.request.Request(
                    url, data=json.dumps(payload_gem).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'X-goog-api-key': gemini_key}, method='POST'
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode())
                    if 'candidates' in res_data and len(res_data['candidates']) > 0:
                        return {"draft": res_data['candidates'][0]['content']['parts'][0]['text'].strip(), "model": "gemini-flash-latest"}
            except Exception as e:
                print(f"Gemini failed for drafting: {e}")

        # Fallback to Ollama
        try:
            import urllib.request
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
            ollama_model = os.getenv("OLLAMA_MODEL", "functiongemma:latest")
            
            data = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False
            }
            
            req = urllib.request.Request(
                ollama_url, 
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode())
                return {"draft": res_data.get("response", "No response from local LLM.").strip(), "model": f"ollama:{ollama_model}"}
        except Exception as ollama_e:
            return {"draft": f"Unable to generate {field} draft. (Gemini: 429/Busy, Ollama: {str(ollama_e)})", "model": "Error"}
            
    except Exception as e:
        return {"draft": f"Drafting failed: {str(e)}", "model": "Error"}

@app.get("/api/realized-pnl")
def get_realized_pnl(category: Optional[str] = None):
    """Return all realized P&L rows aggregated dynamically from trades"""
    try:
        trades = get_closed_trades(category)
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
    read strictly from the Database where the holding is currently active.
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
            # Primary source for current positions: Only where quantity > 0
            holdings = session.exec(select(Holding).where(Holding.quantity > 0)).all()
            for h in holdings:
                if h.broker and h.account_type:
                    add_entry(h.symbol, h.broker, h.account_type)
                    
        return result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SettingPayload(BaseModel):
    key: str
    value: str

@app.get("/api/settings/{key}")
def get_setting(key: str):
    try:
        with Session(engine) as session:
            setting = session.exec(select(UserSettings).where(UserSettings.key == key)).first()
            if setting:
                return {"key": setting.key, "value": setting.value}
            return {"key": key, "value": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
def save_setting(payload: SettingPayload):
    try:
        with Session(engine) as session:
            setting = session.exec(select(UserSettings).where(UserSettings.key == payload.key)).first()
            if not setting:
                setting = UserSettings(key=payload.key, value=payload.value)
                session.add(setting)
            else:
                setting.value = payload.value
            session.commit()
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
