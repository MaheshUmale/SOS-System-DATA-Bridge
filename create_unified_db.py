"""
create_unified_db.py

This script initializes the unified SQLite database for the SOS project.
It creates all the necessary tables for storing instrument master data,
candles, option chain data, and sentiment updates.

Usage:
    python create_unified_db.py
"""

import sqlite3

def create_unified_database(db_path="sos_unified.db"):
    """
    Creates and initializes the unified SQLite database with the new schema.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"Database '{db_path}' created successfully.")

        # Table for Instrument Master Data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS instrument_master (
                trading_symbol TEXT PRIMARY KEY,
                instrument_key TEXT,
                segment TEXT,
                name TEXT
            )
        ''')
        print("Table 'instrument_master' created or already exists.")

        # Table for Candle Data (for all timeframes)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                symbol TEXT,
                timestamp INTEGER,
                interval TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                source TEXT,
                PRIMARY KEY (symbol, timestamp, interval)
            )
        ''')
        print("Table 'candles' created or already exists.")

        # Table for Aggregated Option Chain Data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_aggregates (
                symbol TEXT,
                timestamp INTEGER,
                expiry TEXT,
                total_call_oi INTEGER,
                total_put_oi INTEGER,
                pcr REAL,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        print("Table 'option_aggregates' created or already exists.")

        # Table for Detailed Option Chain Data (per strike)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_chain_details (
                symbol TEXT,
                timestamp INTEGER,
                strike REAL,
                call_oi INTEGER,
                put_oi INTEGER,
                call_oi_chg INTEGER,
                put_oi_chg INTEGER,
                PRIMARY KEY (symbol, timestamp, strike)
            )
        ''')
        print("Table 'option_chain_details' created or already exists.")

        # Table for Sentiment Updates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_updates (
                timestamp INTEGER PRIMARY KEY,
                regime TEXT,
                pcr REAL,
                advances INTEGER,
                declines INTEGER
            )
        ''')
        print("Table 'sentiment_updates' created or already exists.")


        conn.commit()
        print("Database schema created and committed successfully.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_unified_database()
