import io
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import pandas as pd
from parsers import AmexParser, BankOfScotlandParser, RevolutParser, StarlingParser, MonzoParser, MockParser, StandardParser

csvs = {
    "Amex": """Date\tDescription\tAmount\tExtended Details\tAppears On Your Statement As\tAddress\tTown/City\tPostcode\tCountry\tReference\tCategory
09/01/2026\tCKO LONDON\t3.89\t\tCKO LONDON\t420 KING STREET\tLONDON\tSW1Y 9XY\tUNITED KINGDOM OF GB AND NI\tAT26009008500001005XXX'\tGeneral Purchases-General Retail""",
    
    "Bank of Scotland": """Transaction Date\tTransaction Type\tSort Code\tAccount Number\tTransaction Description\tDebit Amount\tCredit Amount\tBalance
02/03/2026\tFPO\t80-XX-XX\t19XXXXXX\tABC XYZ\t158.32\t\t0""",

    "Revolut": """Type\tProduct\tStarted Date\tCompleted Date\tDescription\tAmount\tFee\tCurrency\tState\tBalance
Topup\tCurrent\t2026-01-21 19:48:44\t2026-01-21 19:49:10\tABCDE\t200\t0\tGBP\tCOMPLETED\t200""",

    "Starling": """Date\tCounter Party\tReference\tType\tAmount (GBP)\tBalance (GBP)\tSpending Category\tNotes
01/01/2026\tABCDE\tXYZ\tFASTER PAYMENT\t4\t1826.46\tINCOME\t""",

    "Monzo": """Transaction ID\tDate\tTime\tType\tName\tEmoji\tCategory\tAmount\tCurrency\tLocal amount\tLocal currency\tNotes and #tags\tAddress\tReceipt\tDescription\tCategory split\tMoney Out\tMoney In
tx_001\t01/02/2026\t12:00:00\tCard payment\tTesco\t🛒\tGroceries\t-15.50\tGBP\t-15.50\tGBP\tWeekly shop\t123 High St\t\tTESCO STORES\t\t15.50\t""",

    "Mock": """Account Number\tPosting Date\tTransaction Date\tDescription\tDebit\tCredit\tBalance
12345\t01/15/2026\t01/15/2026\tGrocery Store\t50.00\t\t1000.00""",

    "Standard": """Date\tType\tCategory\tAmount\tBank\tMerchant\tNote
2026-01-01\texpense\tGroceries\t25.00\tTestBank\tSupermarket\tWeekly shop"""
}

PARSER_MAP = {
    "Amex": AmexParser,
    "Bank of Scotland": BankOfScotlandParser,
    "Revolut": RevolutParser,
    "Starling": StarlingParser,
    "Monzo": MonzoParser,
    "Mock": MockParser,
    "Standard": StandardParser,
}

ALL_PARSERS = list(PARSER_MAP.values())

passed = 0
failed = 0

for name, content in csvs.items():
    print(f"\n--- Testing {name} ---")
    df = pd.read_csv(io.StringIO(content), sep='\t')
    
    expected_parser = PARSER_MAP[name]
    
    # Test can_handle returns True for the correct parser
    assert expected_parser.can_handle(df.columns.tolist()), \
        f"FAIL: {expected_parser.__name__}.can_handle() returned False for its own data"
    
    # Test auto-detection finds the right parser
    detected_parser = None
    for parser in ALL_PARSERS:
        if parser.can_handle(df.columns.tolist()):
            detected_parser = parser
            break
    
    assert detected_parser is not None, f"FAIL: No parser detected for {name}"
    assert detected_parser == expected_parser, \
        f"FAIL: Detected {detected_parser.__name__} instead of {expected_parser.__name__} for {name}"
    
    # Test parsing produces results
    records = expected_parser.parse(df)
    assert isinstance(records, list), f"FAIL: {name} parse() did not return a list"
    assert len(records) > 0, f"FAIL: {name} parse() returned empty results"
    
    # Test standard schema fields (Standard parser may pass through different casing)
    for record in records:
        assert "Date" in record, f"FAIL: {name} record missing 'Date'"
        assert "Amount" in record or "amount" in record, f"FAIL: {name} record missing 'Amount'"
        assert "Bank" in record or "bank" in record, f"FAIL: {name} record missing 'Bank'"
    
    print(f"  ✓ can_handle() correct")
    print(f"  ✓ Auto-detection matched: {detected_parser.__name__}")
    print(f"  ✓ Parsed {len(records)} record(s)")
    print(f"  Sample: {json.dumps(records[0], indent=2)}")
    passed += 1

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed out of {len(csvs)} tests")
assert failed == 0, f"{failed} test(s) failed!"
print("All tests passed! ✓")
