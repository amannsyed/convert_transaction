from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict

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
