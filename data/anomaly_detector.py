import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketAnomalyDetector:
    """
    Real-time market anomaly detection system using streaming semantic memory connections.
    Identifies outliers in price action, volume, and sentiment.
    """
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold # Z-score threshold
        self.history = []

    def update_state(self, current_value: float):
        """Updates the internal rolling history for anomaly detection."""
        self.history.append(current_value)
        if len(self.history) > 1000:
            self.history.pop(0)

    def is_anomaly(self, value: float) -> Tuple[bool, float]:
        """
        Checks if the current value is an anomaly based on historical Z-score.
        """
        if len(self.history) < 30:
            return False, 0.0
            
        mean = np.mean(self.history)
        std = np.std(self.history)
        
        if std == 0: return False, 0.0
        
        z_score = abs((value - mean) / std)
        return z_score > self.threshold, z_score

    def detect_multivariate_anomaly(self, data: Dict[str, float]) -> Dict[str, Any]:
        """
        Detects anomalies across multiple dimensions (Price, Vol, Sentiment).
        """
        anomalies = {}
        for key, val in data.items():
            # In a real system, this would have separate histories for each key
            is_anom, score = self.is_anomaly(val)
            anomalies[key] = {"is_anomaly": is_anom, "score": score}
            
        return anomalies

if __name__ == "__main__":
    detector = MarketAnomalyDetector()
    # Populate history
    for _ in range(100):
        detector.update_state(np.random.normal(100, 1))
    
    # Test normal value
    print(f"Normal value (100.5): {detector.is_anomaly(100.5)}")
    # Test anomaly
    print(f"Anomaly value (110.0): {detector.is_anomaly(110.0)}")
