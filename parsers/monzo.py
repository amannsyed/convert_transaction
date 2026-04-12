from .base import BaseParser
import pandas as pd
from typing import List, Dict
import math
import logging

logger = logging.getLogger(__name__)

class MonzoParser(BaseParser):
    @classmethod
    def can_handle(cls, columns: List[str]) -> bool:
        lower_cols = cls._normalize_columns(columns)
        return "transaction id" in lower_cols and "emoji" in lower_cols and "notes and #tags" in lower_cols

    @classmethod
    def parse(cls, df: pd.DataFrame) -> List[Dict]:
        logger.debug(f"MonzoParser instructed to parse {len(df)} rows.")
        records = []
        for index, row in df.iterrows():
            try:
                amt = cls._parse_amount(row.get("Amount", 0))
            except Exception as e:
                logger.warning(f"MonzoParser issue casting amount at row {index}: {e}")
                amt = 0.0
                
            if math.isnan(amt): amt = 0.0
            
            if amt >= 0:
                t = "income"
            else:
                t = "expense"
                
            merchant = row.get("Name")
            if pd.isna(merchant) or str(merchant).strip() == "":
                merchant = row.get("Description")
            if pd.isna(merchant):
                merchant = None
                
            note = row.get("Notes and #tags")
            if pd.isna(note):
                note = None
                
            category = row.get("Category")
            if pd.isna(category):
                category = None
                
            records.append({
                "Date": cls._parse_date(row.get("Date"), ["%d/%m/%Y", "%Y-%m-%d"]),
                "Type": t,
                "Category": category,
                "Amount": round(abs(amt), 2),
                "Bank": "Monzo",
                "Merchant": merchant,
                "Note": note
            })
        return records
