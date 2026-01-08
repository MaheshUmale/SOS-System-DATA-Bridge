
import sqlite3
try:
    conn = sqlite3.connect('backtest_data.db')
    cursor = conn.cursor()
    # Check tables first just in case
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    # Try querying dates
    if ('backtest_candles',) in tables: 
        table_name = 'backtest_candles'
        try:
            cursor.execute(f"SELECT DISTINCT date(timestamp/1000, 'unixepoch', 'localtime') as d FROM {table_name} ORDER BY d DESC LIMIT 10")
            print("Available Dates (derived from timestamp):", cursor.fetchall())
        except:
             # Try direct date column if exists
            try:
                cursor.execute(f"SELECT DISTINCT date FROM {table_name} ORDER BY date DESC LIMIT 10")
                print("Available Dates (column):", cursor.fetchall())
            except Exception as e:
                print("Error querying dates:", e)
    conn.close()
except Exception as e:
    print("DB Error:", e)
