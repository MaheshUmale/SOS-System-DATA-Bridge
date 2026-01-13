"""
Backfill historical option chain data from Trendlyne SmartOptions API.
This populates a local SQLite database with 1-minute interval historical data.
"""
import requests
import time
import sqlite3
import os
import json
import argparse
from datetime import datetime, timedelta, date


from SymbolMaster import MASTER as SymbolMaster

# Upstox SDK
try:
    import upstox_client
    from upstox_client.rest import ApiException
    import config
    UPSTOX_AVAILABLE = True
except ImportError:
    UPSTOX_AVAILABLE = False
    print("[WARN] Upstox SDK not found. Option Chain will rely on Trendlyne only.")

# ==========================================================================
# 1. DATABASE LAYER (SQLite)
# ==========================================================================
class OptionDatabase:
    def __init__(self, db_path="sos_unified.db"):
        self.db_path = db_path
        # No need for separate master/timeseries DBs, so init methods are simplified.

    def _get_connection(self):
        """Establishes a connection to the unified DB and enables WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def save_snapshot(self, symbol, full_datetime, expiry, aggregates, details):
        """
        Saves a full option chain snapshot to the unified database.
        Timestamps are now Unix timestamps for consistency.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Save Aggregates
            cursor.execute("""INSERT OR REPLACE INTO option_aggregates
                              (symbol, timestamp, expiry, total_call_oi, total_put_oi, pcr)
                              VALUES (?, ?, ?, ?, ?, ?)""",
                           (symbol, int(full_datetime.timestamp()), expiry,
                            aggregates['call_oi'], aggregates['put_oi'], aggregates['pcr']))

            # Save Details (per-strike data)
            # Use a list of tuples for executemany for efficiency
            details_to_insert = [
                (symbol, int(full_datetime.timestamp()), float(strike),
                 d['call_oi'], d['put_oi'], d['call_oi_chg'], d['put_oi_chg'])
                for strike, d in details.items()
            ]

            if details_to_insert:
                cursor.executemany("""INSERT OR REPLACE INTO option_chain_details
                                      (symbol, timestamp, strike, call_oi, put_oi, call_oi_chg, put_oi_chg)
                                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                   details_to_insert)

            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to save snapshot for {symbol} at {full_datetime}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_latest_chain(self, symbol):
        """
        Retrieves the most recent, full option chain for a symbol from the unified DB.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Find the timestamp of the latest entry for the given symbol
            cursor.execute("""SELECT timestamp FROM option_chain_details
                              WHERE symbol=?
                              ORDER BY timestamp DESC LIMIT 1""", (symbol,))
            last_ts_row = cursor.fetchone()
            if not last_ts_row:
                return []

            last_ts = last_ts_row[0]

            # Fetch all strike data for that latest timestamp
            cursor.execute("""SELECT strike, call_oi, put_oi, call_oi_chg, put_oi_chg
                              FROM option_chain_details
                              WHERE symbol=? AND timestamp=?""", (symbol, last_ts))
            rows = cursor.fetchall()

            # Format into the expected list of dictionaries
            return [{
                'strike': r[0], 'call_oi': r[1], 'put_oi': r[2],
                'call_oi_chg': r[3], 'put_oi_chg': r[4]
            } for r in rows]
        except Exception as e:
            print(f"[DB READ ERROR] Could not get latest chain for {symbol}: {e}")
            return []
        finally:
            conn.close()

    # Note: The other methods like save_market_depth, save_breadth, etc. have been removed
    # as they are either not used or will be handled by the new sentiment/market data tables.
    # The pcr_history can be derived from the option_aggregates table if needed.

# Keep a cache to avoid repeated API calls
STOCK_ID_CACHE = {}
EXPIRY_CACHE = {}  # Cache for expiry dates
DB = OptionDatabase()

def get_stock_id_for_symbol(symbol):
    """Automatically lookup Trendlyne stock ID for a given symbol"""
    if symbol in STOCK_ID_CACHE:
        return STOCK_ID_CACHE[symbol]

    search_url = "https://smartoptions.trendlyne.com/phoenix/api/search-contract-stock/"
    params = {'query': symbol.lower()}

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and 'body' in data and 'data' in data['body'] and len(data['body']['data']) > 0:
            # Match strictly or take first
            for item in data['body']['data']:
                if item.get('stock_code', '').upper() == symbol.upper():
                    stock_id = item['stock_id']
                    STOCK_ID_CACHE[symbol] = stock_id
                    return stock_id

            stock_id = data['body']['data'][0]['stock_id']
            STOCK_ID_CACHE[symbol] = stock_id
            return stock_id
        return None
    except Exception as e:
        print(f"[ERROR] Stock Lookup {symbol}: {e}")
        return None

def backfill_from_trendlyne(symbol, stock_id, expiry_date_str, time_snapshot_str):
    """
    Fetch and save historical OI data from Trendlyne for a specific timestamp snapshot.
    This now works with a combined datetime object for accurate DB insertion.
    """
    url = f"https://smartoptions.trendlyne.com/phoenix/api/live-oi-data/"
    params = {
        'stockId': stock_id,
        'expDateList': expiry_date_str,
        'minTime': "09:15",
        'maxTime': time_snapshot_str
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('head', {}).get('status') != '0':
            return False

        body = data.get('body', {})
        oi_data = body.get('oiData', {})
        input_data = body.get('inputData', {})

        # Construct a full datetime object for the snapshot
        trading_date_str = input_data.get('tradingDate', date.today().strftime("%Y-%m-%d"))
        snapshot_datetime = datetime.strptime(f"{trading_date_str} {time_snapshot_str}", "%Y-%m-%d %H:%M")

        expiry = input_data.get('expDateList', [expiry_date_str])[0]

        total_call_oi, total_put_oi = 0, 0
        details = {}

        for strike_str, strike_data in oi_data.items():
            c_oi = int(strike_data.get('callOi', 0))
            p_oi = int(strike_data.get('putOi', 0))
            total_call_oi += c_oi
            total_put_oi += p_oi

            details[strike_str] = {
                'call_oi': c_oi, 'put_oi': p_oi,
                'call_oi_chg': int(strike_data.get('callOiChange', 0)),
                'put_oi_chg': int(strike_data.get('putOiChange', 0))
            }

        if total_call_oi == 0 and total_put_oi == 0:
            return False # No data to save

        pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0
        aggregates = {'call_oi': total_call_oi, 'put_oi': total_put_oi, 'pcr': pcr}

        DB.save_snapshot(symbol, snapshot_datetime, expiry, aggregates, details)
        return True

    except Exception as e:
        print(f"[ERROR] Fetch {symbol} @ {time_snapshot_str}: {e}")
        return False

def fetch_live_snapshot_upstox(symbol):
    """
    Fetches live option chain from Upstox Primary API and saves to the unified DB.
    Returns the latest chain details from the DB upon success.
    """
    if not UPSTOX_AVAILABLE or not hasattr(config, 'ACCESS_TOKEN'):
        return None

    try:
        instrument_key = {"NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank"}.get(symbol)
        if not instrument_key:
            instrument_key = SymbolMaster.get_upstox_key(symbol)

        if not instrument_key: return None

        expiry = EXPIRY_CACHE.get(symbol)
        if not expiry:
            stock_id = get_stock_id_for_symbol(symbol)
            if stock_id:
                try:
                    expiry_url = f"https://smartoptions.trendlyne.com/phoenix/api/fno/get-expiry-dates/?mtype=options&stock_id={stock_id}"
                    resp = requests.get(expiry_url, timeout=5)
                    ex_list = resp.json().get('body', {}).get('expiryDates', [])
                    if ex_list:
                        expiry = ex_list[0]
                        EXPIRY_CACHE[symbol] = expiry
                except Exception: pass

        if not expiry: return None

        configuration = upstox_client.Configuration()
        configuration.access_token = config.ACCESS_TOKEN
        api_client = upstox_client.ApiClient(configuration)
        api_instance = upstox_client.OptionsApi(api_client)
        response = api_instance.get_put_call_option_chain(instrument_key, expiry)

        if not response or not response.data: return None

        total_call_oi, total_put_oi = 0, 0
        details = {}
        snapshot_datetime = datetime.now()

        for item in response.data:
            strike = float(item.strike_price)
            ce, pe = item.call_options.market_data, item.put_options.market_data

            c_oi = int(ce.oi) if ce and ce.oi else 0
            p_oi = int(pe.oi) if pe and pe.oi else 0
            c_prev = int(ce.prev_oi) if ce and ce.prev_oi else 0
            p_prev = int(pe.prev_oi) if pe and pe.prev_oi else 0

            total_call_oi += c_oi
            total_put_oi += p_oi
            details[str(strike)] = {
                'call_oi': c_oi, 'put_oi': p_oi,
                'call_oi_chg': c_oi - c_prev,
                'put_oi_chg': p_oi - p_prev
            }

        if total_call_oi == 0 and total_put_oi == 0: return None

        pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0
        aggregates = {'call_oi': total_call_oi, 'put_oi': total_put_oi, 'pcr': pcr}

        DB.save_snapshot(symbol, snapshot_datetime, expiry, aggregates, details)
        return DB.get_latest_chain(symbol)

    except Exception as e:
        print(f"[UPSTOX OCR FAIL] {symbol}: {e}")
        return None


def fetch_live_snapshot(symbol):

    """
    Fetches live data for symbol, saves to DB, and returns the chain.
    Priority: Upstox -> Trendlyne.
    """
    # 1. Try Upstox Primary
    upstox_chain = fetch_live_snapshot_upstox(symbol)
    if upstox_chain:
        # print(f"[OCR UPDATE] {symbol} via Upstox")
        return upstox_chain

    # 2. Fallback to Trendlyne
    stock_id = get_stock_id_for_symbol(symbol)
    if not stock_id:
        return []

    # Get Expiry (cached)
    expiry = EXPIRY_CACHE.get(symbol)
    # Simple validation: if expiry is in the past, refresh
    if expiry:
        try:
             exp_date = datetime.strptime(expiry, "%Y-%m-%d").date()
             if date.today() > exp_date:
                 expiry = None
        except:
             expiry = None

    if not expiry:
        try:
             expiry_url = f"https://smartoptions.trendlyne.com/phoenix/api/fno/get-expiry-dates/?mtype=options&stock_id={stock_id}"
             resp = requests.get(expiry_url, timeout=5)
             expiry_list = resp.json().get('body', {}).get('expiryDates', [])
             if expiry_list:
                 expiry = expiry_list[0]
                 EXPIRY_CACHE[symbol] = expiry
        except Exception as e:
             print(f"[WARN] Failed to fetch expiry for {symbol}: {e}")
             pass

    if not expiry:
        return DB.get_latest_chain(symbol)

    # Timestamp
    ts = datetime.now().strftime("%H:%M")

    # Fetch and Save
    # This calls the existing backfill logic which SAVES to DB
    success = backfill_from_trendlyne(symbol, stock_id, expiry, ts)

    # Return latest from DB (whether update succeeded or not, we return best available)
    return DB.get_latest_chain(symbol)

def generate_time_intervals(start_time="09:15", end_time="15:30", interval_minutes=1):
    """Generate time strings in HH:MM format with 1-minute default"""
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    current = start
    times = []
    while current <= end:
        times.append(current.strftime("%H:%M"))
        current += timedelta(minutes=interval_minutes)
    return times

def run_backfill(symbols_list=None, test_time=None):
    if not symbols_list:
        symbols_list = ["NIFTY", "BANKNIFTY", "RELIANCE", "SBIN", "HDFCBANK"]

    print("=" * 60)
    print("STARTING TRENDLYNE BACKFILL (LAST 15 MINS)")
    print("=" * 60)

    now = test_time if test_time else datetime.now()

    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    end_time = now
    if now < market_open:
        # If run before market open, don't fetch anything.
        print("Market is not open yet. No backfill will be performed.")
        return
    if now > market_close:
        end_time = market_close

    start_time = end_time - timedelta(minutes=15)
    if start_time < market_open:
        start_time = market_open

    time_slots = generate_time_intervals(start_time=start_time.strftime("%H:%M"),
                                         end_time=end_time.strftime("%H:%M"))
    print(f"Time Slots: {len(time_slots)} ({start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}) | Symbols: {len(symbols_list)}")

    for symbol in symbols_list:
        stock_id = get_stock_id_for_symbol(symbol)
        if not stock_id:
            print(f"[SKIP] No Stock ID for {symbol}")
            continue

        try:
            expiry_url = f"https://smartoptions.trendlyne.com/phoenix/api/fno/get-expiry-dates/?mtype=options&stock_id={stock_id}"
            resp = requests.get(expiry_url, timeout=10)
            expiry_list = resp.json().get('body', {}).get('expiryDates', [])
            if not expiry_list:
                print(f"[SKIP] No Expiry for {symbol}")
                continue

            nearest_expiry = expiry_list[0]
            print(f"Syncing {symbol} | Expiry: {nearest_expiry}...")

            success_count = 0
            for ts_str in time_slots:
                if backfill_from_trendlyne(symbol, stock_id, nearest_expiry, ts_str):
                    success_count += 1
                time.sleep(0.1)  # Small delay to be polite to the API

            print(f"[OK] {symbol}: Captured {success_count}/{len(time_slots)} points")
        except Exception as e:
            print(f"[FAIL] {symbol}: An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trendlyne Data Backfill Script for Unified Database")
    # --full argument is removed as the logic now defaults to a smart 15-min window.
    # Future arguments like --date could be added for historical backfills.
    args = parser.parse_args()

    target_symbols = ["NIFTY", "BANKNIFTY", "RELIANCE"]
    run_backfill(target_symbols)
    print("\n[DB PATH]:", os.path.abspath("sos_unified.db"))
