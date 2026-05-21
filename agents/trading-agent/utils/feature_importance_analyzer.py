import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.ensemble import RandomForestRegressor
from typing import Any, Dict, List

class FeatureImportanceAnalyzer:
    """
    Analyzes feature importance for trading ML models to improve interpretability.
    Supports both model-native importance and permutation importance for agnostic analysis.
    """
    def __init__(self, model: Any):
        self.model = model

    def analyze(self, X: pd.DataFrame, y: pd.Series, metric: str = 'r2') -> Dict[str, Any]:
        """
        Performs feature importance analysis.
        """
        # 1. Model-native importance (if available)
        native_importance = None
        if hasattr(self.model, 'feature_importances_'):
            native_importance = dict(zip(X.columns, self.model.feature_importances_))
        
        # 2. Permutation Importance (Model Agnostic)
        # We use a subset of X to speed up analysis if it's too large
        result = permutation_importance(
            self.model, X, y, n_repeats=10, random_state=42, scoring=metric
        )
        perm_importance = dict(zip(X.columns, result.importances_mean))
        
        return {
            "native_importance": native_importance,
            "permutation_importance": perm_importance,
            "top_features": sorted(perm_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        }

if __name__ == "__main__":
    # Mock data
    X = pd.DataFrame(np.random.rand(100, 5), columns=['RSI', 'MACD', 'EMA_20', 'Vol_ZScore', 'Sentiment'])
    y = np.random.rand(100)
    
    model = RandomForestRegressor().fit(X, y)
    analyzer = FeatureImportanceAnalyzer(model)
    report = analyzer.analyze(X, y)
    
    print("Top Features by Permutation Importance:")
    for feat, imp in report['top_features']:
        print(f"{feat}: {imp:.4f}")
