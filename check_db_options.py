import sqlite3
conn = sqlite3.connect('sos_unified.db')
res = conn.execute("SELECT DISTINCT symbol FROM candles WHERE symbol LIKE '%CE%' OR symbol LIKE '%PE%'").fetchall()
print("Option Symbols Found in Unified DB:", res)
conn.close()
