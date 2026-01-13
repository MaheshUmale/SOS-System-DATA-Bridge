import sqlite3
import datetime

DB_PATH = "backtest_data.db"
SYMBOL = "SBIN"
DATE = "2026-01-05"

def create_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

def generate_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    start_time = datetime.datetime.strptime("09:15", "%H:%M")
    
    # 20 flat candles to establish low ATR/StDev and history
    base_price = 100.0
    for i in range(25):
        ts = (start_time + datetime.timedelta(minutes=i)).strftime("%H:%M")
        # Tight range: stdev low
        # Price oscillates slightly: 100.0, 100.1, 100.0...
        offset = (i % 2) * 0.1
        price = base_price + offset
        
        # open, high, low, close, volume
        # Volume 1000 avg
        cursor.execute("INSERT OR REPLACE INTO backtest_candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (SYMBOL, DATE, ts, price, price+0.2, price-0.1, price, 1000, 'synthetic'))
    
    # Breakout candle at 09:40 (i=25)
    # Triggers SCREENER_MOMENTUM_LONG:
    # 1. screener.rvol > 2.0 (Mocked by Java as 3.0 if missing)
    # 2. screener.change_from_open > 1.0 (Mocked by Java as 2.5 if missing)
    # 3. close > range_max (Range max ~100.2, Close 104.0)
    # 4. volume > moving_avg(20) * 2.5 (MA ~1000, Volume 5000 > 2500)
    
    ts_breakout = (start_time + datetime.timedelta(minutes=25)).strftime("%H:%M") # 09:40
    print(f"Inserting breakout at {ts_breakout}")
    
    cursor.execute("INSERT OR REPLACE INTO backtest_candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (SYMBOL, DATE, ts_breakout, 100.0, 105.0, 100.0, 104.0, 5000, 'synthetic'))

    conn.commit()
    conn.close()
    print(f"Generated synthetic data for {SYMBOL} at {DATE}")

if __name__ == "__main__":
    create_db()
    generate_data()
