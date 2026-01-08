import os

# Read the file and print lines to see if they are actually wrapped
with open("backtest_java.log", "r", encoding="utf-16", errors="ignore") as f:
    for i in range(1500):
        line = f.readline()
        if "SCALP SIGNAL" in line or "Entry:" in line:
            print(f"L{i}: {repr(line)}")
