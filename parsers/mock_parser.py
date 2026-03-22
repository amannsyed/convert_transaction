from .base import BaseParser
import pandas as pd
from typing import List, Dict
import math
import logging

logger = logging.getLogger(__name__)

class MockParser(BaseParser):
    @classmethod
    def can_handle(cls, columns: List[str]) -> bool:
        lower_cols = [str(c).lower().strip() for c in columns]
        return "posting date" in lower_cols and "debit" in lower_cols and "credit" in lower_cols

    @classmethod
    def parse(cls, df: pd.DataFrame) -> List[Dict]:
        logger.debug(f"MockParser instructed to parse {len(df)} rows.")
        records = []
        for index, row in df.iterrows():
            debit = row.get("Debit")
            credit = row.get("Credit")
            
            try:
                debit_val = float(debit) if pd.notnull(debit) else 0.0
            except Exception as e:
                logger.warning(f"MockParser issue casting debit at row {index}: {e}")
                debit_val = 0.0
                
            try:
                credit_val = float(credit) if pd.notnull(credit) else 0.0
            except Exception as e:
                logger.warning(f"MockParser issue casting credit at row {index}: {e}")
                credit_val = 0.0
                
            if math.isnan(debit_val): debit_val = 0.0
            if math.isnan(credit_val): credit_val = 0.0
                
            if credit_val > 0:
                t = "income"
                amt = credit_val
            else:
                t = "expense"
                amt = debit_val
                
            records.append({
                "Date": cls._parse_date(row.get("Transaction Date"), ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"]),
                "Type": t,
                "Category": None,
                "Amount": round(abs(amt), 2),
                "Bank": "Mock",
                "Merchant": row.get("Description") if pd.notna(row.get("Description")) else None,
                "Note": None
            })
        return records
