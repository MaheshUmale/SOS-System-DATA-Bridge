"""
SymbolMaster - Centralized Instrument Key Resolution

This singleton class provides a unified interface for resolving instrument symbols
across different data providers (TradingView, NSE, Upstox).

Key Features:
- Downloads and caches Upstox NSE instrument master (8,792+ instruments)
- Bidirectional mapping: Symbol ↔ Instrument Key
- Special handling for index instruments (NIFTY, BANKNIFTY)

Usage:
    from SymbolMaster import MASTER

    MASTER.initialize()  # Downloads instrument master (one-time)

    # Resolve symbol to Upstox key
    key = MASTER.get_upstox_key("RELIANCE")  # Returns: NSE_EQ|INE002A01018

    # Reverse lookup
    symbol = MASTER.get_ticker_from_key(key)  # Returns: RELIANCE

Architecture:
    - Singleton pattern ensures single download per session
    - Filters for NSE_EQ and NSE_INDEX segments only
    - Caches mappings in-memory for O(1) lookups

Author: Mahesh
Version: 1.0
"""

import sqlite3
import requests
import gzip
import io
import pandas as pd
import os
import time

class SymbolMaster:
    _instance = None
    _mappings = {} # { "RELIANCE": "NSE_EQ|INE002A01018" }
    _reverse_mappings = {} # { "NSE_EQ|INE002A01018": "RELIANCE" }
    _initialized = False
    _db_path = "sos_unified.db"

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(SymbolMaster, cls).__new__(cls)
        return cls._instance

    def _get_db_connection(self):
        """Establishes a connection to the unified SQLite database."""
        conn = sqlite3.connect(self._db_path)
        return conn

    def initialize(self):
        """
        Loads instrument keys from the unified database. If the database is empty or stale,
        it fetches fresh data from the Upstox API and populates the database.
        """
        if self._initialized:
            return

        print("[SymbolMaster] Initializing Instrument Keys from Unified DB...")
        
        # 1. Try to load from the unified DB
        try:
            conn = self._get_db_connection()
            # Check if the table has data and when it was last updated.
            # A simple way is to check the file modification time.
            db_file_age_seconds = time.time() - os.path.getmtime(self._db_path) if os.path.exists(self._db_path) else float('inf')

            # If DB file is recent (less than 24 hours old), try to load from it
            if db_file_age_seconds < (24 * 60 * 60):
                df_cache = pd.read_sql_query("SELECT * FROM instrument_master", conn)
                if not df_cache.empty:
                    print(f"  [INFO] Loading from recent SQLite cache: {self._db_path}")
                    self._populate_mappings_from_df(df_cache)
                    conn.close()
                    print(f"  ✓ Loaded {len(self._mappings)} keys from SQLite.")
                    self._initialized = True
                    return
            conn.close()
        except Exception as e:
            print(f"  [WARN] Pre-check or loading from SQLite cache failed: {e}")

        # 2. If loading failed or cache is stale, fetch from network
        content = None
        try:
            print("  [INFO] Fetching fresh instrument master from Upstox...")
            url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            content = response.content
        except Exception as e:
            print(f"  [CRITICAL] Download failed: {e}")
            raise Exception("Failed to download instrument master from source.")

        # 3. Parse and Populate SQLite
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                df = pd.read_json(f)

            df_filtered = df[df['segment'].isin(['NSE_EQ', 'NSE_INDEX', 'NSE_FO'])][['trading_symbol', 'instrument_key', 'segment', 'name']].copy()
            
            # Save to unified SQLite DB
            conn = self._get_db_connection()
            # Use 'replace' to wipe old data and insert the fresh data
            df_filtered.to_sql('instrument_master', conn, if_exists='replace', index=False)
            conn.close()
            print(f"  [INFO] Successfully wrote {len(df_filtered)} instruments to the unified DB.")

            # Populate in-memory mappings
            self._populate_mappings_from_df(df_filtered)

            print(f"  ✓ Parsed and cached {len(self._mappings)} keys to unified DB.")
            self._initialized = True

        except Exception as e:
            print(f"[SymbolMaster] Parsing or DB write failed: {e}")
            raise e

    def _populate_mappings_from_df(self, df):
        """Helper to populate in-memory dicts from a DataFrame."""
        for _, row in df.iterrows():
            name = row['trading_symbol'].upper()
            key = row['instrument_key']
            segment = row['segment']
            self._mappings[name] = key
            self._reverse_mappings[key] = (name, segment)
            if segment == 'NSE_INDEX':
                if row['name'] == "Nifty 50": self._mappings["NIFTY"] = key
                elif row['name'] == "Nifty Bank": self._mappings["BANKNIFTY"] = key

    def get_upstox_key(self, symbol):
        """
        Resolves a trading symbol to its Upstox instrument key.

        Args:
            symbol (str): Trading symbol (e.g., 'RELIANCE', 'NIFTY', 'SBIN')

        Returns:
            str: Upstox instrument key (e.g., 'NSE_EQ|INE002A01018') or None if not found

        Example:
            >>> MASTER.get_upstox_key('RELIANCE')
            'NSE_EQ|INE002A01018'
        """
        if not self._initialized:
            self.initialize()

        # 1. Handle unified format
        s_upper = symbol.upper()
        if s_upper.startswith("NSE|INDEX|"):
            s_upper = s_upper.split('|')[-1]

        # 2. Direct Match
        if s_upper in self._mappings:
            return self._mappings[s_upper]

        return None

    def get_ticker_from_key(self, key):
        """
        Reverse lookup: Upstox instrument key to trading symbol.

        Args:
            key (str): Upstox instrument key (e.g., 'NSE_EQ|INE002A01018')

        Returns:
            str: Trading symbol (unified for indices) or the original key if not found

        Example:
            >>> MASTER.get_ticker_from_key('NSE_INDEX|Nifty 50')
            'NSE|INDEX|NIFTY'
        """
        if not self._initialized:
            self.initialize()
        if key in self._reverse_mappings:
            name, segment = self._reverse_mappings[key]
            if segment == 'NSE_INDEX':
                if name == "Nifty 50":
                    return "NSE|INDEX|NIFTY"
                if name == "NIFTY BANK":
                    return "NSE|INDEX|BANKNIFTY"
            return name

        return key

# Singleton Instance
MASTER = SymbolMaster()
