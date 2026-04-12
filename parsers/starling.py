from .base import BaseParser
import pandas as pd
from typing import List, Dict
import math
import logging

logger = logging.getLogger(__name__)

class StarlingParser(BaseParser):
    @classmethod
    def can_handle(cls, columns: List[str]) -> bool:
        lower_cols = cls._normalize_columns(columns)
        return "counter party" in lower_cols and "spending category" in lower_cols

    @classmethod
    def parse(cls, df: pd.DataFrame) -> List[Dict]:
        logger.debug(f"StarlingParser instructed to parse {len(df)} rows.")
        records = []
        # Find the correct amount column which might be "Amount (GBP)" etc.
        amount_col = "Amount"
        for col in df.columns:
            if "amount" in str(col).lower():
                amount_col = col
                break
                
        for index, row in df.iterrows():
            try:
                amt = cls._parse_amount(row.get(amount_col, 0))
            except Exception as e:
                logger.warning(f"StarlingParser issue casting amount at row {index}: {e}")
                amt = 0.0
            if math.isnan(amt): amt = 0.0
            
            # Starling 'Sent from Revolut' is 4 (positive) means income
            t = "income" if amt > 0 else "expense"
            
            records.append({
                "Date": cls._parse_date(row.get("Date"), ["%d/%m/%Y", "%Y-%m-%d"]),
                "Type": t,
                "Category": row.get("Spending Category") if pd.notna(row.get("Spending Category")) else None,
                "Amount": round(abs(amt), 2),
                "Bank": "Starling",
                "Merchant": row.get("Counter Party") if pd.notna(row.get("Counter Party")) else None,
                "Note": row.get("Reference") if pd.notna(row.get("Reference")) else row.get("Notes")
            })
        return records
