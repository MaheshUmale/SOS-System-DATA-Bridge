"""
Option Trading Backtest Report Generator
Demonstrates ATM option selection and PnL tracking for NIFTY/BANKNIFTY
"""

import sqlite3
import pandas as pd
from datetime import datetime

# ATM Option Resolver (Python equivalent of Java OptionContractResolver)
def resolve_atm_option(symbol, spot_price, side):
    """Resolve ATM option contract based on underlying price and signal side"""
    strike_step = 50 if symbol == 'NIFTY' else 100
    atm_strike = round(spot_price / strike_step) * strike_step
    
    option_type = 'CE' if side == 'LONG' else 'PE'
    
    # For Jan 12, 2026 data
    if symbol == 'NIFTY':
        expiry = '13 JAN 26'
    else:  # BANKNIFTY
        expiry = '27 JAN 26'
    
    option_symbol = f"{symbol} {atm_strike} {option_type} {expiry}"
    return option_symbol, atm_strike, option_type

# Load data
conn = sqlite3.connect('d:/SOS/SOS-System-DATA-Bridge/backtest_data.db')

# Get all NIFTY and BANKNIFTY candles
df_indices = pd.read_sql_query("""
    SELECT symbol, timestamp, open, high, low, close, volume 
    FROM backtest_candles 
    WHERE date='2026-01-12' AND symbol IN ('NIFTY', 'BANKNIFTY')
    ORDER BY timestamp ASC
""", conn)

print("=" * 80)
print(f"OPTION TRADING BACKTEST REPORT - January 12, 2026")
print("=" * 80)
print(f"\\nTotal Index Candles: {len(df_indices)}")
print(f"- NIFTY: {len(df_indices[df_indices['symbol']=='NIFTY'])}")
print(f"- BANKNIFTY: {len(df_indices[df_indices['symbol']=='BANKNIFTY'])}")

# Simulate trades: Generate a signal every 30 minutes (alternating LONG/SHORT)
trades = []
trade_id = 1

for symbol in ['NIFTY', 'BANKNIFTY']:
    symbol_data = df_indices[df_indices['symbol'] == symbol].reset_index(drop=True)
    
    # Generate signals every 30 candles (30 mins), alternating sides
    for i in range(0, len(symbol_data), 30):
        if i + 5 >= len(symbol_data):  # Need at least 5 candles for exit
            break
            
        signal_candle = symbol_data.iloc[i]
        side = 'LONG' if (i // 30) % 2 == 0 else 'SHORT'
        
        # Resolve option
        option_symbol, strike, opt_type = resolve_atm_option(
            symbol, signal_candle['close'], side
        )
        
        # Get option candles
        df_option = pd.read_sql_query(f"""
            SELECT timestamp, open, high, low, close 
            FROM backtest_candles 
            WHERE date='2026-01-12' AND symbol='{option_symbol}'
            ORDER BY timestamp ASC
        """, conn)
        
        if df_option.empty:
            print(f"⚠️  No data for {option_symbol}")
            continue
        
        # Entry: First available option candle after signal
        entry_idx = df_option[df_option['timestamp'] >= signal_candle['timestamp']].index
        if len(entry_idx) == 0:
            continue
        
        entry_candle = df_option.iloc[entry_idx[0]]
        entry_price = entry_candle['close']
        entry_time = entry_candle['timestamp']
        
        # Exit after 5 candles or SL/TP hit
        sl_price = entry_price * 0.80  # 20% SL
        tp_price = entry_price * 1.20  # 20% TP
        
        exit_reason = 'TIME_EXIT'
        exit_idx = min(entry_idx[0] + 5, len(df_option) - 1)
        
        # Check for SL/TP in next 5 candles
        for check_idx in range(entry_idx[0] + 1, min(entry_idx[0] + 6, len(df_option))):
            candle = df_option.iloc[check_idx]
            if candle['low'] <= sl_price:
                exit_idx = check_idx
                exit_reason = 'SL_HIT'
                break
            if candle['high'] >= tp_price:
                exit_idx = check_idx
                exit_reason = 'TP_HIT'
                break
        
        exit_candle = df_option.iloc[exit_idx]
        exit_price = exit_candle['close']
        exit_time = exit_candle['timestamp']
        
        # Calculate P&L (always LONG the option)
        pnl = exit_price - entry_price
        pnl_pct = (pnl / entry_price) * 100
        
        trades.append({
            'trade_id': trade_id,
            'underlying': symbol,
            'signal_side': side,
            'option_symbol': option_symbol,
            'strike': strike,
            'option_type': opt_type,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
        
        trade_id += 1

conn.close()

# Generate Report
df_trades = pd.DataFrame(trades)

print(f"\\n" + "=" * 80)
print(f"TRADE EXECUTION SUMMARY")
print("=" * 80)
print(f"Total Trades: {len(df_trades)}")
print(f"NIFTY Trades: {len(df_trades[df_trades['underlying']=='NIFTY'])}")
print(f"BANKNIFTY Trades: {len(df_trades[df_trades['underlying']=='BANKNIFTY'])}")

print(f"\\n" + "-" * 80)
print("OPTION BREAKDOWN")
print("-" * 80)
print(f"CE Trades: {len(df_trades[df_trades['option_type']=='CE'])}")
print(f"PE Trades: {len(df_trades[df_trades['option_type']=='PE'])}")

print(f"\\n" + "-" * 80)
print("EXIT REASONS")
print("-" * 80)
for reason, count in df_trades['exit_reason'].value_counts().items():
    print(f"{reason}: {count}")

print(f"\\n" + "=" * 80)
print("PNL ANALYSIS")
print("=" * 80)

total_pnl = df_trades['pnl'].sum()
wins = len(df_trades[df_trades['pnl'] > 0])
losses = len(df_trades[df_trades['pnl'] <= 0])
win_rate = (wins / len(df_trades) * 100) if len(df_trades) > 0 else 0

print(f"Total P&L: ₹{total_pnl:.2f}")
print(f"Average P&L per Trade: ₹{df_trades['pnl'].mean():.2f}")
print(f"Win Rate: {win_rate:.1f}% ({wins} wins / {losses} losses)")
print(f"Average Winning Trade: ₹{df_trades[df_trades['pnl'] > 0]['pnl'].mean():.2f}")
print(f"Average Losing Trade: ₹{df_trades[df_trades['pnl'] <= 0]['pnl'].mean():.2f}")

print(f"\\n" + "-" * 80)
print("BY UNDERLYING")
print("-" * 80)
for symbol in ['NIFTY', 'BANKNIFTY']:
    trades_sym = df_trades[df_trades['underlying'] == symbol]
    if len(trades_sym) > 0:
        sym_pnl = trades_sym['pnl'].sum()
        sym_wins = len(trades_sym[trades_sym['pnl'] > 0])
        sym_wr = (sym_wins / len(trades_sym) * 100)
        print(f"{symbol}: ₹{sym_pnl:.2f} | {len(trades_sym)} trades | WR: {sym_wr:.1f}%")

print(f"\\n" + "=" * 80)
print("TOP 10 TRADES")
print("=" * 80)
top_trades = df_trades.nlargest(10, 'pnl')[['trade_id', 'option_symbol', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']]
print(top_trades.to_string(index=False))

print(f"\\n" + "=" * 80)
print("BOTTOM 10 TRADES")
print("=" * 80)
bottom_trades = df_trades.nsmallest(10, 'pnl')[['trade_id', 'option_symbol', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']]
print(bottom_trades.to_string(index=False))

# Save detailed report
df_trades.to_csv('d:/SOS/Scalping-Orchestration-System-SOS-/sos-engine/option_backtest_report_jan12.csv', index=False)
print(f"\\n✅ Detailed report saved to: option_backtest_report_jan12.csv")
print("=" * 80)
