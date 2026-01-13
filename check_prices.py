import sqlite3
conn = sqlite3.connect('sos_unified.db')
res = conn.execute("SELECT symbol, close FROM candles WHERE symbol='BANKNIFTY' LIMIT 10").fetchall()
print("BANKNIFTY Sample Prices from Unified DB:", res)
res2 = conn.execute("SELECT DISTINCT symbol FROM candles WHERE symbol LIKE '%NIFTY%'").fetchall()
print("Symbols in Unified DB containing NIFTY:", res2)
conn.close()
