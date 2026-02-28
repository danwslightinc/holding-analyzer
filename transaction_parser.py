import pandas as pd

def calculate_holdings(df_tx):
    """
    Calculates current holdings and realized PnL from transactions.
    Using FIFO for Tax Lots to be more accurate for CAGR.
    """
    if df_tx is None or df_tx.empty:
        return pd.DataFrame(), {}
        
    df_tx['Date'] = pd.to_datetime(df_tx['Date'])
    df_tx = df_tx.sort_values('Date')
        
    # (symbol, broker, account_type) -> list of lots
    lots = {} 
    realized_pnl = {} # (symbol, broker, account_type) -> { 'CAD': 0, 'USD': 0 }
    merger_basis_carryover = {} # {(Symbol, broker, account): cost}

    # Group by symbol and broker/account and process sorted transactions
    for _, tx in df_tx.iterrows():
        sym = tx['Symbol']
        broker = tx.get('Broker')
        account = tx.get('Account_Type')
        key = (sym, broker, account)
        
        action = tx['Action']
        qty = tx['Quantity']
        price = tx['Price']
        comm = tx['Commission']
        curr = tx['Currency']
        
        if action == 'BUY':
            if key not in lots: lots[key] = []
            desc = str(tx.get('Description', '')).upper()
            
            # Calculate cost basis from Amount if possible
            cost = abs(tx['Amount']) if tx['Amount'] != 0 and not pd.isna(tx['Amount']) else (qty * price + comm)
            
            # SPECIAL CASE: Merger receipt
            if 'RECEIVED' in desc and ('MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc):
                if key in merger_basis_carryover:
                    cost += merger_basis_carryover.pop(key)
                elif (sym, broker, account) in merger_basis_carryover:
                    cost += merger_basis_carryover.pop((sym, broker, account))

            lots[key].append({
                'Trade Date': tx['Date'],
                'Quantity': qty,
                'Cost': cost,
                'Purchase Price': cost / qty if qty > 0 else price,
                'Commission': comm,
                'Currency': curr,
                'Description': desc,
                'Broker': broker,
                'Account_Type': account
            })
        elif action == 'SELL':
            if key in lots:
                remaining_sell_qty = qty
                if key not in realized_pnl: realized_pnl[key] = {}
                
                # Proceeds from Amount if possible
                total_proceeds = tx['Amount'] if tx['Amount'] != 0 and not pd.isna(tx['Amount']) else (qty * price - comm)
                
                desc = str(tx.get('Description', '')).upper()
                is_merger_surrender = 'SURRENDERED' in desc and ('MERGER' in desc or 'ADJUSTMENT' in desc or 'REORG' in desc)
                
                while remaining_sell_qty > 0 and lots[key]:
                    lot = lots[key][0]
                    if lot['Quantity'] <= remaining_sell_qty:
                        # Full lot sold
                        sold_qty = lot['Quantity']
                        cost_basis = lot['Cost']
                        share_of_proceeds = total_proceeds * (sold_qty / qty)
                        
                        if is_merger_surrender:
                            if key not in merger_basis_carryover: merger_basis_carryover[key] = 0.0
                            merger_basis_carryover[key] += cost_basis
                        else:
                            if curr not in realized_pnl[key]: realized_pnl[key][curr] = 0.0
                            realized_pnl[key][curr] += (share_of_proceeds - cost_basis)
                        
                        remaining_sell_qty -= sold_qty
                        lots[key].pop(0)
                    else:
                        # Partial lot sold
                        sold_qty = remaining_sell_qty
                        cost_basis = lot['Cost'] * (sold_qty / lot['Quantity'])
                        share_of_proceeds = total_proceeds * (sold_qty / qty)
                        
                        if is_merger_surrender:
                            if key not in merger_basis_carryover: merger_basis_carryover[key] = 0.0
                            merger_basis_carryover[key] += cost_basis
                        else:
                            if curr not in realized_pnl[key]: realized_pnl[key][curr] = 0.0
                            realized_pnl[key][curr] += (share_of_proceeds - cost_basis)
                        
                        lot['Quantity'] -= sold_qty
                        lot['Cost'] -= cost_basis
                        remaining_sell_qty = 0
            else:
                # Sold without history
                pass

    rows = []
    for key, symbol_lots in lots.items():
        sym, broker, account = key
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
            'Broker': broker,
            'Account_Type': account,
            'Quantity': total_quantity,
            'Purchase Price': total_cost / total_quantity if total_quantity > 0 else 0,
            'Trade Date': latest_date,
            'Commission': total_comm,
            'Currency': valid_lots[0]['Currency']
        })
    df_out = pd.DataFrame(rows)
    if df_out.empty:
        df_out = pd.DataFrame(columns=['Symbol', 'Broker', 'Account_Type', 'Quantity', 'Purchase Price', 'Trade Date', 'Commission', 'Currency'])
    return df_out, realized_pnl

def clean_symbol(symbol, broker=None, description=""):
    """Clean symbol strings from various broker formats."""
    if not isinstance(symbol, str):
        if pd.isna(symbol): return ""
        symbol = str(symbol)
    
    s = symbol.strip().upper()
    
    # Handle CIBC specific symbol padding or formats
    if broker == "CIBC":
        # CIBC symbols sometimes have trailing spaces or are part of a longer string
        s = s.split(':')[0].strip()
        
    # Handle crypto
    if "BITCOIN" in description.upper() or "BTC" in s:
        if "BTC" in s: return "BTC-USD"
        return "BTC-USD"
    if "ETHEREUM" in description.upper() or "ETH" in s:
        return "ETH-USD"

    # Remove currency suffixes if they are separated by space
    s = s.split(' ')[0]
    
    # Common CAD stocks might not have .TO in some files but are Canadian
    # If we are in a CAD account and it's a known Cdn symbol, we might add .TO
    # But for now, we'll stick to what's in the file or Description
    if "CDN" in description.upper() and not s.endswith(".TO") and "." not in s:
        # Avoid adding .TO to US stocks traded in CAD (rare but possible)
        # Usually if it says CDN and no period, it's TSX
        pass 

    return s

def parse_cibc(filepath):
    """Parse CIBC Investors Edge transaction history CSV."""
    # Find the header row (starts with "Transaction Date")
    with open(filepath, 'r') as f:
        lines = f.readlines()
    header_idx = -1
    for i, line in enumerate(lines):
        if "Transaction Date" in line:
            header_idx = i
            break
            
    if header_idx == -1: return pd.DataFrame() # No data found
    
    df = pd.read_csv(filepath, skiprows=header_idx, on_bad_lines='skip')
    df.columns = [c.strip() for c in df.columns]
    
    # Map columns
    col_map = {
        'Transaction Date': 'Date',
        'Transaction Type': 'Action',
        'Symbol': 'Symbol',
        'Quantity': 'Quantity',
        'Price': 'Price',
        'Commission': 'Commission',
        'Amount': 'Amount',
        'Currency of Amount': 'Currency',
        'Description': 'Description'
    }
    df = df.rename(columns=col_map)
    
    # If symbol is NaN, try to extract it from description (sometimes happens for some brokers)
    if 'Symbol' in df.columns:
        df = df[df['Symbol'].notna() | df['Description'].notna()]
    
    # Normalize actions
    action_map = {
        'Buy': 'BUY',
        'Sell': 'SELL',
        'Dividend': 'DIV',
        'Reinvest': 'BUY',  # DRIP
        'Interest': 'INT',
        'Transfer In': 'BUY',
        'Transf In': 'BUY',
        'Merger': 'BUY'
    }
    df['Action'] = df['Action'].map(lambda x: action_map.get(str(x).strip(), str(x).upper()))
    
    # Clean up numbers
    for col in ['Quantity', 'Price', 'Commission', 'Amount']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('(', '').str.replace(')', '').str.replace('$', '').str.replace('"', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df.dropna(subset=['Date'])

def parse_rbc(filepath):
    """Parse RBC Direct Investing activity export CSV."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    header_idx = -1
    for i, line in enumerate(lines):
        if "Date" in line and "Activity" in line:
            header_idx = i
            break
    if header_idx == -1: return pd.DataFrame()
    
    df = pd.read_csv(filepath, skiprows=header_idx, on_bad_lines='skip')
    df.columns = [c.strip() for c in df.columns]
    
    col_map = {
        'Date': 'Date',
        'Activity': 'Action',
        'Symbol': 'Symbol',
        'Quantity': 'Quantity',
        'Price': 'Price',
        'Value': 'Amount',
        'Currency': 'Currency',
        'Description': 'Description'
    }
    df = df.rename(columns=col_map)
    
    action_map = {
        'Buy': 'BUY',
        'Sell': 'SELL',
        'Dividends': 'DIV',
        'Interest': 'INT',
        'Distribution': 'DIV',
        'Reinvestment': 'BUY'
    }
    df['Action'] = df['Action'].map(lambda x: action_map.get(str(x).strip(), str(x).upper()))
    
    for col in ['Quantity', 'Price', 'Amount']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('(', '').str.replace(')', '').str.replace('$', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    df['Commission'] = 0.0
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df.dropna(subset=['Date'])

def parse_td(filepath):
    """Parse TD Direct Investing activity CSV."""
    with open(filepath, 'r', encoding='latin-1') as f:
        lines = f.readlines()
    header_idx = -1
    for i, line in enumerate(lines):
        if "Trade Date" in line and "Action" in line:
            header_idx = i
            break
    if header_idx == -1: return pd.DataFrame()
    
    df = pd.read_csv(filepath, skiprows=header_idx, encoding='latin-1', on_bad_lines='skip')
    df.columns = [c.strip() for c in df.columns]
    
    col_map = {
        'Trade Date': 'Date',
        'Action': 'Action',
        'Symbol': 'Symbol',
        'Quantity': 'Quantity',
        'Price': 'Price',
        'Commission': 'Commission',
        'Net Amount': 'Amount',
        'Currency': 'Currency',
        'Description': 'Description'
    }
    df = df.rename(columns=col_map)
    
    # TD sometimes misses Symbol column in activity - extract from description
    if 'Symbol' not in df.columns:
        # Simple heuristic: first word of description usually not a ticker if it's "ISHR S&P..."
        # But we can try to find tickers in parentheses or capitals.
        def extract_td_sym(desc):
            desc = str(desc).strip()
            # If "ISHR S&PTSX CMP HI DV ETF", map it to "XEI.TO" maybe?
            # Or if it has a ticker in the description like "(XIU)", use it.
            if "(" in desc and ")" in desc:
                return desc.split("(")[1].split(")")[0]
            # If it's a known ETF name, handle it?
            # For now, we'll try to find a capitalized word that looks like a symbol
            words = desc.split(' ')
            for w in words:
                if w.isupper() and 1 <= len(w) <= 6: return w
            return desc.split(' ')[0] # Default to first word
        df['Symbol'] = df['Description'].apply(extract_td_sym)
    
    action_map = {
        'BUY': 'BUY',
        'SELL': 'SELL',
        'TXPDDV': 'DIV',
        'DIV': 'DIV',
        'TFR-IN': 'BUY',
        'CONT': 'ADD'
    }
    df['Action'] = df['Action'].map(lambda x: action_map.get(str(x).strip().upper(), str(x).upper()))
    
    for col in ['Quantity', 'Price', 'Commission', 'Amount']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('(', '').str.replace(')', '').str.replace('$', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df.dropna(subset=['Date', 'Symbol'])
