from .base import BaseParser
import pandas as pd
from typing import List, Dict
import math
import logging

logger = logging.getLogger(__name__)

class RevolutParser(BaseParser):
    @classmethod
    def can_handle(cls, columns: List[str]) -> bool:
        lower_cols = cls._normalize_columns(columns)
        return "started date" in lower_cols and "completed date" in lower_cols and "fee" in lower_cols

    @classmethod
    def parse(cls, df: pd.DataFrame) -> List[Dict]:
        logger.debug(f"RevolutParser instructed to parse {len(df)} rows.")
        records = []
        for index, row in df.iterrows():
            try:
                amt = cls._parse_amount(row.get("Amount", 0))
            except Exception as e:
                logger.warning(f"RevolutParser issue casting amount at row {index}: {e}")
                amt = 0.0
            if math.isnan(amt): amt = 0.0
            
            # Revolut topup (income) is positive, expenses are negative
            t = "income" if amt > 0 else "expense"
            
            # Grab date from 'Started Date'
            dt_raw = row.get("Started Date")
            if pd.isna(dt_raw):
                dt_raw = row.get("Completed Date")
                
            # Usually format is YYYY-MM-DD HH:MM:SS
            dt = cls._parse_date(dt_raw, ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"])
            
            records.append({
                "Date": dt,
                "Type": t,
                "Category": None,
                "Amount": round(abs(amt), 2),
                "Bank": "Revolut",
                "Merchant": row.get("Description") if pd.notna(row.get("Description")) else None,
                "Note": row.get("Product") if pd.notna(row.get("Product")) else None
            })
        return records
