from .base import BaseParser
import pandas as pd
from typing import List, Dict
import math
import logging

logger = logging.getLogger(__name__)

class AmexParser(BaseParser):
    @classmethod
    def can_handle(cls, columns: List[str]) -> bool:
        lower_cols = [str(c).lower().strip() for c in columns]
        is_full = "extended details" in lower_cols and "appears on your statement as" in lower_cols
        is_simple = lower_cols == ["date", "description", "amount"]
        return is_full or is_simple

    @classmethod
    def parse(cls, df: pd.DataFrame) -> List[Dict]:
        logger.debug(f"AmexParser instructed to parse {len(df)} rows.")
        records = []
        for index, row in df.iterrows():
            # Handle numeric conversion safely
            try:
                amt = float(row.get("Amount", 0))
            except Exception as e:
                logger.warning(f"AmexParser issue casting amount at row {index}: {e}")
                amt = 0.0
                
            if pd.isna(amt) or math.isnan(amt):
                amt = 0.0

            # Assuming positive means expense from user's snippet where amount is 3.89 for a purchase
            t = "expense" if amt > 0 else "income"
            
            records.append({
                "Date": cls._parse_date(row.get("Date"), ["%d/%m/%Y", "%Y-%m-%d"]),
                "Type": t,
                "Category": row.get("Category") if pd.notna(row.get("Category")) else None,
                "Amount": round(abs(amt), 2),
                "Bank": "Amex",
                "Merchant": row.get("Description") if pd.notna(row.get("Description")) else None,
                "Note": row.get("Reference") if pd.notna(row.get("Reference")) else None
            })
        return records
