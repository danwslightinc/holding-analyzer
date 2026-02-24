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
