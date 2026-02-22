import pandas as pd
import os
from datetime import datetime
import glob
import re

def parse_cibc(file_path):
    """
    Parses CIBC Transaction History CSV.
    Columns: Transaction Date, Settlement Date, Currency of Sub-account Held In, Transaction Type, Symbol, ... Quantity, Price, Commission, Amount, ...
    """
    # Header starts at row 10 (0-indexed 9)
    df = pd.read_csv(file_path, skiprows=9, on_bad_lines='skip')
    
    # Filter for relevant transaction types
    df = df[df['Transaction Type'].isin(['Buy', 'Sell', 'Dividend', 'Reinvest', 'Merger', 'Transf In'])]
    
    # Clean up Symbol
    df['Symbol'] = df['Symbol'].str.strip()
    
    # Handle dates
    df['Date'] = pd.to_datetime(df['Transaction Date'], errors='coerce')
    
    # CIBC: Extract Book Value from Description if Amount is 0 for Transfers
    def get_amount(row):
        amt = pd.to_numeric(str(row['Amount']).replace(',', ''), errors='coerce')
        if amt == 0 or pd.isna(amt):
            desc = str(row['Description']).upper()
            if 'BOOK VALUE' in desc:
                match = re.search(r'BOOK VALUE\s+([\d,.]+)', desc)
                if match:
                    val = float(match.group(1).replace(',', ''))
                    # For Buy/Transf In, we want negative if it's a cost, but my parser handles abs() later.
                    return -val if row['Transaction Type'] in ['Buy', 'Transf In', 'Merger'] else val
        return amt

    # Normalize Action
    result = pd.DataFrame({
        'Date': df['Date'],
        'Symbol': df['Symbol'],
        'Action': df['Transaction Type'],
        'Quantity': pd.to_numeric(df['Quantity'].astype(str).str.replace(',', ''), errors='coerce'),
        'Price': pd.to_numeric(df['Price'].astype(str).str.replace(',', ''), errors='coerce'),
        'Commission': pd.to_numeric(df['Commission'].astype(str).str.replace(',', ''), errors='coerce').fillna(0),
        'Amount': df.apply(get_amount, axis=1),
        'Currency': df['Currency of Amount'],
        'Source': 'CIBC'
    })
    
    # Normalize Action
    def get_cibc_action(row):
        t_type = str(row['Transaction Type'])
        desc = str(row['Description']).upper()
        if t_type == 'Merger':
            if 'SURRENDERED' in desc: return 'SELL'
            if 'RECEIVED' in desc: return 'BUY'
        
        mapping = {
            'Buy': 'BUY', 'Sell': 'SELL', 'Dividend': 'DIV',
            'Reinvest': 'BUY', 'Transf In': 'BUY', 'Transf Out': 'SELL',
            'Sell (short)': 'SELL'
        }
        return mapping.get(t_type, 'OTHER')

    result['Action'] = df.apply(get_cibc_action, axis=1)
    result['Description'] = df['Description']
    
    # In CIBC, Sell quantity is positive, but Amount is positive (proceeds).
    # Buy quantity is positive, Amount is negative (cost).
    # We want Quantity to be positive for both, but Action to distinguish.
    
    result['Symbol'] = result['Symbol'].fillna('')
    return result.dropna(subset=['Date'])

def parse_rbc(file_path):
    """
    Parses RBC Activity CSV.
    Columns: Date, Activity, Symbol, Symbol Description, Quantity, Price, Settlement Date, Account, Value, Currency, Description
    """
    # Header starts at row 9 (0-indexed 8)
    df = pd.read_csv(file_path, skiprows=8)
    
    # Clean Symbol
    df['Symbol'] = df['Symbol'].str.strip()
    
    # Handle dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # RBC Action mapping
    def get_rbc_action(row):
        act = str(row['Activity'])
        desc = str(row['Description']).upper()
        if 'REINV' in desc or 'REI -' in desc:
            return 'BUY'
        if act == 'Buy': return 'BUY'
        if act == 'Sell': return 'SELL'
        if act in ['Dividends', 'Distribution']: return 'DIV'
        return 'OTHER'
    
    result = pd.DataFrame({
        'Date': df['Date'],
        'Symbol': df['Symbol'],
        'Action': df.apply(get_rbc_action, axis=1),
        'Quantity': pd.to_numeric(df['Quantity'].astype(str).str.replace(',', ''), errors='coerce').abs(),
        'Price': pd.to_numeric(df['Price'].astype(str).str.replace(',', ''), errors='coerce'),
        'Commission': 0.0,
        'Amount': pd.to_numeric(df['Value'].astype(str).str.replace(',', ''), errors='coerce'),
        'Currency': df['Currency'],
        'Description': df['Description'],
        'Source': 'RBC'
    })
    
    return result.dropna(subset=['Symbol', 'Date'])

def parse_td(file_path):
    """
    Parses TD Activity CSV.
    Columns: Trade Date, Settle Date, Description, Action, Quantity, Price, Commission, Net Amount, Security Type, Currency
    """
    # Header starts at row 4 (0-indexed 3)
    df = pd.read_csv(file_path, skiprows=3)
    
    # TD Symbols are in the Description or Symbol column? 
    # In the sample, Symbol is NOT a column, it's in Description. 
    # "VANGUARD 500 INDX ETF-NEW"
    # Wait, in the sample I saw Action column but no Symbol column.
    
    # Let's extract symbol from Description. This is tricky.
    # Usually TD exports have a Symbol column if it's the right format.
    # From the sample: 
    # 4: Trade Date,Settle Date,Description,Action,Quantity,Price,Commission,Net Amount,Security Type,Currency
    # 5: 24 Dec 2025,24 Dec 2025,VANGUARD 500 INDX ETF-NEW,DRIP,0.05831,,,-36.91,ETF,,
    
    # Manual mapping for common symbols or attempt extraction
    # Actually, the user's portfolio.csv has symbols like VOO, MSFT.
    
    def extract_symbol(desc):
        if 'VANGUARD 500' in desc: return 'VOO' # Example mapping
        if 'MICROSOFT' in desc: return 'MSFT'
        if 'BERKSHIRE' in desc: return 'BRK-B'
        if 'TESLA' in desc: return 'TSLA'
        # Fallback: check if description matches any symbol in a list
        # For now, let's keep it simple or try to find a Symbol column
        return desc # Need better logic here
    
    # TD Action mapping
    action_map = {
        'BUY': 'BUY',
        'SELL': 'SELL',
        'DIV': 'DIV',
        'DRIP': 'BUY',
        'TXPDDV': 'DIV'
    }
    
    result = pd.DataFrame({
        'Date': pd.to_datetime(df['Trade Date'], errors='coerce'),
        'Symbol': df['Description'].apply(extract_td_symbol),
        'Action': df['Action'].map(action_map),
        'Quantity': pd.to_numeric(df['Quantity'], errors='coerce').abs(),
        'Price': pd.to_numeric(df['Price'], errors='coerce'),
        'Commission': pd.to_numeric(df['Commission'], errors='coerce').fillna(0).abs(),
        'Amount': pd.to_numeric(df['Net Amount'], errors='coerce'),
        'Currency': df['Currency'],
        'Description': df['Description'],
        'Source': 'TD'
    })
    
    # Fill in currency if missing (TD USD files usually have it in the name)
    if 'USD' in file_path:
        result['Currency'] = result['Currency'].fillna('USD')
    else:
        result['Currency'] = result['Currency'].fillna('CAD')
        
    return result.dropna(subset=['Symbol', 'Date'])

# Mapping for TD Symbol Extraction
TD_SYMBOL_MAP = {
    'VANGUARD 500': 'VOO',
    'MICROSOFT': 'MSFT',
    'BERKSHIRE': 'BRK-B',
    'TESLA': 'TSLA',
    'ALIBABA': 'BABA',
    'VANGUARD FTSE CANADIAN HIGH': 'VDY.TO',
    'ISHR S&PTSX CMP HI DV ETF': 'XEI.TO',
    'ISHARES CORE MSCI EAFE': 'XEF.TO',
    'ISHARES CORE MSCI EM': 'XEC.TO',
    'ISHARES S&P/TSX 60': 'XIU.TO',
    'CANADIAN IMPERIAL': 'CM.TO',
    'TORONTO-DOMINION': 'TD.TO',
    'WHITECAP RESOURCES': 'WCP.TO',
    'AIR CANADA': 'AC.TO',
    'VEREN INC': 'WCP.TO' # Veren became Whitecap
}

def extract_td_symbol(desc):
    desc_upper = str(desc).upper()
    for k, v in TD_SYMBOL_MAP.items():
        if k in desc_upper: return v
    return "" # Return empty if no match found

# Known Canadian Tickers (often missing .TO in broker exports)
CANADIAN_TICKERS = {
    'VDY', 'XEI', 'XEF', 'XEC', 'XIU', 'CM', 'TD', 'WCP', 
    'CASH', 'DLR', 'XRE', 'VCN', 'VEE', 'VIU', 'VUN', 'VAV'
}

def clean_symbol(symbol, source, description=""):
    """Normalize symbols (e.g. DLR.TO vs DLR)"""
    s = str(symbol).strip().upper()
    
    # Try to extract from description if symbol is missing or generic
    if (not s or s == 'NAN' or len(s) > 10) and description:
        s = extract_td_symbol(description)

    # Remove extra spaces and common broker suffixes
    s = re.sub(r'\s+UNITS?$', '', s)
    s = re.sub(r'\s+ETF$', '', s)
    s = re.sub(r'\.TO$', '', s) 
    
    # If the symbol is in our known Canadian list, add .TO
    if s in CANADIAN_TICKERS:
        return s + ".TO"
    
    # Heuristic: if source says 'CDN' or market is Canadian
    # (CIBC has a 'Market' column we could use)
    
    return s

def load_all_transactions(directory):
    all_txs = []
    
    # Recursive search if transactions are in subfolders
    files = glob.glob(os.path.join(directory, "**/*.csv"), recursive=True)
    for f in files:
        filename = os.path.basename(f)
        try:
            if "CIBC" in filename:
                txs = parse_cibc(f)
            elif "RBC" in filename:
                txs = parse_rbc(f)
            elif "TD" in filename:
                txs = parse_td(f)
            else:
                continue
            all_txs.append(txs)
        except Exception as e:
            print(f"Error parsing {filename}: {e}")
            
    if not all_txs:
        return pd.DataFrame()
        
    df = pd.concat(all_txs, ignore_index=True)
    
    # Clean symbols once with description
    df['Symbol'] = df.apply(lambda row: clean_symbol(row['Symbol'], row['Source'], row.get('Description', '')), axis=1)
    
    # Define a robust sorting order:
    # 1. Merger Surrenders (SELL) - must be first to capture cost basis for carryover
    # 2. All BUYS (including Merger Receipts) - next to ensure lots exist for same-day sells
    # 3. Standard SELLS - last to consume lots
    def get_action_rank(row):
        desc = str(row.get('Description', '')).upper()
        is_merger = 'MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc
        action = row['Action']
        
        if action == 'SELL' and is_merger and 'SURRENDERED' in desc:
            return 0 # Merger Surrender
        if action == 'BUY':
            return 1 # All Buys (including merger receipts)
        if action == 'SELL':
            return 2 # Standard Sells
        if action == 'DIV':
            return 3
        return 99

    df['Action_Rank'] = df.apply(get_action_rank, axis=1)
    df = df.sort_values(['Date', 'Action_Rank'])
    
    # Filter out empty symbols
    df = df[df['Symbol'].str.strip() != ""]
    
    return df.drop(columns=['Action_Rank'])

def calculate_holdings(df_tx):
    """
    Calculates current holdings and realized PnL from transactions.
    Using FIFO for Tax Lots to be more accurate for CAGR.
    """
    # symbol -> list of [date, qty, price, comm_per_share, currency]
    lots = {} 
    realized_pnl = {} # symbol -> { 'CAD': 0, 'USD': 0 }
    merger_basis_carryover = {} # {Symbol: cost}

    # Group by symbol and process sorted transactions
    for _, tx in df_tx.iterrows():
        sym = tx['Symbol']
        action = tx['Action']
        qty = tx['Quantity']
        price = tx['Price']
        comm = tx['Commission']
        curr = tx['Currency']
        
        if action == 'BUY':
            if sym not in lots: lots[sym] = []
            desc = str(tx.get('Description', '')).upper()
            
            # Calculate cost basis from Amount if possible (CIBC buys are negative amounts)
            cost = abs(tx['Amount']) if tx['Amount'] != 0 and not pd.isna(tx['Amount']) else (qty * price + comm)
            
            # SPECIAL CASE: Merger receipt
            if 'RECEIVED' in desc and ('MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc):
                if sym in merger_basis_carryover:
                    cost += merger_basis_carryover.pop(sym)
                elif 'WCP' in sym and 'WCP' in merger_basis_carryover:
                    # Specific hack for WCP/VEREN if needed, but the mapping should handle it
                    cost += merger_basis_carryover.pop('WCP')

            lots[sym].append({
                'Trade Date': tx['Date'],
                'Quantity': qty,
                'Cost': cost,
                'Purchase Price': cost / qty if qty > 0 else price,
                'Commission': comm,
                'Currency': curr,
                'Description': desc
            })
        elif action == 'SELL':
            if sym in lots:
                remaining_sell_qty = qty
                if sym not in realized_pnl: realized_pnl[sym] = {}
                
                # Proceeds from Amount if possible
                total_proceeds = tx['Amount'] if tx['Amount'] != 0 and not pd.isna(tx['Amount']) else (qty * price - comm)
                
                desc = str(tx.get('Description', '')).upper()
                is_merger_surrender = 'SURRENDERED' in desc and ('MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc)
                
                while remaining_sell_qty > 0 and lots[sym]:
                    lot = lots[sym][0]
                    if lot['Quantity'] <= remaining_sell_qty:
                        # Full lot sold
                        sold_qty = lot['Quantity']
                        cost_basis = lot['Cost']
                        share_of_proceeds = total_proceeds * (sold_qty / qty)
                        
                        if is_merger_surrender:
                            if sym not in merger_basis_carryover: merger_basis_carryover[sym] = 0.0
                            merger_basis_carryover[sym] += cost_basis
                        else:
                            if curr not in realized_pnl[sym]: realized_pnl[sym][curr] = 0.0
                            realized_pnl[sym][curr] += (share_of_proceeds - cost_basis)
                        
                        remaining_sell_qty -= sold_qty
                        lots[sym].pop(0)
                    else:
                        # Partial lot sold
                        sold_qty = remaining_sell_qty
                        cost_basis = lot['Cost'] * (sold_qty / lot['Quantity'])
                        share_of_proceeds = total_proceeds * (sold_qty / qty)
                        
                        if is_merger_surrender:
                            if sym not in merger_basis_carryover: merger_basis_carryover[sym] = 0.0
                            merger_basis_carryover[sym] += cost_basis
                        else:
                            if curr not in realized_pnl[sym]: realized_pnl[sym][curr] = 0.0
                            realized_pnl[sym][curr] += (share_of_proceeds - cost_basis)
                        
                        lot['Quantity'] -= sold_qty
                        lot['Cost'] -= cost_basis
                        remaining_sell_qty = 0
            else:
                # Sold without history
                pass

    rows = []
    for sym, symbol_lots in lots.items():
        valid_lots = [lot for lot in symbol_lots if lot['Quantity'] > 0.0001]
        if not valid_lots:
            continue
            
        total_quantity = sum(lot['Quantity'] for lot in valid_lots)
        total_cost = sum(lot['Cost'] for lot in valid_lots)
        total_comm = sum(lot['Commission'] for lot in valid_lots)
        
        # Find latest valid trade date
        dates = pd.to_datetime([l['Trade Date'] for l in valid_lots], errors='coerce').dropna()
        latest_date = dates.max() if not dates.empty else None
        
        rows.append({
            'Symbol': sym,
            'Quantity': total_quantity,
            'Purchase Price': total_cost / total_quantity if total_quantity > 0 else 0,
            'Trade Date': latest_date,
            'Commission': total_comm,
            'Currency': valid_lots[0]['Currency']
        })
    return pd.DataFrame(rows), realized_pnl

def prepare_portfolio_df(holdings_df):
    """
    Converts the internal holdings format to the one expected by main.py
    """
    # Rename columns to match portfolio.csv
    # Symbol,Trade Date,Purchase Price,Quantity,Commission,Comment
    df = holdings_df.copy()
    df['Comment'] = 'Imported from History'
    # Current main.py expects df to have certain columns which usually come from CSV
    return df

if __name__ == "__main__":
    tx_dir = "/Users/mingli/PycharmProjects/holding-analyzer/transactions"
    df_tx = load_all_transactions(tx_dir)
    print("Transactions Loaded:")
    print(df_tx.head())
    
    holdings = calculate_holdings(df_tx)
    print("\nCalculated Holdings:")
    print(holdings)
