import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import learning_curve
from typing import Any, Dict

class OverfittingDetector:
    """
    Detects overfitting in ML models by analyzing training vs validation curves.
    """
    def __init__(self, model: Any):
        self.model = model

    def analyze_curves(self, X, y, cv=5):
        """
        Computes learning curves and identifies gaps that signify overfitting.
        """
        train_sizes, train_scores, test_scores = learning_curve(
            self.model, X, y, cv=cv, scoring='r2', 
            train_sizes=np.linspace(0.1, 1.0, 5)
        )
        
        train_mean = np.mean(train_scores, axis=1)
        test_mean = np.mean(test_scores, axis=1)
        gap = train_mean - test_mean
        
        is_overfitting = gap[-1] > 0.15 # Threshold for significant overfitting
        
        return {
            "is_overfitting": is_overfitting,
            "final_gap": gap[-1],
            "train_scores": train_mean,
            "test_scores": test_mean
        }

if __name__ == "__main__":
    from sklearn.ensemble import RandomForestRegressor
    X = np.random.rand(100, 10)
    y = np.random.rand(100)
    
    # Overfit the model by using too many estimators/depth
    model = RandomForestRegressor(max_depth=20, n_estimators=100)
    detector = OverfittingDetector(model)
    result = detector.analyze_curves(X, y)
    
    print(f"Overfitting detected: {result['is_overfitting']} (Gap: {result['final_gap']:.4f})")
