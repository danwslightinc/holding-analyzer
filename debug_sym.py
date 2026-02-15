import pandas as pd
from transaction_parser import clean_symbol, extract_td_symbol

print(f"Extract VEREN: {extract_td_symbol('VEREN INC COM NEW  COM NEW TD WATERHOUSE TFSA TRANSFER BOOK VALUE            6432.90')}")
print(f"Clean VEREN: {clean_symbol('', 'CIBC', 'VEREN INC COM NEW  COM NEW TD WATERHOUSE TFSA TRANSFER BOOK VALUE            6432.90')}")
