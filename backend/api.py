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

# Add parent directory to path to import existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_portfolio_holdings
from market_data import get_current_prices, get_fundamental_data, get_technical_data, get_dividend_calendar, get_usd_to_cad_rate, get_portfolio_history, get_latest_news
from analysis import calculate_metrics
from backend.ticker_performance import get_ticker_performance

app = FastAPI(title="Holding Analyzer API")

# Allow CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
   allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "portfolio.csv")
THESIS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "thesis.json")
TARGET_CAGR = 0.10

# Load thesis data once at startup
THESIS_DATA = {}
try:
    with open(THESIS_PATH, 'r') as f:
        THESIS_DATA = json.load(f)
    print(f"Loaded thesis data for {len(THESIS_DATA)} symbols")
except Exception as e:
    print(f"Warning: Could not load thesis.json: {e}")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/portfolio")
def get_portfolio():
    try:
        df = load_portfolio_holdings(CSV_PATH)
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
            
            # Add thesis data
            thesis = THESIS_DATA.get(sym, {})
            holding_dict['Thesis'] = thesis.get('Thesis', '')
            holding_dict['Conviction'] = thesis.get('Conviction', '')
            holding_dict['Timeframe'] = thesis.get('Timeframe', '')
            holding_dict['Kill Switch'] = thesis.get('Kill Switch', '')
            
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
        df = load_portfolio_holdings(CSV_PATH)
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
        df = load_portfolio_holdings(CSV_PATH)
        if df.empty: return []
        
        history = get_portfolio_history(df)
        if history.empty:
             return []
        
        # Convert Date to string
        history['Date'] = history['Date'].dt.strftime('%Y/%m/%d')
        
        return history.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticker-performance")
def get_ticker_perf():
    """Get per-ticker performance over various timeframes"""
    try:
        df = load_portfolio_holdings(CSV_PATH)
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
    Transaction_Type: str = "Buy" # Buy or Sell
    Comment: Optional[str] = ""

@app.get("/api/transactions")
def get_transactions():
    """Get raw transactions from CSV"""
    try:
        if not os.path.exists(CSV_PATH):
            return []
        df = pd.read_csv(CSV_PATH)
        # Filter for rows that are actually transactions (must have Symbol and Price/Qty)
        # Specifically avoid rows like 'CAD=X' which might be in the CSV for other purposes
        if 'Trade Date' in df.columns:
             df = df.dropna(subset=['Trade Date'])
        elif 'Purchase Price' in df.columns:
             df = df.dropna(subset=['Purchase Price'])
        
        # Format Trade Date for consistency in frontend
        if 'Trade Date' in df.columns:
             # Handle numeric YYYYMMDD or string dates, and fallback to 'Date' if missing
             def parse_trade_date(row):
                 td = str(row.get('Trade Date', '')).split('.')[0].strip()
                 if td and td != 'nan':
                     try:
                         # Try YYYYMMDD first if it looks like it
                         if len(td) == 8 and td.isdigit():
                             return pd.to_datetime(td, format='%Y%m%d').strftime('%Y/%m/%d')
                         return pd.to_datetime(td).strftime('%Y/%m/%d')
                     except:
                         pass
                 
                 # Fallback to 'Date' column if Trade Date is unavailable
                 main_date = str(row.get('Date', '')).strip()
                 if main_date and main_date != 'nan':
                     try:
                         return pd.to_datetime(main_date).strftime('%Y/%m/%d')
                     except:
                         pass
                 return None

             df['Trade Date'] = df.apply(parse_trade_date, axis=1)
        
        # Replace NaN and Inf with None for JSON compliance
        df = df.replace([np.nan, np.inf, -np.inf], None)
        
        # Add a stable ID for frontend to reference
        df['id'] = range(len(df))
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transactions")
def add_transaction(tx: Transaction):
    """Add a new transaction to CSV"""
    try:
        # Load existing
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
        else:
            # Create with default columns if doesn't exist
            cols = ['Symbol', 'Current Price', 'Date', 'Time', 'Change', 'Open', 'High', 'Low', 'Volume', 'Trade Date', 'Purchase Price', 'Quantity', 'Commission', 'High Limit', 'Low Limit', 'Comment', 'Transaction Type']
            df = pd.DataFrame(columns=cols)
        
        # Prepare new row
        new_row = {
            'Symbol': tx.Symbol,
            'Purchase Price': tx.Purchase_Price,
            'Quantity': tx.Quantity,
            'Commission': tx.Commission,
            'Trade Date': tx.Trade_Date,
            'Transaction Type': tx.Transaction_Type,
            'Comment': tx.Comment,
            'Date': datetime.now().strftime('%Y/%m/%d'),
            'Time': datetime.now().strftime('%H:%M %Z'),
            'Current Price': 0, # Will be updated by market data later
        }
        
        # Append
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(CSV_PATH, index=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions/{index}")
def delete_transaction(index: int):
    """Delete a transaction from CSV by index"""
    try:
        if not os.path.exists(CSV_PATH):
            raise HTTPException(status_code=404, detail="CSV not found")
        
        df = pd.read_csv(CSV_PATH)
        if index < 0 or index >= len(df):
            raise HTTPException(status_code=404, detail="Index out of range")
        
        df = df.drop(df.index[index])
        df.to_csv(CSV_PATH, index=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
