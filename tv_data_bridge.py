"""
SOS Engine Data Bridge - WebSocket Client

Connects to the SOS Engine WebSocket server to provide real-time market data
with a multi-source redundancy strategy.

Data Feeds Sent:
- `CANDLE_UPDATE`: Per-symbol 1-minute OHLCV snapshots.
- `SENTIMENT_UPDATE`: Market sentiment regime derived from PCR and market breadth.

Redundancy Tiers:
- Candles: Upstox (Primary) -> TradingView (Secondary) -> Yahoo Finance (Tertiary)
- Breadth/PCR: NSE API (Primary) -> Trendlyne DB/TV Screener (Fallbacks)

Usage:
    python tv_data_bridge.py --port 8765
    # Connects to ws://localhost:8765 by default

Dependencies:
    - websockets, pandas, requests
    - tradingview-screener, yfinance
    - upstox-client (optional, for primary data source)
    - backfill_trendlyne (optional, for historical option chain)

Author: Mahesh
Version: 3.0 (Contract-Compliant Refactor)
"""
print("--- Data Bridge script started ---")
import time
import json
import argparse
import asyncio
import websockets
import pandas as pd
from datetime import datetime
from tradingview_screener import Query, col
from NSEAPICLient import NSEHistoricalAPI
from SymbolMaster import MASTER as SymbolMaster

# Yahoo Finance Import (Level 3 Fallback)
try:
    import yfinance as yf
    YAHOO_AVAILABLE = True
except ImportError:
    YAHOO_AVAILABLE = False
    print("[WARN] yfinance not found. Level 3 Candle Fallback disabled.")

try:
    from backfill_trendlyne import DB as TrendlyneDB, fetch_live_snapshot
except ImportError:
    TrendlyneDB = None
    fetch_live_snapshot = None
    print("[WARN] could not import backfill_trendlyne. Option chain data will be missing.")

# Upstox SDK Imports
try:
    import upstox_client
    import config
    UPSTOX_AVAILABLE = True
except ImportError:
    UPSTOX_AVAILABLE = False
    print("[WARN] Upstox SDK or config not found. Level 3 Fallback disabled.")
# Configuration
# Adding more comprehensive list of symbols for scanning
SYMBOLS = [
    'RELIANCE', 'SBIN', 'ADANIENT', 'NIFTY', 'BANKNIFTY',
    'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'BHARTIARTL',
    'ITC', 'KOTAKBANK', 'HINDUNILVR', 'LT', 'AXISBANK',
    'MARUTI', 'SUNPHARMA', 'TITAN', 'ULTRACEMCO', 'WIPRO',
    'BAJFINANCE', 'ASIANPAINT', 'HCLTECH', 'NTPC', 'POWERGRID'
]

class SOSDataBridgeClient:
    def __init__(self, symbols, host='localhost', port=8765):
        self.uri = f"ws://{host}:{port}"
        self.symbols = symbols
        self.nse = NSEHistoricalAPI()
        self.tickers = [f"NSE:{s}" for s in symbols]
        self.websocket = None
        self.connection_established = asyncio.Event()
        self.pcr_data = {"NIFTY": 1.0, "BANKNIFTY": 1.0}
        self.market_breadth = {"advances": 0, "declines": 0} # Simplified state

    async def send_message(self, message):
        """Generic method to send a JSON message to the SOS Engine."""
        if not self.websocket:
            print("[WARN] No active connection. Message dropped.")
            return False
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except websockets.ConnectionClosed:
            print("[WARN] Connection closed while sending. Will attempt reconnect.")
            self.websocket = None
            return False

    async def publish_sentiment_update(self):
        """
        Calculates and sends the `SENTIMENT_UPDATE` message every 30 seconds.
        """
        await self.connection_established.wait()
        while True:
            # 1. Update PCR and Breadth Data (in-memory)
            await self.update_pcr_and_breadth()

            # 2. Determine Regime
            pcr = self.pcr_data.get("NIFTY", 1.0) # Use NIFTY as primary indicator
            adv = self.market_breadth.get("advances", 0)
            dec = self.market_breadth.get("declines", 1) # Avoid division by zero

            regime = "UNKNOWN"
            ratio = adv / dec if dec > 0 else adv

            if pcr < 0.8 and ratio > 1.5: regime = "COMPLETE_BULLISH"
            elif pcr < 0.9 and ratio > 1.2: regime = "BULLISH"
            elif pcr < 1.0 and ratio > 1.0: regime = "SIDEWAYS_BULLISH"
            elif pcr > 1.2 and ratio < 0.7: regime = "COMPLETE_BEARISH"
            elif pcr > 1.1 and ratio < 0.9: regime = "BEARISH"
            elif pcr > 1.0 and ratio < 1.0: regime = "SIDEWAYS_BEARISH"
            else: regime = "SIDEWAYS"

            # 3. Format and Send Message
            message = {
                "type": "SENTIMENT_UPDATE",
                "timestamp": int(time.time() * 1000),
                "data": {"regime": regime}
            }
            await self.send_message(message)
            print(f"[SENTIMENT] Sent update: {regime} (PCR: {pcr}, ADV/DEC: {round(ratio, 2)})")

            await asyncio.sleep(30) # 30-second interval for sentiment

    async def update_pcr_and_breadth(self):
        """
        Internal method to fetch latest PCR and Breadth data.
        This runs just before calculating sentiment.
        """
        # Fetch Market Breadth
        try:
            data = self.nse.get_market_breadth()
            if data and 'advance' in data:
                counts = data['advance'].get('count', {})
                advances = counts.get('Advances', 0)
                declines = counts.get('Declines', 0)
                self.market_breadth['advances'] = advances
                self.market_breadth['declines'] = declines

                # Persist Market Breadth
                if TrendlyneDB:
                    ts = int(time.time())
                    adv_dec_ratio = advances / declines if declines > 0 else advances
                    TrendlyneDB.save_market_depth(ts, "NIFTY_TOTAL", 0, 0, adv_dec_ratio)

        except Exception as e:
            print(f"[WARN] NSE Breadth fetch failed: {e}. Using stale data.")

        # Fetch PCR
        try:
            for sym in ["NIFTY", "BANKNIFTY"]:
                # Try NSE Live API first
                try:
                    data = self.nse.get_option_chain_v3(sym, indices=True)
                    if data and 'records' in data:
                        filtered = data.get('filtered', {})
                        if filtered:
                            ce_oi = filtered.get('CE', {}).get('totOI', 0)
                            pe_oi = filtered.get('PE', {}).get('totOI', 0)
                            if ce_oi > 0:
                                self.pcr_data[sym] = round(pe_oi / ce_oi, 2)
                                continue # Skip fallback if successful
                except Exception:
                    pass # Silently fail to try fallback

                # Fallback to Trendlyne DB
                if TrendlyneDB:
                    agg = TrendlyneDB.get_latest_aggregates(sym)
                    if agg: self.pcr_data[sym] = agg['pcr']
        except Exception as e:
            print(f"[WARN] PCR update failed: {e}. Using stale data.")

    async def publish_candles(self):
        """
        Continuously fetches candle data and sends `CANDALE_UPDATE` messages
        for each symbol.
        """
        await self.connection_established.wait()
        while True:
            # This logic fetches all symbols at once
            all_candles_data = await self.fetch_all_candles()

            if all_candles_data:
                for candle_info in all_candles_data:
                    # Ensure data types are compliant with the contract
                    candle_data = candle_info["1m"]

                    # Format message according to contract
                    message = {
                        "type": "CANDLE_UPDATE",
                        "timestamp": candle_info["timestamp"],
                        "data": {
                            "symbol": candle_info["symbol"],
                            "candle": {
                                "open": float(candle_data.get("open") or 0.0),
                                "high": float(candle_data.get("high") or 0.0),
                                "low": float(candle_data.get("low") or 0.0),
                                "close": float(candle_data.get("close") or 0.0),
                                "volume": int(candle_data.get("volume") or 0)
                            }
                        }
                    }
                    await self.send_message(message)
                print(f"[CANDLE] Sent updates for {len(all_candles_data)} symbols.")

            # Poll every 10 seconds to catch the latest 1-min candle
            await asyncio.sleep(10)

    async def fetch_all_candles(self):
        """
        Orchestrates fetching candles from multiple sources with fallbacks.
        """
        # Priority 1: Upstox
        if UPSTOX_AVAILABLE and hasattr(config, 'ACCESS_TOKEN') and config.ACCESS_TOKEN:
            try:
                candles = self._fetch_candles_upstox()
                if candles: return candles
            except Exception as e:
                print(f"[WARN] Upstox fetch failed: {e}. Falling back.")

        # Priority 2: TradingView
        try:
            candles = self._fetch_candles_tv()
            if candles: return candles
        except Exception as e:
            print(f"[WARN] TradingView fetch failed: {e}. Falling back.")

        # Priority 3: Yahoo Finance
        try:
            candles = self._fetch_candles_yahoo()
            if candles: return candles
        except Exception as e:
            print(f"[ERROR] All candle sources failed: {e}.")
            return []

    def _fetch_candles_yahoo(self):
        """Fallback: Fetch from Yahoo Finance."""
        if not YAHOO_AVAILABLE: return []

        candles = []
        ts = int(time.time() * 1000)
        for sym in self.symbols:
            y_sym = f"{sym}.NS"
            if sym == "NIFTY": y_sym = "^NSEI"
            if sym == "BANKNIFTY": y_sym = "^NSEBANK"

            try:
                ticker = yf.Ticker(y_sym)
                df = ticker.history(period="1d", interval="1m")
                if df.empty: continue
                last = df.iloc[-1]
                candles.append({
                    "symbol": sym, "timestamp": ts,
                    "1m": {"open": last['Open'], "high": last['High'], "low": last['Low'], "close": last['Close'], "volume": last['Volume']}
                })
            except Exception:
                continue
        return candles

    def _fetch_candles_upstox(self):
        """PRIMARY: Fetch latest intraday candles using Upstox HistoryV3 API."""
        if not UPSTOX_AVAILABLE or not config.ACCESS_TOKEN:
            print("[CRITICAL] Upstox Fallback unavailable (No Token/SDK).")
            return []

        upstox_candles = []
        try:
            configuration = upstox_client.Configuration()
            configuration.access_token = config.ACCESS_TOKEN
            api_client = upstox_client.ApiClient(configuration)
            history_api = upstox_client.HistoryV3Api(api_client) # Use HistoryV3Api

            ts = int(time.time() // 60 * 60 * 1000)

            for sym in self.symbols:
                u_key = SymbolMaster.get_upstox_key(sym)
                if not u_key: continue

                try:
                    # Fetch Intraday Data (Current Day)
                    response = history_api.get_intra_day_candle_data(u_key, "1minute")

                    if response and hasattr(response, 'data') and hasattr(response.data, 'candles'):
                        candles = response.data.candles
                        if not candles: continue

                        sorted_candles = sorted(candles, key=lambda x: x[0], reverse=True)
                        last_candle = sorted_candles[0]

                        ltp = float(last_candle[4]) # Close
                        op = float(last_candle[1])
                        hi = float(last_candle[2])
                        lo = float(last_candle[3])
                        vol = int(last_candle[5])

                        # Create Candle Packet
                        c_data = {
                            "symbol": sym, "timestamp": ts,
                            "1m": {
                                "open": op, "high": hi, "low": lo, "close": ltp, "volume": vol,
                            }
                        }
                        upstox_candles.append(c_data)

                except Exception as inner_e:
                     # print(f"[UPSTOX INNER ERROR] {sym}: {inner_e}")
                     continue

            if upstox_candles:
                 print(f"[UPSTOX PRIMARY] Recovered {len(upstox_candles)} symbols.")
            return upstox_candles

        except Exception as e:
            print(f"[CRITICAL] Upstox Primary Failed: {e}")
            return []

    def _fetch_candles_tv(self):
        """Secondary: Fetch from TradingView Screener."""
        scanner = Query().select('name', 'open|1', 'high|1', 'low|1', 'close|1', 'volume|1')
        scanner.set_tickers(*self.tickers)
        data = scanner.get_scanner_data(cookies=None) # Using public API

        candles = []
        if data and len(data) > 1:
            ts = int(time.time() * 1000)
            for _, row in data[1].iterrows():
                candles.append({
                    "symbol": row['name'].split(':')[-1], "timestamp": ts,
                    "1m": {"open": row['open|1'], "high": row['high|1'], "low": row['low|1'], "close": row['close|1'], "volume": row['volume|1']}
                })
        return candles

    async def publish_option_chain(self):
        """
        Periodically fetches and sends `OPTION_CHAIN_UPDATE` messages.
        """
        await self.connection_established.wait()
        loop = asyncio.get_running_loop()
        while True:
            if TrendlyneDB and fetch_live_snapshot:
                for sym in ["NIFTY", "BANKNIFTY"]:
                    try:
                        chain = await loop.run_in_executor(None, fetch_live_snapshot, sym)
                        if chain:
                            message = {
                                "type": "OPTION_CHAIN_UPDATE",
                                "timestamp": int(time.time() * 1000),
                                "data": {
                                    "symbol": sym,
                                    "chain": chain
                                }
                            }
                            await self.send_message(message)
                    except Exception as e:
                        print(f"[OCR ERROR] {sym}: {e}")

            await asyncio.sleep(60) # Update chain every 60 seconds

    async def connect_and_run(self):
        """
        Main loop to manage connection and run data publishing tasks.
        Includes exponential backoff for reconnection attempts.
        """
        backoff_delay = 1
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    self.websocket = websocket
                    self.connection_established.set()
                    print(f"Connected to SOS Engine at {self.uri}")
                    backoff_delay = 1  # Reset delay on successful connection

                    # These tasks will run until one of them fails (e.g., connection drops)
                    await asyncio.gather(
                        self.publish_candles(),
                        self.publish_sentiment_update()
                        # TODO: Enable when Core Engine supports option chain data
                        # self.publish_option_chain()
                    )
            except (websockets.exceptions.ConnectionClosedError, OSError) as e:
                print(f"Connection lost: {e}. Reconnecting in {backoff_delay}s...")
                self.websocket = None
                self.connection_established.clear()
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 2, 60) # Cap at 60s
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                # Potentially add more specific error handling here
                await asyncio.sleep(5) # Wait before retrying on general errors

    def run(self):
        """Entry point."""
        try:
            asyncio.run(self.connect_and_run())
        except KeyboardInterrupt:
            print("\nShutting down client.")
        except Exception as e:
            print(f"Fatal error in run: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SOS Engine Data Bridge Client")
    parser.add_argument('--host', type=str, default='localhost', help='WebSocket host of the SOS Engine')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket port of the SOS Engine')
    args = parser.parse_args()

    client = SOSDataBridgeClient(SYMBOLS, host=args.host, port=args.port)
    client.run()
