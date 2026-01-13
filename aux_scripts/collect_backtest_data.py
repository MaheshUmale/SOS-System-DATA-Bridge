"""
Backtest Data Collection Script

Fetches and stores historical intraday data for backtesting:
1. Upstox: 1-min candles for equities + indices (spot only, no volume for indices)
2. TradingView: 1-min volume data for NIFTY/BANKNIFTY indices
3. Trendlyne: 1-min option chain data for NIFTY/BANKNIFTY

Usage:
    python collect_backtest_data.py --date 2026-01-05
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
import time
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Upstox SDK
import upstox_client
import config

# TradingView
from tradingview_screener import Query, col

# Local modules
from SymbolMaster import MASTER as SymbolMaster
from backfill_trendlyne import run_backfill  # Use existing backfill function

# Symbol list (same as live bridge)
SYMBOLS = [
    'RELIANCE', 'SBIN', 'ADANIENT', 'HDFCBANK', 'ICICIBANK', 
    'INFY', 'TCS', 'BHARTIARTL', 'ITC', 'KOTAKBANK', 
    'HINDUNILVR', 'LT', 'AXISBANK', 'MARUTI', 'SUNPHARMA', 
    'TITAN', 'ULTRACEMCO', 'WIPRO', 'BAJFINANCE', 'ASIANPAINT', 
    'HCLTECH', 'NTPC', 'POWERGRID', 'NIFTY', 'BANKNIFTY'
]

class BacktestDataCollector:
    def __init__(self, target_date):
        self.target_date = target_date  # Format: YYYY-MM-DD  
        self.db_path = "backtest_data.db"
        self._init_db()
        
        # Upstox setup
        self.configuration = upstox_client.Configuration()
        self.configuration.access_token = config.ACCESS_TOKEN
        self.api_client = upstox_client.ApiClient(self.configuration)
        self.history_api = upstox_client.HistoryV3Api(self.api_client)
        
        # Initialize SymbolMaster with retry
        print("[Collector] Initializing SymbolMaster...")
        for i in range(3):
            try:
                SymbolMaster.initialize()
                if SymbolMaster._initialized:
                    print("  ✓ SymbolMaster initialized.")
                    break
            except Exception as e:
                print(f"  [WARN] SymbolMaster init attempt {i+1} failed: {e}")
                time.sleep(2)
        
    def _init_db(self):
        """Create backtest database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Candles table
        cursor.execute('''CREATE TABLE IF NOT EXISTS backtest_candles (
                            symbol TEXT,
                            date TEXT,
                            timestamp TEXT,
                            open REAL,
                            high REAL,
                            low REAL,
                            close REAL,
                            volume INTEGER,
                            source TEXT,
                            PRIMARY KEY (symbol, date, timestamp)
                          )''')
        
        # Metadata table
        cursor.execute('''CREATE TABLE IF NOT EXISTS backtest_metadata (
                            date TEXT PRIMARY KEY,
                            collection_time TEXT,
                            symbols_count INTEGER,
                            candles_count INTEGER,
                            options_count INTEGER,
                            status TEXT
                          )''')
        
        conn.commit()
        conn.close()
        print(f"[DB] Initialized {self.db_path}")
    
    
    def collect_tradingview_indices(self):
        """Collect NIFTY/BANKNIFTY 1-min candles from TradingView with accurate volumes"""
        print(f"\n[1/6] Collecting Index Data from TradingView...")
        
        if not TV_AVAILABLE:
            print("  ⚠️  tvDatafeed not available, skipping")
            return 0
        
        tv = TvDatafeed()
        candles_collected = 0
        
        for symbol in ['NIFTY', 'BANKNIFTY']:
            print(f"  Fetching {symbol} from TradingView...")
            try:
                # Get 1000 1-minute bars (covers full trading day + history)
                df = tv.get_hist(
                    symbol=symbol,
                    exchange='NSE',
                    interval=Interval.in_1_minute,
                    n_bars=1000
                )
                
                if df is None or df.empty:
                    print(f"    ❌ No data for {symbol}")
                    continue
                
                # Filter for target date
                df = df.reset_index()
                df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                df['time'] = pd.to_datetime(df['datetime']).dt.strftime('%H:%M')
                df_target = df[df['date'] == self.target_date]
                
                if df_target.empty:
                    print(f"    ⚠️  No data for {self.target_date}")
                    continue
                
                # Insert into DB
                conn = sqlite3.connect(self.db_path)
                for _, row in df_target.iterrows():
                    conn.execute("""
                        INSERT OR REPLACE INTO backtest_candles 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        row['date'],
                        row['time'],
                        float(row['open']),
                        float(row['high']),
                        float(row['low']),
                        float(row['close']),
                        int(row['volume']),
                        'tradingview'
                    ))
                    candles_collected += 1
                
                conn.commit()
                conn.close()
                
                print(f"    ✅ {len(df_target)} candles (with volume)")
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        return candles_collected
    
    def collect_upstox_candles(self):
        """Fetch 1-min candles from Upstox for all symbols"""
        print(f"\n[1/3] Collecting Upstox Candles for {self.target_date}...")
        
        candles_collected = 0
        
        for symbol in SYMBOLS:
            try:
                u_key = SymbolMaster.get_upstox_key(symbol)
                if not u_key:
                    print(f"  [WARN] No Upstox key for {symbol}, skipping...")
                    continue
                
                # Fetch data
                # Using get_intra_day_candle_data for today as it's more reliable for 1m
                # If target_date is not today, we could use get_historical_candle_data1
                today_str = datetime.now().strftime("%Y-%m-%d")
                
                if self.target_date == today_str:
                    # Verified Signature: (instrument_key, unit="minutes", interval="1")
                    response = self.history_api.get_intra_day_candle_data(u_key, "minutes", "1")
                else:
                    # For past days
                    response = self.history_api.get_historical_candle_data1(
                        instrument_key=u_key,
                        unit="day",
                        interval="1",
                        to_date=self.target_date,
                        from_date=self.target_date
                    )
                
                if not response or not hasattr(response, 'data') or not hasattr(response.data, 'candles'):
                    print(f"  [WARN] No data for {symbol}")
                    continue
                
                candles = response.data.candles
                if not candles:
                    print(f"  [WARN] Empty candles for {symbol}")
                    continue
                
                # Store in DB
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for candle in candles:
                    # Format: [timestamp_iso, open, high, low, close, volume, oi]
                    ts_iso = candle[0]  # e.g., "2026-01-05T09:15:00+05:30"
                    # Extract HH:MM
                    ts_time = datetime.fromisoformat(ts_iso).strftime("%H:%M")
                    
                    cursor.execute("""INSERT OR REPLACE INTO backtest_candles 
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                   (symbol, self.target_date, ts_time,
                                    float(candle[1]),  # open
                                    float(candle[2]),  # high
                                    float(candle[3]),  # low
                                    float(candle[4]),  # close
                                    int(candle[5]) if symbol not in ['NIFTY', 'BANKNIFTY'] else 0,  # volume (0 for indices)
                                    'upstox'))
                
                conn.commit()
                conn.close()
                
                candles_collected += len(candles)
                print(f"  ✓ {symbol}: {len(candles)} candles")
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"  ✗ {symbol}: {e}")
                continue
        
        print(f"\n[Upstox] Total candles collected: {candles_collected}")
        return candles_collected
    
    def collect_tradingview_volumes(self):
        """Fetch 1-min volume data for NIFTY/BANKNIFTY from TradingView"""
        print(f"\n[2/3] Collecting TradingView Volumes for indices...")
        
        volumes_collected = 0
        
        for symbol in ['NIFTY', 'BANKNIFTY']:
            try:
                # Use TradingView   for volume data
                # Note: This might not give minute-level historical, so this is a placeholder
                # In practice, we might need tvdatafeed or accept zero-volume for indices
                # [FIXME] https://github.com/rongardF/tvdatafeed USE This for NIFTY BANKNIFTY 1 minute-level data candles with volume
                print(f"  [INFO] TradingView minute-level history not available via screener")
                print(f"  [FALLBACK] Using zero-volume for {symbol} indices")
                
                # Update existing Upstox candles with volume=0 (already done above)
                volumes_collected += 1
                
            except Exception as e:
                print(f"  ✗ {symbol}: {e}")
        
        print(f"\n[TradingView] Volumes processed: {volumes_collected}")
        return volumes_collected
    
    def collect_trendlyne_options(self):
        """Fetch 1-min option chain data from Trendlyne"""
        print(f"\n[3/3] Collecting Trendlyne Options for {self.target_date}...")
        
        try:
            # Use existing run_backfill infrastructure
            # This automatically stores data in options_data.db
            symbols = ['NIFTY', 'BANKNIFTY']
            
            print(f"  [INFO] Running Trendlyne backfill for {symbols}...")
            run_backfill(symbols)
            
            print(f"  ✓ Trendlyne data stored in options_data.db")
            
            # Count collected snapshots
            import sqlite3
            conn = sqlite3.connect("options_data.db")
            cursor = conn.cursor()
            cursor.execute("""SELECT COUNT(*) FROM option_chain_details 
                              WHERE date=?""", (self.target_date,))
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
                    
        except Exception as e:
            print(f"  ✗ Trendlyne collection failed: {e}")
            return 0
    
    def collect_multi_strike_options(self, num_otm=2):
        """Fetch 1-min candles for ATM ± num_otm strikes for NIFTY/BANKNIFTY"""
        print(f"\n[4/5] Collecting Multi-Strike Options (ATM +/- {num_otm})...")
        
        # Re-initialize SymbolMaster to include NSE_FO
        SymbolMaster.initialize()
        
        # Get all FO instruments
        import gzip, io
        cache_file = "upstox_instruments.json.gz"
        with gzip.open(cache_file, 'rb') as f:
            df_all = pd.read_json(io.BytesIO(f.read()))
        df_fo = df_all[df_all['segment'] == 'NSE_FO']
        
        total_candles = 0
        
        for symbol in ['NIFTY', 'BANKNIFTY']:
            # Get spot price at market open
            conn = sqlite3.connect(self.db_path)
            df_spot = pd.read_sql_query(f"""
                SELECT close FROM backtest_candles 
                WHERE date='{self.target_date}' AND symbol='{symbol}' AND timestamp='09:15'
            """, conn)
            conn.close()
            
            if df_spot.empty:
                print(f"  [WARN] No spot data for {symbol}")
                continue
            
            spot_price = df_spot.iloc[0]['close']
            strike_step = 50 if symbol == 'NIFTY' else 100
            atm_strike = round(spot_price / strike_step) * strike_step
            
            # Generate strike list (ATM +/- num_otm)
            strikes = [atm_strike + (offset * strike_step) for offset in range(-num_otm, num_otm + 1)]
            print(f"  [INFO] {symbol} Spot: {spot_price:.2f} -> Strikes: {strikes}")
            
            # Find contracts
            mask = (df_fo['name'] == symbol) & (df_fo['instrument_type'].isin(['CE', 'PE']))
            df_contracts = df_fo[mask].copy()
            
            if df_contracts.empty:
                print(f"  [WARN] No contracts for {symbol}")
                continue
            
            # Find weekly expiry
            min_expiry = df_contracts['expiry'].min()
            df_weekly = df_contracts[df_contracts['expiry'] == min_expiry]
            
            for strike in strikes:
                df_strike = df_weekly[df_weekly['strike_price'] == float(strike)]
                
                for _, contract in df_strike.iterrows():
                    opt_key = contract['instrument_key']
                    opt_symbol = contract['trading_symbol']
                    
                    print(f"    Fetching {opt_symbol}...")
                    try:
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        if self.target_date == today_str:
                            response = self.history_api.get_intra_day_candle_data(opt_key, "minutes", "1")
                        else:
                            response = self.history_api.get_historical_candle_data1(
                                instrument_key=opt_key, unit="day", interval="1",
                                to_date=self.target_date, from_date=self.target_date
                            )
                        
                        if response and hasattr(response, 'data') and response.data.candles:
                            conn = sqlite3.connect(self.db_path)
                            for c in response.data.candles:
                                ts_time = datetime.fromisoformat(c[0]).strftime("%H:%M")
                                conn.execute("""
                                    INSERT OR REPLACE INTO backtest_candles 
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (opt_symbol, self.target_date, ts_time, 
                                     float(c[1]), float(c[2]), float(c[3]), float(c[4]), 
                                     int(c[5]), 'upstox_opt'))
                            conn.commit()
                            conn.close()
                            total_candles += len(response.data.candles)
                            print(f"      OK: {len(response.data.candles)} candles")
                        
                        time.sleep(1)
                    except Exception as e:
                        print(f"      ERR: {e}")
        
        return total_candles
    
    def collect_upstox_pcr(self):
        """Collect intraday PCR history from Upstox API"""
        print(f"\n[5/5] Collecting Upstox PCR Data...")
        
        import requests
        pcr_points = 0
        
        for symbol, expiry in [('NIFTY', '2026-01-13'), ('BANKNIFTY', '2026-01-27')]:
            url = f"https://service.upstox.com/fno-tools-service/open/v1/options/oi-analysis/pcr/NSE/{symbol}/{expiry}/0"
            
            try:
                response = requests.get(url, timeout=10)
                data = response.json()
                
                if data.get('success') and 'data' in data:
                    pcr_data = data['data'].get('pcrValues', [])
                    
                    if pcr_data:
                        ts_db = f"sos_timeseries_{datetime.now().strftime('%Y_%m')}.db"
                        conn = sqlite3.connect(ts_db)
                        
                        conn.execute("""
                            CREATE TABLE IF NOT EXISTS upstox_pcr_history (
                                symbol TEXT, date TEXT, time TEXT, pcr REAL, spot REAL,
                                PRIMARY KEY (symbol, date, time)
                            )
                        """)
                        
                        for day_data in pcr_data:
                            for point in day_data.get('data', []):
                                conn.execute("""
                                    INSERT OR REPLACE INTO upstox_pcr_history 
                                    VALUES (?, ?, ?, ?, ?)
                                """, (symbol, day_data['date'], point['time'], 
                                     point['pcr'], point['spot']))
                                pcr_points += 1
                        
                        conn.commit()
                        conn.close()
                        print(f"  OK: {symbol} PCR data stored")
                
            except Exception as e:
                print(f"  ERR: {symbol} PCR - {e}")
        
        return pcr_points

        """Fetch 1-min candles for ATM CE/PE for NIFTY/BANKNIFTY"""
        print(f"\n[4/4] Collecting ATM Option Candles for {self.target_date}...")
        
        # 1. Ensure we have Spot prices to find ATM
        conn = sqlite3.connect(self.db_path)
        df_spot = pd.read_sql_query(f"SELECT symbol, close FROM backtest_candles WHERE date='{self.target_date}' AND timestamp='09:15'", conn)
        conn.close()
        
        if df_spot.empty:
            print("  [ERROR] No spot data found at 09:15, cannot resolve ATM strikes.")
            return 0
            
        # Re-initialize SymbolMaster to include NSE_FO
        SymbolMaster.initialize()
        
        # Get all FO instruments once to search
        import gzip, io
        cache_file = "upstox_instruments.json.gz"
        with gzip.open(cache_file, 'rb') as f:
            df_all = pd.read_json(io.BytesIO(f.read()))
        df_fo = df_all[df_all['segment'] == 'NSE_FO']
        
        candles_collected = 0
        for _, row in df_spot.iterrows():
            symbol = row['symbol']
            if symbol not in ['NIFTY', 'BANKNIFTY']: continue
            
            spot_price = row['close']
            strike_step = 50 if symbol == 'NIFTY' else 100
            atm_strike = round(spot_price / strike_step) * strike_step
            
            print(f"  [INFO] {symbol} Spot: {spot_price:.2f} -> ATM Strike: {atm_strike}")
            
            # Find the nearest weekly expiry
            mask = (df_fo['name'] == symbol) & (df_fo['instrument_type'].isin(['CE', 'PE']))
            df_contracts = df_fo[mask].copy()
            
            if df_contracts.empty:
                print(f"  [WARN] No contracts found for {symbol}")
                continue
                
            # Filter for ATM strike
            df_atm = df_contracts[df_contracts['strike_price'] == float(atm_strike)]
            if df_atm.empty:
                print(f"  [WARN] No {atm_strike} strike found for {symbol}")
                continue
            
            # Find earliest expiry (weekly)
            min_expiry = df_atm['expiry'].min()
            df_weekly = df_atm[df_atm['expiry'] == min_expiry]
            
            for _, contract in df_weekly.iterrows():
                opt_key = contract['instrument_key']
                opt_symbol = contract['trading_symbol']
                opt_type = contract['instrument_type'] # CE or PE
                
                print(f"    Fetching {opt_symbol} ({opt_key})...")
                try:
                    # Same logic as equities
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    if self.target_date == today_str:
                        response = self.history_api.get_intra_day_candle_data(opt_key, "minutes", "1")
                    else:
                        response = self.history_api.get_historical_candle_data1(
                            instrument_key=opt_key, unit="day", interval="1",
                            to_date=self.target_date, from_date=self.target_date
                        )
                    
                    if response and hasattr(response, 'data') and response.data.candles:
                        conn = sqlite3.connect(self.db_path)
                        for c in response.data.candles:
                            ts_time = datetime.fromisoformat(c[0]).strftime("%H:%M")
                            conn.execute("INSERT OR REPLACE INTO backtest_candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                        (opt_symbol, self.target_date, ts_time, float(c[1]), float(c[2]), float(c[3]), float(c[4]), int(c[5]), 'upstox_opt'))
                        conn.commit()
                        conn.close()
                        candles_collected += len(response.data.candles)
                        print(f"      ✓ {opt_symbol}: {len(response.data.candles)} candles")
                    time.sleep(1) # Extra rate limiting for options
                except Exception as e:
                    print(f"      ✗ {opt_symbol}: {e}")
                    
        return candles_collected

    def finalize_metadata(self, candles_count, options_count):
        """Store collection metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""INSERT OR REPLACE INTO backtest_metadata 
                          VALUES (?, ?, ?, ?, ?, ?)""",
                       (self.target_date,
                        datetime.now().isoformat(),
                        len(SYMBOLS),
                        candles_count,
                        options_count,
                        'complete'))
        
        conn.commit()
        conn.close()
        print(f"\n[DB] Metadata updated for {self.target_date}")
    
    def run(self):
        """Execute full collection pipeline"""
        print("=" * 60)
        print(f"BACKTEST DATA COLLECTION - {self.target_date}")
        print("=" * 60)
        
        # Step 1: TradingView for indices (with volumes)
        tv_candles = self.collect_tradingview_indices()
        
        # Step 2: Upstox for equities
        candles = self.collect_upstox_candles()
        volumes = self.collect_tradingview_volumes()
        options = self.collect_trendlyne_options()
        
        # STEP 2 ENHANCEMENT: Multi-strike options + PCR
        opt_candles = self.collect_multi_strike_options(num_otm=2)
        pcr_points = self.collect_upstox_pcr()
        
        self.finalize_metadata(tv_candles + candles + opt_candles, options)
        
        print("\n" + "=" * 60)
        print("COLLECTION COMPLETE")
        print("=" * 60)
        print(f"  Indices (TV):      {tv_candles} (with volume)")
        print(f"  Equities/Indices:  {candles}")
        print(f"  Option Candles:    {opt_candles} (multi-strike)")
        print(f"  PCR Data Points:   {pcr_points}")
        print(f"  Sentiment Snaps:   {options}")
        print(f"  Database: {self.db_path}")
        print("=" * 60)

if __name__ == "__main__":
    today_str = datetime.now().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(description="Collect backtest data")
    parser.add_argument('--date', type=str, default=today_str, 
                        help=f'Target date (YYYY-MM-DD), default: {today_str}')
    args = parser.parse_args()
    
    collector = BacktestDataCollector(args.date)
    collector.run()
