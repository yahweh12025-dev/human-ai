# Advanced Pattern Recognition Engine for Trading Signals using Machine Learning
# This module implements machine learning models to recognize patterns in trading data.

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

class PatternRecognitionEngine:
    def __init__(self, model_path='models/pattern_recognition_model.pkl'):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        
    def prepare_features(self, data):
        """
        Prepare features for pattern recognition.
        This is a simplified example. In practice, you would use technical indicators,
        price action patterns, etc.
        """
        # Example features: moving averages, RSI, MACD, etc.
        df = data.copy()
        
        # Moving averages
        df['MA_10'] = df['close'].rolling(window=10).mean()
        df['MA_50'] = df['close'].rolling(window=50).mean()
        
        # Relative Strength Index (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # Drop rows with NaN values
        df = df.dropna()
        
        # Define feature columns
        self.feature_columns = ['MA_10', 'MA_50', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist']
        
        return df[self.feature_columns]
    
    def train_model(self, data, labels):
        """
        Train the pattern recognition model.
        
        Args:
            data (DataFrame): Features for training
            labels (Series): Target labels (e.g., 1 for buy signal, 0 for no signal, -1 for sell signal)
        """
        # Prepare features
        X = self.prepare_features(data)
        y = labels
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale the features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train the model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate the model
        y_pred = self.model.predict(X_test_scaled)
        print("Model Evaluation:")
        print(classification_report(y_test, y_pred))
        
        # Save the model and scaler
        self.save_model()
        
    def predict(self, data):
        """
        Predict trading signals based on pattern recognition.
        
        Args:
            data (DataFrame): Market data
            
        Returns:
            array: Predicted signals (1 for buy, 0 for hold, -1 for sell)
        """
        if self.model is None:
            raise ValueError("Model has not been trained yet. Call train_model first.")
        
        # Prepare features
        X = self.prepare_features(data)
        
        # Scale the features
        X_scaled = self.scaler.transform(X)
        
        # Make predictions
        predictions = self.model.predict(X_scaled)
        
        return predictions
    
    def save_model(self):
        """Save the trained model and scaler to disk."""
        if self.model is not None:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.model_path.replace('.pkl', '_scaler.pkl'))
            print(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load the trained model and scaler from disk."""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.model_path.replace('.pkl', '_scaler.pkl'))
            print(f"Model loaded from {self.model_path}")
        else:
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

# Example usage
if __name__ == "__main__":
    # This is just an example. In practice, you would load your market data.
    print("Pattern Recognition Engine for Trading Signals")
    print("This module is ready to be integrated into the trading agent.")