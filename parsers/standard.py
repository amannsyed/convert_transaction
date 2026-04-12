from .base import BaseParser
import pandas as pd
from typing import List, Dict
import logging
import math

logger = logging.getLogger(__name__)

class StandardParser(BaseParser):
    @classmethod
    def can_handle(cls, columns: List[str]) -> bool:
        lower_cols = cls._normalize_columns(columns)
        required = ["date", "type", "category", "amount", "bank", "merchant", "note"]
        return all(c in lower_cols for c in required)

    @classmethod
    def parse(cls, df: pd.DataFrame) -> List[Dict]:
        logger.debug(f"StandardParser pass-through parsing {len(df)} rows.")
        records = df.to_dict('records')
        
        cleaned_records = []
        for r in records:
            cleaned = {}
            for k, v in r.items():
                # Convert pandas nan to None
                if isinstance(v, float) and math.isnan(v):
                    cleaned[k] = None
                else:
                    cleaned[k] = v
            cleaned_records.append(cleaned)
            
        return cleaned_records
