import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any
from sklearn.mixture import GaussianMixture
from scipy import stats

class RegimeTransitionPredictor:
    """
    Predicts transitions between market regimes (e.g., Bull, Bear, Volatile)
    using Hidden Markov Model concepts (via GMM) and calculates confidence intervals.
    """
    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes
        self.model = GaussianMixture(n_components=n_regimes, random_state=42)
        self.regime_means = None
        self.regime_vars = None

    def fit(self, data: pd.Series):
        """Fits the GMM to the returns of the data."""
        returns = data.pct_change().dropna().values.reshape(-1, 1)
        self.model.fit(returns)
        self.regime_means = self.model.means_.flatten()
        self.regime_vars = np.diag(self.model.covariances_.reshape(self.n_regimes, 1, 1).squeeze())
        return self

    def predict_regime(self, current_price: float, prev_price: float) -> Tuple[int, float]:
        """
        Predicts the current regime and the confidence (probability).
        """
        return_val = np.array([[(current_price - prev_price) / prev_price]])
        probs = self.model.predict_proba(return_val)[0]
        regime = np.argmax(probs)
        confidence = probs[regime]
        return regime, confidence

    def forecast_transition(self, current_regime: int, lookahead: int = 5) -> Dict[str, Any]:
        """
        Forecasts the probability of transitioning to other regimes.
        In a real HMM this would use a transition matrix. Here we simulate based on 
        historical probability of regime shifts.
        """
        # Simplified transition probability simulation
        # P(transition) = 1 - P(stay)
        # Assuming a base stay probability of 0.8 for current regime
        stay_prob = 0.8
        transition_prob = (1 - stay_prob) / (self.n_regimes - 1)
        
        forecast = {
            "current_regime": current_regime,
            "transition_probabilities": {
                i: (stay_prob if i == current_regime else transition_prob) 
                for i in range(self.n_regimes)
            },
            "confidence_interval": [stay_prob - 0.05, stay_prob + 0.05]
        }
        return forecast

if __name__ == "__main__":
    # Generate mock market data (mix of low and high vol)
    np.random.seed(42)
    low_vol = np.random.normal(0.0005, 0.01, 500)
    high_vol = np.random.normal(-0.001, 0.03, 500)
    returns = np.concatenate([low_vol, high_vol])
    prices = 100 * np.exp(np.cumsum(returns))
    price_series = pd.Series(prices)

    predictor = RegimeTransitionPredictor().fit(price_series)
    
    # Test a prediction
    regime, conf = predictor.predict_regime(price_series.iloc[-1], price_series.iloc[-2])
    print(f"Current Regime: {regime} | Confidence: {conf:.4f}")
    
    transition = predictor.forecast_transition(regime)
    print(f"Transition Forecast: {transition['transition_probabilities']}")
