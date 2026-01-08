import re

with open("backtest_java.log", "r", encoding="utf-16", errors="ignore") as f:
    text = f.read()
    print(f"Total characters: {len(text)}")
    print(f"SCALP SIGNAL count: {text.count('SCALP SIGNAL')}")
    print(f"AUTO-EXIT count: {text.count('AUTO-EXIT')}")
