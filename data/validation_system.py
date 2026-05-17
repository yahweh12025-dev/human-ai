import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataValidationSystem:
    """
    Checks for data quality, completeness, and consistency across sources.
    Prevents 'garbage in, garbage out' in trading ML models.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "max_gap_seconds": 60,
            "max_outlier_zscore": 5.0
        }

    def validate_completeness(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Checks for missing values or unexpected gaps in time-series data."""
        null_counts = df.isnull().sum()
        missing = null_counts[null_counts > 0].index.tolist()
        
        if missing:
            return False, [f"Column {col} has missing values" for col in missing]
        return True, []

    def validate_consistency(self, df: pd.DataFrame, col: str) -> Tuple[bool, List[str]]:
        """Checks for unrealistic price spikes or negative prices."""
        if (df[col] <= 0).any():
            return False, [f"Negative or zero prices found in {col}"]
        
        z_scores = (df[col] - df[col].mean()) / df[col].std()
        if (abs(z_scores) > self.config["max_outlier_zscore"]).any():
            return False, [f"Extreme outliers found in {col}"]
            
        return True, []

    def run_full_audit(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Performs a full validation suite on the dataset."""
        comp_ok, comp_errs = self.validate_completeness(df)
        cons_ok, cons_errs = self.validate_consistency(df, 'close')
        
        return {
            "is_valid": comp_ok and cons_ok,
            "errors": comp_errs + cons_errs
        }

if __name__ == "__main__":
    df = pd.DataFrame({"close": [100, 101, 100.5, 500, 100.2]}) # 500 is an outlier
    validator = DataValidationSystem()
    result = validator.run_full_audit(df)
    print(f"Validation Result: {result}")
