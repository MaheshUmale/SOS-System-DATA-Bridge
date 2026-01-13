"""
Enhanced Option Data Collector for Backtesting
- Collects ±2 OTM strikes (not just ATM)
- Integrates Upstox PCR API for intraday PCR history
- Uses existing Trendlyne backfill for OI data
"""

import requests
import sqlite3
import pandas as pd
from datetime import datetime
import time
import gzip, io

# Initialize SymbolMaster with NSE_FO
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SymbolMaster import MASTER as SymbolMaster

# Upstox API
import config
import upstox_client
from upstox_client.rest import ApiException

class EnhancedOptionCollector:
    def __init__(self, target_date, access_token):
        self.target_date = target_date
        self.access_token = access_token
        self.db_path = "backtest_data.db"
        
        # Initialize Upstox
        configuration = upstox_client.Configuration()
        configuration.access_token = access_token
        self.history_api = upstox_client.HistoryApi(upstox_client.ApiClient(configuration))
        
        SymbolMaster.initialize()
    
    def collect_multi_strike_options(self, symbol, num_otm=2):
        """
        Collect ATM ± num_otm strikes for given index
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            num_otm: Number of OTM strikes on each side (default 2)
        """
        print(f"\n[Enhanced] Collecting {symbol} options (ATM ± {num_otm} strikes)...")
        
        # 1. Get spot price at 09:15
        conn = sqlite3.connect(self.db_path)
        spot_data = pd.read_sql_query(f"""
            SELECT close FROM backtest_candles 
            WHERE date='{self.target_date}' AND symbol='{symbol}' AND timestamp='09:15'
        """, conn)
        conn.close()
        
        if spot_data.empty:
            print(f"  ❌ No spot data for {symbol} at 09:15")
            return 0
        
        spot_price = spot_data.iloc[0]['close']
        strike_step = 50 if symbol == 'NIFTY' else 100
        atm_strike = round(spot_price / strike_step) * strike_step
        
        print(f"  💹 Spot: {spot_price:.2f} → ATM: {atm_strike}")
        
        # 2. Generate strike list
        strikes = []
        for offset in range(-num_otm, num_otm + 1):
            strikes.append(atm_strike + (offset * strike_step))
        
        print(f"  📊 Collecting strikes: {strikes}")
        
        # 3. Load instrument master
        cache_file = "upstox_instruments.json.gz"
        with gzip.open(cache_file, 'rb') as f:
            df_all = pd.read_json(io.BytesIO(f.read()))
        df_fo = df_all[df_all['segment'] == 'NSE_FO']
        
        # 4. Filter for target symbol and strikes
        mask = (df_fo['name'] == symbol) & (df_fo['instrument_type'].isin(['CE', 'PE']))
        df_contracts = df_fo[mask].copy()
        
        # Find nearest weekly expiry
        min_expiry = df_contracts['expiry'].min()
        df_weekly = df_contracts[df_contracts['expiry'] == min_expiry]
        
        # 5. Fetch candles for each strike
        candles_collected = 0
        for strike in strikes:
            df_strike = df_weekly[df_weekly['strike_price'] == float(strike)]
            
            for _, contract in df_strike.iterrows():
                opt_key = contract['instrument_key']
                opt_symbol = contract['trading_symbol']
                opt_type = contract['instrument_type']
                
                print(f"    Fetching {opt_symbol} ({opt_key})...")
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
                        candles_collected += len(response.data.candles)
                        print(f"      ✅ {len(response.data.candles)} candles")
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    print(f"      ❌ {opt_symbol}: {e}")
        
        print(f"  ✅ Total candles collected for {symbol}: {candles_collected}")
        return candles_collected
    
    def collect_upstox_pcr(self, symbol):
        """
        Collect intraday PCR data from Upstox API
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
        """
        print(f"\n[Upstox PCR] Fetching {symbol}...")
        
        # Determine expiry date
        if symbol == 'NIFTY':
            expiry = '2026-01-13'
        else:  # BANKNIFTY
            expiry = '2026-01-27'
        
        url = f"https://service.upstox.com/fno-tools-service/open/v1/options/oi-analysis/pcr/NSE/{symbol}/{expiry}/0"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('success') and 'data' in data:
                pcr_data = data['data'].get('pcrValues', [])
                
                if not pcr_data:
                    print(f"  ⚠️  No PCR data available")
                    return 0
                
                # Store in timeseries DB
                ts_db_path = f"sos_timeseries_{datetime.now().strftime('%Y_%m')}.db"
                conn = sqlite3.connect(ts_db_path)
                
                # Create table if not exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS upstox_pcr_history (
                        symbol TEXT,
                        date TEXT,
                        time TEXT,
                        pcr REAL,
                        spot REAL,
                        PRIMARY KEY (symbol, date, time)
                    )
                """)
                
                rows_inserted = 0
                for day_data in pcr_data:
                    date = day_data.get('date')
                    for point in day_data.get('data', []):
                        conn.execute("""
                            INSERT OR REPLACE INTO upstox_pcr_history 
                            VALUES (?, ?, ?, ?, ?)
                        """, (symbol, date, point['time'], point['pcr'], point['spot']))
                        rows_inserted += 1
                
                conn.commit()
                conn.close()
                
                print(f"  ✅ Stored {rows_inserted} PCR data points")
                return rows_inserted
            else:
                print(f"  ❌ API returned error: {data}")
                return 0
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return 0

# Usage Example
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Option Data Collector")
    parser.add_argument('--date', type=str, default='2026-01-12', help='Target date (YYYY-MM-DD)')
    parser.add_argument('--otm', type=int, default=2, help='Number of OTM strikes on each side (default 2)')
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"ENHANCED OPTION DATA COLLECTION - {args.date}")
    print("=" * 80)
    
    try:
        collector = EnhancedOptionCollector(args.date, config.ACCESS_TOKEN)
        
        # Collect multi-strike options
        nifty_candles = collector.collect_multi_strike_options('NIFTY', num_otm=args.otm)
        banknifty_candles = collector.collect_multi_strike_options('BANKNIFTY', num_otm=args.otm)
        
        # Collect PCR data
        nifty_pcr = collector.collect_upstox_pcr('NIFTY')
        banknifty_pcr = collector.collect_upstox_pcr('BANKNIFTY')
        
        print("\n" + "=" * 80)
        print("✅ COLLECTION COMPLETE")
        print("=" * 80)
        print(f"Option Candles:")
        print(f"  - NIFTY: {nifty_candles}")
        print(f"  - BANKNIFTY: {banknifty_candles}")
        print(f"PCR Data Points:")
        print(f"  - NIFTY: {nifty_pcr}")
        print(f"  - BANKNIFTY: {banknifty_pcr}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
