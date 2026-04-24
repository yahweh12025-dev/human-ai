import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PerformanceAnalyzer")

class TradingPerformanceAnalyzer:
    def __init__(self, results_dir='backtest_logs'):
        self.results_dir = Path(results_dir)
        self.all_data = []

    def load_all_results(self):
        """Load all JSON results from the backtest_logs directory."""
        if not self.results_dir.exists():
            logger.error(f"Results directory {self.results_dir} not found")
            return False
        
        for file in self.results_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.all_data.extend(data)
                    else:
                        self.all_data.append(data)
            except Exception as e:
                logger.error(f"Error loading {file}: {e}")
        
        logger.info(f"Loaded results from {len(self.all_data)} test scenarios")
        return len(self.all_data) > 0

    def analyze_failure_patterns(self):
        """Identify common failure points and loss drivers."""
        if not self.all_data: return "No data to analyze"
        
        all_trades = []
        for res in self.all_data:
            all_trades.extend(res.get('trades', []))
        
        if not all_trades: return "No trades found in logs"
        
        df = pd.DataFrame(all_trades)
        losses = df[df['pnl'] <= 0]
        
        analysis = {
            "total_trades": len(df),
            "total_losses": len(losses),
            "loss_rate": (len(losses) / len(df)) * 100 if len(df) > 0 else 0,
            "avg_loss": losses['pnl'].mean() if not losses.empty else 0,
            "max_loss": losses['pnl'].min() if not losses.empty else 0,
            "loss_distribution": losses['pnl'].describe().to_dict() if not losses.empty else {}
        }
        return analysis

    def optimize_parameters(self):
        """Suggest optimal SMA periods based on best performing timeframes."""
        # This is a heuristic based on the results loaded
        best_tf = None
        max_return = -float('inf')
        
        for res in self.all_data:
            if res.get('total_return_pct', 0) > max_return:
                max_return = res['total_return_pct']
                best_tf = res.get('timeframe')
        
        return {
            "recommended_tf": best_tf,
            "best_return": max_return,
            "suggested_adj": "Tighten SMA windows for shorter timeframes to capture micro-trends"
        }

    def run_comprehensive_audit(self):
        """Full audit of test data for future improvements."""
        if not self.load_all_results():
            return "Audit failed: No data"
        
        failures = self.analyze_failure_patterns()
        optimizations = self.optimize_parameters()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "failure_analysis": failures,
            "optimization_suggestions": optimizations,
            "data_coverage": {
                "symbols": list(set([r.get('symbol') for r in self.all_data])),
                "timeframes": list(set([r.get('timeframe') for r in self.all_data]))
            }
        }
        return report

if __name__ == "__main__":
    analyzer = TradingPerformanceAnalyzer()
    audit = analyzer.run_comprehensive_audit()
    print(json.dumps(audit, indent=2))
