from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict
import math

class BaseParser(ABC):
    @classmethod
    @abstractmethod
    def can_handle(cls, columns: List[str]) -> bool:
        """Return True if the parser can handle these columns"""
        pass
        
    @classmethod
    @abstractmethod
    def parse(cls, df: pd.DataFrame) -> List[Dict]:
        """Parse DataFrame into standard format records"""
        pass
        
    @staticmethod
    def _parse_date(date_str, formats=None):
        if pd.isnull(date_str) or not str(date_str).strip():
            return None
        
        if formats:
            for fmt in formats:
                try:
                    return pd.to_datetime(date_str, format=fmt).strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    continue
        
        # Fallback to generic parsing
        try:
            return pd.to_datetime(date_str).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_amount(value) -> float:
        if pd.isnull(value):
            return 0.0

        if isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                return 0.0
            return float(value)

        text = str(value).strip()
        if not text:
            return 0.0

        negative = False
        if text.startswith("(") and text.endswith(")"):
            negative = True
            text = text[1:-1]

        cleaned = (
            text.replace(",", "")
            .replace("£", "")
            .replace("$", "")
            .replace("€", "")
            .strip()
        )

        if cleaned.endswith("-"):
            negative = True
            cleaned = cleaned[:-1].strip()

        amount = float(cleaned)
        return -amount if negative else amount

    @staticmethod
    def _normalize_columns(columns: List[str]) -> List[str]:
        return [str(c).lower().strip().replace('\ufeff', '') for c in columns]
