import sqlite3

# Check sos_unified.db for option data coverage
print("=" * 80)
print("SOS_UNIFIED.DB - Option Data Coverage")
print("=" * 80)

try:
    conn = sqlite3.connect('sos_unified.db')
    cursor = conn.cursor()

    # 1. Check for option symbols in the candles table
    print("\n--- Candle Data for Options ---")
    options_in_candles = cursor.execute("""
        SELECT DISTINCT symbol
        FROM candles
        WHERE (symbol LIKE '%CE%' OR symbol LIKE '%PE%')
    """).fetchall()

    if options_in_candles:
        print(f"✅ Found {len(options_in_candles)} unique option contracts with candle data.")
        for opt in options_in_candles:
            count = cursor.execute("SELECT COUNT(*) FROM candles WHERE symbol=?", (opt[0],)).fetchone()[0]
            print(f"  - {opt[0]}: {count} candles")
    else:
        print("❌ No option symbols found in the 'candles' table.")

    # 2. Check for data in the option chain tables
    print("\n--- Option Chain and Aggregates Data ---")
    
    # Check option_aggregates
    cursor.execute("SELECT COUNT(*) FROM option_aggregates")
    aggregates_count = cursor.fetchone()[0]
    if aggregates_count > 0:
        print(f"✅ Found {aggregates_count} rows in 'option_aggregates'.")
        # You could add a breakdown by symbol here if needed
    else:
        print("❌ No data found in 'option_aggregates'.")

    # Check option_chain_details
    cursor.execute("SELECT COUNT(*) FROM option_chain_details")
    details_count = cursor.fetchone()[0]
    if details_count > 0:
        print(f"✅ Found {details_count} rows in 'option_chain_details'.")
    else:
        print("❌ No data found in 'option_chain_details'.")

    conn.close()

except sqlite3.Error as e:
    print(f"❌ Database Error: {e}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
