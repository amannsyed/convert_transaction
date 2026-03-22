import io
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import pandas as pd
from parsers import AmexParser, BankOfScotlandParser, RevolutParser, StarlingParser

csvs = {
    "Amex": """Date	Description	Amount	Extended Details	Appears On Your Statement As	Address	Town/City	Postcode	Country	Reference	Category
09/01/2026	CKO LONDON	3.89		CKO LONDON	420 KING STREET	LONDON	SW1Y 9XY	UNITED KINGDOM OF GB AND NI	AT26009008500001005XXX'	General Purchases-General Retail""",
    
    "Bank of Scotland": """Transaction Date	Transaction Type	Sort Code	Account Number	Transaction Description	Debit Amount	Credit Amount	Balance
02/03/2026	FPO	80-XX-XX	19XXXXXX	ABC XYZ	158.32		0""",

    "Revolut": """Type	Product	Started Date	Completed Date	Description	Amount	Fee	Currency	State	Balance
Topup	Current	2026-01-21 19:48:44	2026-01-21 19:49:10	ABCDE	200	0	GBP	COMPLETED	200""",

    "Starling": """Date	Counter Party	Reference	Type	Amount (GBP)	Balance (GBP)	Spending Category	Notes
01/01/2026	ABCDE	XYZ	FASTER PAYMENT	4	1826.46	INCOME	"""
}

PARSERS = [AmexParser, BankOfScotlandParser, RevolutParser, StarlingParser]

for name, content in csvs.items():
    print(f"\\n--- Testing {name} ---")
    df = pd.read_csv(io.StringIO(content), sep='\t')
    
    parser_found = None
    for parser in PARSERS:
        if parser.can_handle(df.columns.tolist()):
            parser_found = parser
            break
            
    if not parser_found:
        print(f"FAILED: No parser found for {name}")
        continue
        
    records = parser_found.parse(df)
    print(json.dumps(records, indent=2))
