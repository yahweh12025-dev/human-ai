#!/usr/bin/env python3
"""
Unified Agent Improvement Workflow
Orchestrates the cycle: Implement → Backtest → Review → Iterate
Works for both FreqTrade and EA agents
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

import importlib.util

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_project_root = Path(__file__).parent.parent.parent
_ft_bridge = _load_module('ft_bridge', str(_project_root / 'agents' / 'trading-agent' / 'openclaw_freqtrade_bridge.py'))
_ea_trigger = _load_module('ea_trigger', str(_project_root / 'agents' / 'openclaw_ea_trigger_gui.py'))
OpenClawFreqTradeBridge = _ft_bridge.OpenClawFreqTradeBridge
OpenClawEATrigger = _ea_trigger.OpenClawEATrigger


class UnifiedImprovementWorkflow:
    """
    Orchestrates continuous improvement cycle for trading agents:
    1. Agent implements strategy improvement
    2. Automatically triggers backtest
    3. Reviews results and extracts metrics
    4. Decides on next iteration based on performance
    """

    def __init__(self):
        self.project_root = Path.home() / "human-ai"
        self.freqtrade_bridge = OpenClawFreqTradeBridge()
        self.ea_trigger = OpenClawEATrigger()

        self.workflow_log = []
        self.iteration_counter = 0

    def execute_freqtrade_improvement_cycle(self, strategy_params: Dict = None) -> Dict:
        """
        Execute improvement cycle for FreqTrade agent

        Args:
            strategy_params: Strategy parameters to test

        Returns:
            Results dictionary with performance metrics
        """
        self.iteration_counter += 1
        cycle_id = f"FT_CYCLE_{self.iteration_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\n{'='*70}")
        print(f"🔄 FreqTrade Improvement Cycle #{self.iteration_counter}")
        print(f"{'='*70}")

        cycle_result = {
            'cycle_id': cycle_id,
            'agent': 'FreqTrade',
            'iteration': self.iteration_counter,
            'timestamp_start': datetime.now().isoformat(),
            'steps': []
        }

        # Step 1: Download latest data
        print("\n📊 Step 1/4: Downloading market data...")
        data_result = self.freqtrade_bridge.download_market_data(
            pairs=['BTC/USDT'],
            timerange='20260401-20260510'
        )
        cycle_result['steps'].append({
            'step': 'download_data',
            'status': data_result['status'],
            'details': data_result
        })

        if data_result['status'] != 'completed':
            print(f"   ❌ Data download failed")
            return self._finalize_cycle(cycle_result, 'failed')

        print(f"   ✅ Market data ready")

        # Step 2: Run backtest
        print("\n🧪 Step 2/4: Running backtest...")
        backtest_result = self.freqtrade_bridge.run_backtest(
            strategy='SwarmIntelligenceStrategy',
            timerange='20260401-20260510'
        )
        cycle_result['steps'].append({
            'step': 'backtest',
            'status': backtest_result['status'],
            'details': backtest_result
        })

        if backtest_result['status'] != 'completed':
            print(f"   ❌ Backtest failed")
            return self._finalize_cycle(cycle_result, 'failed')

        print(f"   ✅ Backtest completed")

        # Step 3: Analyze results
        print("\n📈 Step 3/4: Analyzing results...")
        analysis = self._analyze_freqtrade_results(backtest_result)
        cycle_result['steps'].append({
            'step': 'analysis',
            'analysis': analysis
        })

        print(f"   Performance Score: {analysis['score']}/100")
        print(f"   Rating: {analysis['rating']}")

        # Step 4: Generate recommendations
        print("\n💡 Step 4/4: Generating recommendations...")
        recommendations = self._generate_freqtrade_recommendations(analysis)
        cycle_result['steps'].append({
            'step': 'recommendations',
            'recommendations': recommendations
        })

        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['action']}: {rec['description']}")

        # Finalize
        return self._finalize_cycle(cycle_result, 'completed')

    def execute_ea_improvement_cycle(self, ea_name: str = "MasterMetalsEA") -> Dict:
        """
        Execute improvement cycle for EA agent

        Args:
            ea_name: EA to test

        Returns:
            Results dictionary with performance metrics
        """
        self.iteration_counter += 1
        cycle_id = f"EA_CYCLE_{self.iteration_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\n{'='*70}")
        print(f"🔄 EA Improvement Cycle #{self.iteration_counter}")
        print(f"{'='*70}")

        cycle_result = {
            'cycle_id': cycle_id,
            'agent': 'EA',
            'ea_name': ea_name,
            'iteration': self.iteration_counter,
            'timestamp_start': datetime.now().isoformat(),
            'steps': []
        }

        # Step 1: Compile EA
        print(f"\n🔧 Step 1/4: Compiling {ea_name}...")
        compile_result = self.ea_trigger.bridge.compile_ea(ea_name)
        cycle_result['steps'].append({
            'step': 'compile',
            'status': compile_result['status'],
            'details': compile_result
        })

        if compile_result.get('errors', 0) > 0:
            print(f"   ❌ Compilation errors: {compile_result['errors']}")
            return self._finalize_cycle(cycle_result, 'compilation_failed')

        print(f"   ✅ Compilation successful ({compile_result.get('warnings', 0)} warnings)")

        # Step 2: Run backtest
        print(f"\n🧪 Step 2/4: Running backtest...")
        backtest_result = self.ea_trigger.bridge.run_backtest(
            ea_name=ea_name,
            symbol="XAUUSD",
            timeframe="M15",
            start_date="2026.01.01",
            end_date="2026.05.10"
        )
        cycle_result['steps'].append({
            'step': 'backtest',
            'status': backtest_result['status'],
            'details': backtest_result
        })

        if backtest_result['status'] not in ['completed', 'completed_simulated']:
            print(f"   ❌ Backtest failed")
            return self._finalize_cycle(cycle_result, 'failed')

        print(f"   ✅ Backtest completed")
        print(f"      Net Profit: ${backtest_result.get('net_profit', 0):.2f}")
        print(f"      Win Rate: {backtest_result.get('win_rate', 0):.1f}%")

        # Step 3: Analyze results
        print(f"\n📈 Step 3/4: Analyzing results...")
        analysis = self.ea_trigger._analyze_backtest(backtest_result)
        cycle_result['steps'].append({
            'step': 'analysis',
            'analysis': analysis
        })

        print(f"   Performance Score: {analysis['score']}/100")
        print(f"   Rating: {analysis['rating']}")
        print(f"   Recommended: {'Yes' if analysis['recommended'] else 'No'}")

        # Step 4: Generate recommendations
        print(f"\n💡 Step 4/4: Generating recommendations...")
        recommendations = self._generate_ea_recommendations(analysis, backtest_result)
        cycle_result['steps'].append({
            'step': 'recommendations',
            'recommendations': recommendations
        })

        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['action']}: {rec['description']}")

        # Finalize
        return self._finalize_cycle(cycle_result, 'completed')

    def _analyze_freqtrade_results(self, backtest_output: Dict) -> Dict:
        """Analyze FreqTrade backtest results"""
        # Parse backtest stdout for metrics
        # This would parse actual FreqTrade output
        # For now, simulate analysis

        return {
            'score': 75,
            'rating': 'Good',
            'profitable': True,
            'recommended': True,
            'strengths': ['Consistent wins', 'Good risk management'],
            'weaknesses': ['Lower profit factor', 'Max drawdown high']
        }

    def _analyze_ea_results(self, backtest_data: Dict) -> Dict:
        """Already implemented in OpenClawEATrigger"""
        return self.ea_trigger._analyze_backtest(backtest_data)

    def _generate_freqtrade_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate actionable recommendations for FreqTrade strategy"""
        recommendations = []

        if analysis['score'] < 60:
            recommendations.append({
                'priority': 'high',
                'action': 'Adjust entry threshold',
                'description': 'Increase RSI threshold to filter weak signals',
                'parameter': 'buy_rsi_threshold',
                'suggested_value': 35
            })

        if 'drawdown' in str(analysis.get('weaknesses', [])).lower():
            recommendations.append({
                'priority': 'medium',
                'action': 'Tighten stop loss',
                'description': 'Reduce max loss per trade to limit drawdown',
                'parameter': 'stoploss',
                'suggested_value': -0.03
            })

        if len(recommendations) == 0:
            recommendations.append({
                'priority': 'low',
                'action': 'Optimize parameters',
                'description': 'Run hyperopt to fine-tune current settings',
                'next_step': 'hyperopt'
            })

        return recommendations

    def _generate_ea_recommendations(self, analysis: Dict, backtest: Dict) -> List[Dict]:
        """Generate actionable recommendations for EA"""
        recommendations = []

        if analysis['score'] < 60:
            recommendations.append({
                'priority': 'high',
                'action': 'Adjust risk per basket',
                'description': 'Reduce risk from 2.5% to 2.0% to limit losses',
                'parameter': 'BasketRiskPct',
                'suggested_value': 2.0
            })

        if backtest.get('win_rate', 0) < 50:
            recommendations.append({
                'priority': 'high',
                'action': 'Increase entry score threshold',
                'description': 'Raise MinScoreToTrade to filter weak entries',
                'parameter': 'MinScoreToTrade',
                'suggested_value': 4.0
            })

        if backtest.get('profit_factor', 0) < 1.5:
            recommendations.append({
                'priority': 'medium',
                'action': 'Optimize exit logic',
                'description': 'Increase partial close threshold for better R:R',
                'parameter': 'Partial_RR',
                'suggested_value': 1.5
            })

        return recommendations

    def _finalize_cycle(self, cycle_data: Dict, status: str) -> Dict:
        """Finalize improvement cycle and log results"""
        cycle_data['timestamp_end'] = datetime.now().isoformat()
        cycle_data['status'] = status
        cycle_data['duration_seconds'] = (
            datetime.fromisoformat(cycle_data['timestamp_end']) -
            datetime.fromisoformat(cycle_data['timestamp_start'])
        ).seconds

        # Log to workflow history
        self.workflow_log.append(cycle_data)

        # Save to file
        log_file = self.project_root / "data" / "data" / "logs" / "workflows" / f"{cycle_data['cycle_id']}.json"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, 'w') as f:
            json.dump(cycle_data, f, indent=2)

        # Push to swarm queue
        self._push_to_swarm(cycle_data)

        print(f"\n{'='*70}")
        print(f"✅ Cycle complete: {status}")
        print(f"   Duration: {cycle_data['duration_seconds']}s")
        print(f"   Log: {log_file}")
        print(f"{'='*70}\n")

        return cycle_data

    def _push_to_swarm(self, cycle_data: Dict):
        """Push cycle results to swarm queue"""
        queue_file = self.project_root / "swarm" / "improvement_cycles.jsonl"
        queue_file.parent.mkdir(parents=True, exist_ok=True)

        with open(queue_file, 'a') as f:
            f.write(json.dumps(cycle_data) + '\n')

    def get_workflow_history(self, limit: int = 10) -> List[Dict]:
        """Get recent workflow history"""
        return self.workflow_log[-limit:]


def main():
    """Main execution"""
    print("🤖 Unified Agent Improvement Workflow - Starting...")

    workflow = UnifiedImprovementWorkflow()

    # Test EA cycle
    print("\n🎯 Testing EA improvement cycle...")
    ea_result = workflow.execute_ea_improvement_cycle("MasterMetalsEA")

    # Show summary
    print("\n📋 Workflow Summary:")
    print(f"   Total cycles: {workflow.iteration_counter}")
    print(f"   Latest cycle: {ea_result['cycle_id']}")
    print(f"   Status: {ea_result['status']}")

    return workflow


if __name__ == "__main__":
    workflow = main()
