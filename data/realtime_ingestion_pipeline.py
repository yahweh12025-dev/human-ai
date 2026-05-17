import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeIngestionPipeline:
    """
    Real-time data pipeline that ingests market data from multiple exchanges 
    and stores it in a time-series database format.
    """
    def __init__(self, exchanges: List[str]):
        self.exchanges = exchanges
        self.buffer = []
        self.storage = {} # Mock time-series DB

    def ingest(self, exchange: str, data: Dict[str, Any]):
        """Ingests a single data packet from an exchange."""
        if exchange not in self.exchanges:
            logger.warning(f"Unknown exchange: {exchange}")
            return
        
        packet = {
            "exchange": exchange,
            "timestamp": pd.Timestamp.now(),
            "data": data
        }
        self.buffer.append(packet)
        
        # Flush buffer to storage if it reaches a threshold
        if len(self.buffer) >= 100:
            self.flush_to_storage()

    def flush_to_storage(self):
        """Writes buffered data to the mock time-series database."""
        logger.info(f"Flushing {len(self.buffer)} packets to storage...")
        for packet in self.buffer:
            symbol = packet['data'].get('symbol', 'UNKNOWN')
            if symbol not in self.storage:
                self.storage[symbol] = []
            self.storage[symbol].append(packet)
        self.buffer = []

    def get_recent_data(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves the most recent data for a specific symbol."""
        return self.storage.get(symbol, [])[-limit:]

if __name__ == "__main__":
    pipeline = RealtimeIngestionPipeline(["BINANCE", "COINBASE"])
    # Simulate ingestion
    for _ in range(110):
        pipeline.ingest("BINANCE", {"symbol": "BTCUSDT", "price": np.random.normal(60000, 100)})
    
    print(f"Ingested data for BTCUSDT: {len(pipeline.get_recent_data('BTCUSDT'))} records")
