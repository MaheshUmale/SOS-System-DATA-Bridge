import re
import pandas as pd
import os

# Known gates for extraction
KNOWN_GATES = [
    "STUFF_S", "CRUSH_L", "REBID", "RESET",
    "HITCH_L", "HITCH_S", "CLOUD_L", "CLOUD_S",
    "RUBBER_L", "RUBBER_S", "SNAP_B", "SNAP_S", "BIG_DOG_L", "BIG_DOG_S",
    "VWAP_REC", "VWAP_REJ", "MAGNET",
    "ORB_L", "ORB_S", "LATE_SQ",
    "GAP_GO_L", "GAP_GO_S", "MACD_BASE_L", "MACD_BASE_S",
    "FASHION_L", "FASHION_S", "SECOND_L", "SECOND_S",
    "BACKSIDE_L", "BACKSIDE_S"
]

def get_gate_name(gate_key):
    if not gate_key: return "Unknown"
    for gate in KNOWN_GATES:
        if gate_key.endswith("_" + gate) or gate_key == gate:
            return gate
    return gate_key.split('_')[-1] # Fallback

def analyze_log(log_path):
    if not os.path.exists(log_path):
        print(f"Log file {log_path} not found.")
        return

    signals = []
    executions = []
    exits = []

    # PowerShell redirection uses UTF-16, CMD uses UTF-8 (usually)
    # We try both if needed, but our current file is ASCII/UTF-8
    encoding = 'utf-8'
    with open(log_path, 'rb') as f:
        head = f.read(2)
        if head == b'\xff\xfe': encoding = 'utf-16'

    with open(log_path, 'r', encoding=encoding, errors='ignore') as f:
        for line in f:
            if "[SIGNAL_DATA]" in line:
                m = re.search(r"Gate=(.*?), Symbol=(.*?), Entry=([\d\.]+), SL=([\d\.]+), TP=([\d\.]+)", line)
                if m:
                    signals.append(m.groups())
                else:
                    m = re.search(r"\[SIGNAL_DATA\] Gate=(.*?), Symbol=(.*?), Entry=([\d\.]+), SL=([\d\.]+), TP=([\d\.]+), Score=([\d\.]+), Time=(\d+)", line)
                    if m:
                        signals.append(m.groups()[:5])
            
            if "[EXEC_DATA]" in line:
                m = re.search(r"Side=(.*?), Symbol=(.*?), Qty=(\d+), Price=([\d\.]+), SL=([\d\.]+), TP=([\d\.]+), Gate=(.*)", line)
                if m: executions.append(m.groups())

            if "[EXIT_DATA]" in line:
                m = re.search(r"Side=(.*?), Symbol=(.*?), Price=([\d\.]+), Reason=(.*?), PnL=([\-\d\.]+), Gate=(.*)", line)
                if m: exits.append(m.groups())

    print(f"Summary: {len(signals)} signals, {len(executions)} executions, {len(exits)} exits.")

    if exits:
        df = pd.DataFrame(exits, columns=['Side', 'Symbol', 'Price', 'Reason', 'PnL', 'GateKey'])
        df['PnL'] = df['PnL'].astype(float)
        df['Gate'] = df['GateKey'].apply(get_gate_name)
        
        print("\n" + "="*40)
        print("OVERALL PERFORMANCE")
        print("="*40)
        print(f"Total Trades: {len(df)}")
        print(f"Win Rate:     {(df['PnL'] > 0).mean()*100:.2f}%")
        print(f"Total PnL:    {df['PnL'].sum():.2f}")
        print(f"Avg PnL:      {df['PnL'].mean():.2f}")
        
        print("\nBY STRATEGY (GATE):")
        # Fix for FutureWarning: only select PnL before apply
        def calc_wr(x):
            return (x > 0).mean() * 100
            
        stats = df.groupby('Gate')['PnL'].agg(['count', 'sum', 'mean'])
        stats['Win%'] = df.groupby('Gate')['PnL'].apply(calc_wr)
        print(stats.sort_values('sum', ascending=False))

        print("\nBY EXIT REASON:")
        print(df.groupby('Reason')['PnL'].agg(['count', 'sum', 'mean']))
    else:
        print("No trades closed yet.")

if __name__ == "__main__":
    analyze_log("backtest_java.log")
