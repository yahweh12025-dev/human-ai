"""
Automated Outcome Journal Trigger
Tracks trading outcomes and synchronizes them with performance journals and analytics
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
import sqlite3
from collections import defaultdict

logger = logging.getLogger(__name__)

class OutcomeSync:
    """
    Automated Outcome Journal Trigger
    Tracks trading outcomes and syncs with performance journals
    """
    
    def __init__(self, 
                 journal_directory: str = "./human-ai/outputs/journals",
                 analytics_directory: str = "./human-ai/outputs/analytics",
                 sync_interval_minutes: int = 5,
                 buffer_size: int = 100):
        """
        Initialize Outcome Sync
        
        Args:
            journal_directory: Directory to store outcome journals
            analytics_directory: Directory to store analytics data
            sync_interval_minutes: How often to sync outcomes to journals
            buffer_size: Number of outcomes to buffer before forcing sync
        """
        self.journal_dir = Path(journal_directory)
        self.analytics_dir = Path(analytics_directory)
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.buffer_size = buffer_size
        
        # Ensure directories exist
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        
        # Outcome tracking
        self.outcome_buffer = []  # Buffer of outcomes waiting to be synced
        self.last_sync_time = datetime.now()
        self.is_syncing = False
        self.sync_thread = None
        
        # Statistics
        self.total_outcomes = 0
        self.successful_syncs = 0
        self.failed_syncs = 0
        
        # Initialize database for persistent storage
        self.db_path = self.journal_dir / "outcomes.db"
        self._init_database()
        
        logger.info(f"OutcomeSync initialized with journal dir: {self.journal_dir}")
    
    def _init_database(self):
        """Initialize SQLite database for storing outcomes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create outcomes table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_type TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    quantity REAL,
                    pnl REAL,
                    pnl_percent REAL,
                    holding_period_minutes INTEGER,
                    exit_reason TEXT,
                    strategy_used TEXT,
                    market_conditions TEXT,
                    notes TEXT
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON trading_outcomes(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_symbol 
                ON trading_outcomes(symbol)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_pnl 
                ON trading_outcomes(pnl)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Outcome database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize outcome database: {e}")
            raise
    
    def start_sync(self):
        """Start the automatic outcome synchronization"""
        if self.is_syncing:
            logger.warning("OutcomeSync is already running")
            return
        
        self.is_syncing = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("OutcomeSync started")
    
    def stop_sync(self):
        """Stop the automatic outcome synchronization"""
        self.is_syncing = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        
        # Sync any remaining outcomes before stopping
        self._sync_outcomes()
        logger.info("OutcomeSync stopped")
    
    def _sync_loop(self):
        """Main synchronization loop"""
        while self.is_syncing:
            try:
                # Check if it's time to sync based on interval
                if datetime.now() - self.last_sync_time >= self.sync_interval:
                    self._sync_outcomes()
                
                # Check if buffer is full
                if len(self.outcome_buffer) >= self.buffer_size:
                    self._sync_outcomes()
                
                # Sleep briefly to avoid excessive CPU usage
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in OutcomeSync loop: {e}")
                time.sleep(5)  # Shorter sleep on error
    
    def record_outcome(self, outcome_data: Dict[str, Any]):
        """
        Record a trading outcome for synchronization
        
        Args:
            outcome_data: Dictionary containing outcome information
        """
        # Validate required fields
        required_fields = ['timestamp', 'symbol']
        for field in required_fields:
            if field not in outcome_data:
                logger.warning(f"Outcome missing required field '{field}': {outcome_data}")
                return
        
        # Add to buffer
        self.outcome_buffer.append(outcome_data)
        self.total_outcomes += 1
        
        logger.debug(f"Recorded outcome for {outcome_data.get('symbol')}: "
                    f"P&L={outcome_data.get('pnl', 0):.2f}")
        
        # If buffer is getting large, trigger sync
        if len(self.outcome_buffer) >= self.buffer_size // 2:
            logger.debug(f"Outcome buffer at {len(self.outcome_buffer)}/{self.buffer_size}")
    
    def _sync_outcomes(self):
        """Sync buffered outcomes to persistent storage and journals"""
        if not self.outcome_buffer:
            return
        
        if self.is_syncing:
            logger.debug("Sync already in progress, skipping")
            return
        
        self.is_syncing = True
        sync_start = datetime.now()
        
        try:
            outcomes_to_sync = self.outcome_buffer.copy()
            self.outcome_buffer.clear()
            
            logger.info(f"Syncing {len(outcomes_to_sync)} outcomes to journal")
            
            # Store in database
            self._store_outcomes_db(outcomes_to_sync)
            
            # Update journal files
            self._update_journal_files(outcomes_to_sync)
            
            # Update analytics
            self._update_analytics(outcomes_to_sync)
            
            self.last_sync_time = datetime.now()
            self.successful_syncs += 1
            
            sync_duration = (datetime.now() - sync_start).total_seconds()
            logger.info(f"Outcome sync completed in {sync_duration:.2f}s. "
                       f"Synced {len(outcomes_to_sync)} outcomes")
            
        except Exception as e:
            logger.error(f"Failed to sync outcomes: {e}")
            self.failed_syncs += 1
            # Put outcomes back in buffer for retry
            self.outcome_buffer.extend(outcomes_to_sync)
        finally:
            self.is_syncing = False
    
    def _store_outcomes_db(self, outcomes: List[Dict[str, Any]]):
        """Store outcomes in SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for outcome in outcomes:
                cursor.execute('''
                    INSERT INTO trading_outcomes 
                    (timestamp, symbol, signal_type, entry_price, exit_price, 
                     quantity, pnl, pnl_percent, holding_period_minutes, 
                     exit_reason, strategy_used, market_conditions, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    outcome.get('timestamp'),
                    outcome.get('symbol'),
                    outcome.get('signal_type'),
                    outcome.get('entry_price'),
                    outcome.get('exit_price'),
                    outcome.get('quantity'),
                    outcome.get('pnl'),
                    outcome.get('pnl_percent'),
                    outcome.get('holding_period_minutes'),
                    outcome.get('exit_reason'),
                    outcome.get('strategy_used'),
                    json.dumps(outcome.get('market_conditions', {})),
                    outcome.get('notes', '')
                ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored {len(outcomes)} outcomes in database")
            
        except Exception as e:
            logger.error(f"Failed to store outcomes in database: {e}")
            raise
    
    def _update_journal_files(self, outcomes: List[Dict[str, Any]]):
        """Update journal files with new outcomes"""
        try:
            # Create daily journal file
            today = datetime.now().strftime("%Y-%m-%d")
            journal_file = self.journal_dir / f"trading_journal_{today}.json"
            
            # Load existing journal or create new
            if journal_file.exists():
                with open(journal_file, 'r') as f:
                    journal_data = json.load(f)
            else:
                journal_data = {
                    "date": today,
                    "created_at": datetime.now().isoformat(),
                    "outcomes": [],
                    "summary": {
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "total_pnl": 0.0,
                        "win_rate": 0.0,
                        "avg_win": 0.0,
                        "avg_loss": 0.0,
                        "profit_factor": 0.0
                    }
                }
            
            # Add new outcomes
            journal_data["outcomes"].extend(outcomes)
            journal_data["updated_at"] = datetime.now().isoformat()
            
            # Recalculate summary
            self._calculate_journal_summary(journal_data)
            
            # Write back to file
            with open(journal_file, 'w') as f:
                json.dump(journal_data, f, indent=2, default=str)
            
            logger.debug(f"Updated journal file: {journal_file}")
            
        except Exception as e:
            logger.error(f"Failed to update journal files: {e}")
            raise
    
    def _calculate_journal_summary(self, journal_data: Dict[str, Any]):
        """Calculate summary statistics for journal"""
        outcomes = journal_data["outcomes"]
        
        if not outcomes:
            return
        
        total_trades = len(outcomes)
        winning_trades = len([o for o in outcomes if o.get('pnl', 0) > 0])
        losing_trades = len([o for o in outcomes if o.get('pnl', 0) < 0])
        total_pnl = sum(o.get('pnl', 0) for o in outcomes)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        winning_pnls = [o.get('pnl', 0) for o in outcomes if o.get('pnl', 0) > 0]
        losing_pnls = [abs(o.get('pnl', 0)) for o in outcomes if o.get('pnl', 0) < 0]
        
        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
        
        profit_factor = (sum(winning_pnls) / sum(losing_pnls)) if losing_pnls and sum(losing_pnls) > 0 else 0
        
        journal_data["summary"] = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2)
        }
    
    def _update_analytics(self, outcomes: List[Dict[str, Any]]):
        """Update analytics files with new outcome data"""
        try:
            # Update cumulative analytics
            analytics_file = self.analytics_dir / "performance_analytics.json"
            
            # Load existing analytics or create new
            if analytics_file.exists():
                with open(analytics_file, 'r') as f:
                    analytics_data = json.load(f)
            else:
                analytics_data = {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "total_outcomes": 0,
                    "symbols": {},
                    "timeframes": {},
                    "strategies": {},
                    "monthly_performance": {},
                    "yearly_performance": {}
                }
            
            # Update with new outcomes
            for outcome in outcomes:
                symbol = outcome.get('symbol', 'UNKNOWN')
                timestamp = outcome.get('timestamp')
                pnl = outcome.get('pnl', 0)
                strategy = outcome.get('strategy_used', 'UNKNOWN')
                
                # Update symbol statistics
                if symbol not in analytics_data["symbols"]:
                    analytics_data["symbols"][symbol] = {
                        "trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "total_pnl": 0.0,
                        "win_rate": 0.0
                    }
                
                sym_stats = analytics_data["symbols"][symbol]
                sym_stats["trades"] += 1
                if pnl > 0:
                    sym_stats["wins"] += 1
                elif pnl < 0:
                    sym_stats["losses"] += 1
                sym_stats["total_pnl"] += pnl
                sym_stats["win_rate"] = (sym_stats["wins"] / sym_stats["trades"] * 100) if sym_stats["trades"] > 0 else 0
                
                # Update strategy statistics
                if strategy not in analytics_data["strategies"]:
                    analytics_data["strategies"][strategy] = {
                        "trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "total_pnl": 0.0,
                        "win_rate": 0.0
                    }
                
                strat_stats = analytics_data["strategies"][strategy]
                strat_stats["trades"] += 1
                if pnl > 0:
                    strat_stats["wins"] += 1
                elif pnl < 0:
                    strat_stats["losses"] += 1
                strat_stats["total_pnl"] += pnl
                strat_stats["win_rate"] = (strat_stats["wins"] / strat_stats["trades"] * 100) if strat_stats["trades"] > 0 else 0
                
                # Update timeframe analysis (if holding period available)
                holding_period = outcome.get('holding_period_minutes')
                if holding_period is not None:
                    timeframe_key = self._categorize_timeframe(holding_period)
                    if timeframe_key not in analytics_data["timeframes"]:
                        analytics_data["timeframes"][timeframe_key] = {
                            "trades": 0,
                            "total_pnl": 0.0,
                            "avg_pnl": 0.0
                        }
                    
                    tf_stats = analytics_data["timeframes"][timeframe_key]
                    tf_stats["trades"] += 1
                    tf_stats["total_pnl"] += pnl
                    tf_stats["avg_pnl"] = tf_stats["total_pnl"] / tf_stats["trades"] if tf_stats["trades"] > 0 else 0
                
                # Update monthly/yearly performance
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        month_key = dt.strftime("%Y-%m")
                        year_key = dt.strftime("%Y")
                        
                        # Monthly
                        if month_key not in analytics_data["monthly_performance"]:
                            analytics_data["monthly_performance"][month_key] = {
                                "trades": 0,
                                "total_pnl": 0.0,
                                "win_rate": 0.0
                            }
                        
                        month_stats = analytics_data["monthly_performance"][month_key]
                        month_stats["trades"] += 1
                        month_stats["total_pnl"] += pnl
                        
                        # Yearly
                        if year_key not in analytics_data["yearly_performance"]:
                            analytics_data["yearly_performance"][year_key] = {
                                "trades": 0,
                                "total_pnl": 0.0,
                                "win_rate": 0.0
                            }
                        
                        year_stats = analytics_data["yearly_performance"][year_key]
                        year_stats["trades"] += 1
                        year_stats["total_pnl"] += pnl
                        
                    except Exception as e:
                        logger.debug(f"Could not parse timestamp for period analysis: {timestamp}")
            
            # Update metadata
            analytics_data["updated_at"] = datetime.now().isoformat()
            analytics_data["total_outcomes"] = analytics_data.get("total_outcomes", 0) + len(outcomes)
            
            # Recalculate win rates for symbols and strategies
            for symbol_data in analytics_data["symbols"].values():
                if symbol_data["trades"] > 0:
                    symbol_data["win_rate"] = (symbol_data["wins"] / symbol_data["trades"] * 100)
            
            for strategy_data in analytics_data["strategies"].values():
                if strategy_data["trades"] > 0:
                    strategy_data["win_rate"] = (strategy_data["wins"] / strategy_data["trades"] * 100)
            
            # Write back to file
            with open(analytics_file, 'w') as f:
                json.dump(analytics_data, f, indent=2, default=str)
            
            logger.debug(f"Updated analytics file: {analytics_file}")
            
        except Exception as e:
            logger.error(f"Failed to update analytics: {e}")
            raise
    
    def _categorize_timeframe(self, minutes: int) -> str:
        """Categorize holding period into timeframe buckets"""
        if minutes < 5:
            return "scalp"
        elif minutes < 60:
            return "intraday"
        elif minutes < 480:  # 8 hours
            return "day_trade"
        elif minutes < 10080:  # 1 week
            return "swing"
        else:
            return "position"
    
    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get performance summary for the last N days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with performance statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date threshold
            threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get outcomes from database
            cursor.execute('''
                SELECT * FROM trading_outcomes 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (threshold_date,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return {
                    "period_days": days,
                    "total_trades": 0,
                    "message": "No trades found in specified period"
                }
            
            # Convert rows to dictionaries
            columns = [description[0] for description in cursor.description]
            outcomes = []
            for row in rows:
                outcome = dict(zip(columns, row))
                # Parse JSON fields
                if outcome['market_conditions']:
                    try:
                        outcome['market_conditions'] = json.loads(outcome['market_conditions'])
                    except:
                        outcome['market_conditions'] = {}
                outcomes.append(outcome)
            
            # Calculate statistics
            total_trades = len(outcomes)
            winning_trades = len([o for o in outcomes if o['pnl'] > 0])
            losing_trades = len([o for o in outcomes if o['pnl'] < 0])
            total_pnl = sum(o['pnl'] for o in outcomes)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            winning_pnls = [o['pnl'] for o in outcomes if o['pnl'] > 0]
            losing_pnls = [abs(o['pnl']) for o in outcomes if o['pnl'] < 0]
            
            avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
            avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
            
            profit_factor = (sum(winning_pnls) / sum(losing_pnls)) if losing_pnls and sum(losing_pnls) > 0 else 0
            
            # Group by symbol
            by_symbol = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
            for outcome in outcomes:
                symbol = outcome['symbol']
                by_symbol[symbol]["trades"] += 1
                by_symbol[symbol]["pnl"] += outcome['pnl']
                if outcome['pnl'] > 0:
                    by_symbol[symbol]["wins"] += 1
            
            symbol_summary = {}
            for symbol, stats in by_symbol.items():
                symbol_win_rate = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
                symbol_summary[symbol] = {
                    "trades": stats["trades"],
                    "total_pnl": round(stats["pnl"], 2),
                    "win_rate": round(symbol_win_rate, 2)
                }
            
            return {
                "period_days": days,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2),
                "best_trade": max([o['pnl'] for o in outcomes]) if outcomes else 0,
                "worst_trade": min([o['pnl'] for o in outcomes]) if outcomes else 0,
                "by_symbol": symbol_summary,
                "period_start": min([o['timestamp'] for o in outcomes]) if outcomes else None,
                "period_end": max([o['timestamp'] for o in outcomes]) if outcomes else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {"error": str(e)}
    
    def force_sync(self):
        """Force an immediate synchronization of all buffered outcomes"""
        logger.info("Forcing immediate outcome sync")
        self._sync_outcomes()

# Global instance for easy access
outcome_sync = OutcomeSync()

def start_outcome_tracking():
    """Start the global outcome sync tracking"""
    outcome_sync.start_sync()

def stop_outcome_tracking():
    """Stop the global outcome sync tracking"""
    outcome_sync.stop_sync()

def record_trade_outcome(outcome_data: Dict[str, Any]):
    """Record a trade outcome using the global outcome sync"""
    outcome_sync.record_outcome(outcome_data)

def get_performance_stats(days: int = 30) -> Dict[str, Any]:
    """Get performance statistics using the global outcome sync"""
    return outcome_sync.get_performance_summary(days)

# Example usage and testing
if __name__ == "__main__":
    # Configure logging to see output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create outcome sync instance
    sync = OutcomeSync(
        journal_directory="./test_journals",
        analytics_directory="./test_analytics",
        sync_interval_minutes=1,  # Sync every minute for demo
        buffer_size=5
    )
    
    # Start syncing
    sync.start_sync()
    
    try:
        print("OutcomeSync started. Recording test trades...")
        
        # Simulate some trading outcomes
        test_outcomes = [
            {
                "timestamp": datetime.now().isoformat(),
                "symbol": "BTC/USDT",
                "signal_type": "BUY",
                "entry_price": 65000.0,
                "exit_price": 67000.0,
                "quantity": 0.1,
                "pnl": 200.0,
                "pnl_percent": 3.08,
                "holding_period_minutes": 45,
                "exit_reason": "Take profit hit",
                "strategy_used": "VAB_Momentum",
                "market_conditions": {
                    "regime": "trending_up",
                    "volatility": "medium",
                    "volume": "high"
                },
                "notes": "Good entry on pullback to EMA20"
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "symbol": "ETH/USDT",
                "signal_type": "SELL",
                "entry_price": 3200.0,
                "exit_price": 3100.0,
                "quantity": 1.0,
                "pnl": 100.0,
                "pnl_percent": 3.125,
                "holding_period_minutes": 120,
                "exit_reason": "Stop loss hit",
                "strategy_used": "MeanReversion",
                "market_conditions": {
                    "regime": "ranging",
                    "volatility": "low",
                    "volume": "medium"
                },
                "notes": "Failed breakdown attempt"
            },
            {
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "symbol": "ADA/USDT",
                "signal_type": "BUY",
                "entry_price": 0.45,
                "exit_price": 0.48,
                "quantity": 100.0,
                "pnl": 3.0,
                "pnl_percent": 6.67,
                "holding_period_minutes": 30,
                "exit_reason": "Signal reversal",
                "strategy_used": "VAB_Momentum",
                "market_conditions": {
                    "regime": "trending_up",
                    "volatility": "high",
                    "volume": "very_high"
                },
                "notes": "Quick scalping trade"
            }
        ]
        
        # Record outcomes
        for outcome in test_outcomes:
            sync.record_outcome(outcome)
            print(f"Recorded outcome: {outcome['symbol']} {outcome['signal_type']} P&L: {outcome['pnl']:.2f}")
            time.sleep(0.5)  # Small delay between records
        
        # Wait for sync to happen
        print("\nWaiting for automatic sync...")
        time.sleep(70)  # Wait for sync interval + buffer
        
        # Force a final sync
        print("\nForcing final sync...")
        sync.force_sync()
        
        # Show performance summary
        print("\nPerformance Summary (Last 7 days):")
        summary = sync.get_performance_summary(days=7)
        for key, value in summary.items():
            if key != "by_symbol":
                print(f"  {key}: {value}")
        
        if "by_symbol" in summary:
            print("  By Symbol:")
            for symbol, stats in summary["by_symbol"].items():
                print(f"    {symbol}: {stats}")
        
        # Show journal files created
        journal_dir = Path("./test_journals")
        if journal_dir.exists():
            print(f"\nJournal files created:")
            for journal_file in journal_dir.glob("*.json"):
                print(f"  {journal_file.name}")
        
        # Show analytics files created
        analytics_dir = Path("./test_analytics")
        if analytics_dir.exists():
            print(f"\nAnalytics files created:")
            for analytics_file in analytics_dir.glob("*.json"):
                print(f"  {analytics_file.name}")
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Stop syncing
        sync.stop_sync()
        print("OutcomeSync stopped.")
