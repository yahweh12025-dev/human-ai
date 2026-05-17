import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import requests
import ccxt
import pandas as pd

class MarketDataParserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Market Data Parser")
        self.root.geometry("600x500")

        # UI Elements
        ttk.Label(root, text="Symbol (e.g., BTC/USD):").pack(pady=5)
        self.symbol_entry = ttk.Entry(root)
        self.symbol_entry.insert(0, "BTC/USD")
        self.symbol_entry.pack(pady=5)

        ttk.Label(root, text="Source:").pack(pady=5)
        self.source_var = tk.StringVar(value="CoinGecko")
        ttk.Combobox(root, textvariable=self.source_var, values=["CoinGecko", "Binance"]).pack(pady=5)

        self.fetch_btn = ttk.Button(root, text="Fetch Data", command=self.start_fetch_thread)
        self.fetch_btn.pack(pady=10)

        self.output_area = scrolledtext.ScrolledText(root, width=70, height=20)
        self.output_area.pack(pady=10)

    def start_fetch_thread(self):
        self.fetch_btn.config(state=tk.DISABLED)
        self.output_area.delete(1.0, tk.END)
        self.output_area.insert(tk.END, "Fetching data...\n")
        
        # Run network requests in a separate thread
        thread = threading.Thread(target=self.fetch_data)
        thread.start()

    def fetch_data(self):
        symbol = self.symbol_entry.get()
        source = self.source_var.get()

        try:
            if source == "CoinGecko":
                data = self._get_coingecko_data(symbol)
            else:
                data = self._get_binance_data(symbol)
                
            self.root.after(0, self.update_ui, data)
        except Exception as e:
            self.root.after(0, self.update_ui, f"Error: {str(e)}")

    def _get_coingecko_data(self, symbol: str):
        """Free CoinGecko implementation using context mapping"""
        symbol_map = {
            'BTC/USD': 'bitcoin', 'ETH/USD': 'ethereum', 'SOL/USD': 'solana',
            'XRP/USD': 'ripple', 'ADA/USD': 'cardano', 'DOGE/USD': 'dogecoin'
        }
        coin_id = symbol_map.get(symbol, symbol.lower().replace('/usd', '').replace('-usd', ''))
        
        # Fetching last 24h market chart (1 day)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=1"
        response = requests.get(url)
        response.raise_for_status()
        
        prices = response.json().get('prices', [])
        if not prices:
            return "No data found for this symbol on CoinGecko."
            
        # Convert to DataFrame for clean parsing
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df.tail(5).to_string() # Return last 5 data points

    def _get_binance_data(self, symbol: str):
        """Binance implementation using CCXT"""
        # Note: Binance testnet futures sandbox is deprecated. Using live spot for standard data fetch.
        exchange = ccxt.binance({'enableRateLimit': True})
        
        # Format symbol for CCXT (e.g., BTC/USDT)
        ccxt_symbol = symbol.replace('USD', 'USDT')
        
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe='1h', limit=5)
        
        # Handling standard column formats (Context 3 compliance)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df.to_string()

    def update_ui(self, result):
        self.output_area.delete(1.0, tk.END)
        self.output_area.insert(tk.END, result)
        self.fetch_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = MarketDataParserGUI(root)
    root.mainloop()
