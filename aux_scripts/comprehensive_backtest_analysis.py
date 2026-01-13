"""
Comprehensive Backtest Analysis for Jan 12, 2026
Analyzes option trading performance with detailed metrics and recommendations
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

class BacktestAnalyzer:
    def __init__(self, db_path='backtest_data.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
    
    def analyze_market_conditions(self):
        """Analyze overall market behavior on Jan 12"""
        print("=" * 80)
        print("MARKET CONDITIONS ANALYSIS - January 12, 2026")
        print("=" * 80)
        
        # NIFTY analysis
        df_nifty = pd.read_sql_query("""
            SELECT timestamp, open, high, low, close, volume
            FROM backtest_candles
            WHERE date='2026-01-12' AND symbol='NIFTY'
            ORDER BY timestamp
        """, self.conn)
        
        # BANKNIFTY analysis
        df_bn = pd.read_sql_query("""
            SELECT timestamp, open, high, low, close, volume
            FROM backtest_candles
            WHERE date='2026-01-12' AND symbol='BANKNIFTY'
            ORDER BY timestamp
        """, self.conn)
        
        print("\n📊 NIFTY 50")
        print("-" * 80)
        if not df_nifty.empty:
            print(f"  Open:    {df_nifty.iloc[0]['open']:.2f}")
            print(f"  High:    {df_nifty['high'].max():.2f}")
            print(f"  Low:     {df_nifty['low'].min():.2f}")
            print(f"  Close:   {df_nifty.iloc[-1]['close']:.2f}")
            
            day_change = df_nifty.iloc[-1]['close'] - df_nifty.iloc[0]['open']
            day_change_pct = (day_change / df_nifty.iloc[0]['open']) * 100
            print(f"  Change:  {day_change:+.2f} ({day_change_pct:+.2f}%)")
            print(f"  Range:   {df_nifty['high'].max() - df_nifty['low'].min():.2f} points")
            
            # Identify trend
            sma20 = df_nifty['close'].rolling(20).mean().iloc[-1]
            current = df_nifty.iloc[-1 ]['close']
            trend = "BULLISH" if current > sma20 else "BEARISH"
            print(f"  Trend:   {trend} (Close vs SMA20: {current:.2f} vs {sma20:.2f})")
        
        print("\n📊 BANKNIFTY")
        print("-" * 80)
        if not df_bn.empty:
            print(f"  Open:    {df_bn.iloc[0]['open']:.2f}")
            print(f"  High:    {df_bn['high'].max():.2f}")
            print(f"  Low:     {df_bn['low'].min():.2f}")
            print(f"  Close:   {df_bn.iloc[-1]['close']:.2f}")
            
            day_change = df_bn.iloc[-1]['close'] - df_bn.iloc[0]['open']
            day_change_pct = (day_change / df_bn.iloc[0]['open']) * 100
            print(f"  Change:  {day_change:+.2f} ({day_change_pct:+.2f}%)")
            print(f"  Range:   {df_bn['high'].max() - df_bn['low'].min():.2f} points")
            
            sma20 = df_bn['close'].rolling(20).mean().iloc[-1]
            current = df_bn.iloc[-1]['close']
            trend = "BULLISH" if current > sma20 else "BEARISH"
            print(f"  Trend:   {trend} (Close vs SMA20: {current:.2f} vs {sma20:.2f})")
        
        return df_nifty, df_bn
    
    def analyze_pcr_sentiment(self):
        """Analyze PCR data for market sentiment"""
        print("\n" + "=" * 80)
        print("PCR SENTIMENT ANALYSIS")
        print("=" * 80)
        
        ts_db = f"sos_timeseries_{datetime.now().strftime('%Y_%m')}.db"
        try:
            conn_ts = sqlite3.connect(ts_db)
            
            for symbol in ['NIFTY', 'BANKNIFTY']:
                df_pcr = pd.read_sql_query(f"""
                    SELECT time, pcr, spot
                    FROM upstox_pcr_history
                    WHERE symbol='{symbol}' AND date='2026-01-12'
                    ORDER BY time
                """, conn_ts)
                
                if not df_pcr.empty:
                    print(f"\n📈 {symbol} PCR")
                    print("-" * 80)
                    print(f"  Open PCR:  {df_pcr.iloc[0]['pcr']:.4f}")
                    print(f"  Close PCR: {df_pcr.iloc[-1]['pcr']:.4f}")
                    print(f"  Avg PCR:   {df_pcr['pcr'].mean():.4f}")
                    print(f"  Max PCR:   {df_pcr['pcr'].max():.4f} @ {df_pcr.loc[df_pcr['pcr'].idxmax(), 'time']}")
                    print(f"  Min PCR:   {df_pcr['pcr'].min():.4f} @ {df_pcr.loc[df_pcr['pcr'].idxmin(), 'time']}")
                    
                    # Sentiment interpretation
                    avg_pcr = df_pcr['pcr'].mean()
                    if avg_pcr > 1.0:
                        sentiment = "BEARISH (Put-heavy)"
                    elif avg_pcr > 0.7:
                        sentiment = "NEUTRAL"
                    else:
                        sentiment = "BULLISH (Call-heavy)"
                    print(f"  Sentiment: {sentiment}")
            
            conn_ts.close()
        except Exception as e:
            print(f"  ⚠️  PCR data not available: {e}")
    
    def simulate_option_trades(self):
        """Simulate option trades based on INDEX_BREAKOUT_LONG logic"""
        print("\n" + "=" * 80)
        print("SIMULATED OPTION TRADES (INDEX_BREAKOUT_LONG Strategy)")
        print("=" * 80)
        
        trades = []
        trade_id = 1
        
        for symbol in ['NIFTY', 'BANKNIFTY']:
            # Get underlying candles
            df_idx = pd.read_sql_query(f"""
                SELECT timestamp, open, high, low, close, volume
                FROM backtest_candles
                WHERE date='2026-01-12' AND symbol='{symbol}'
                ORDER BY timestamp
            """, self.conn)
            
            if df_idx.empty:
                continue
            
            # Calculate EMA20
            df_idx['ema20'] = df_idx['close'].ewm(span=20, adjust=False).mean()
            df_idx['vol_avg'] = df_idx['volume'].rolling(20).mean()
            
            # Identify breakout signals
            for i in range(20, len(df_idx)):
                row = df_idx.iloc[i]
                
                # INDEX_BREAKOUT_LONG conditions:
                # 1. Close > EMA20
                # 2. Volume > Avg Volume * 1.2
                # 3. Bullish candle (close > open)
                
                if (row['close'] > row['ema20'] and 
                    row['volume'] > row['vol_avg'] * 1.2 and
                    row['close'] > row['open']):
                    
                    # Resolve to ATM option
                    strike_step = 50 if symbol == 'NIFTY' else 100
                    atm_strike = round(row['close'] / strike_step) * strike_step
                    
                    expiry = '13 JAN 26' if symbol == 'NIFTY' else '27 JAN 26'
                    option_symbol = f"{symbol} {atm_strike} CE {expiry}"
                    
                    # Get option data
                    df_opt = pd.read_sql_query(f"""
                        SELECT timestamp, close
                        FROM backtest_candles
                        WHERE date='2026-01-12' AND symbol='{option_symbol}'
                        ORDER BY timestamp
                    """, self.conn)
                    
                    if not df_opt.empty:
                        # Entry at signal time
                        entry_opt = df_opt[df_opt['timestamp'] >= row['timestamp']]
                        if len(entry_opt) > 0:
                            entry_price = entry_opt.iloc[0]['close']
                            entry_time = entry_opt.iloc[0]['timestamp']
                            
                            # SL/TP based on INDEX_BREAKOUT_LONG
                            # SL: Entry - (Entry - Low) * 0.5
                            # TP: Entry + (SL distance * 2.5)
                            sl_distance = (entry_price - row['low']) * 0.5
                            sl_price = entry_price - sl_distance
                            tp_price = entry_price + (sl_distance * 2.5)
                            
                            # Exit logic (check next 10 candles)
                            exit_idx = min(len(entry_opt), 10)
                            exit_candle = entry_opt.iloc[exit_idx-1] if exit_idx > 0 else entry_opt.iloc[-1]
                            exit_price = exit_candle['close']
                            exit_time = exit_candle['timestamp']
                            exit_reason = 'TIME_EXIT'
                            
                            # Check for SL/TP in range
                            for j in range(1, min(exit_idx, len(entry_opt))):
                                check_price = entry_opt.iloc[j]['close']
                                if check_price <= sl_price:
                                    exit_price = sl_price
                                    exit_time = entry_opt.iloc[j]['timestamp']
                                    exit_reason = 'SL_HIT'
                                    break
                                elif check_price >= tp_price:
                                    exit_price = tp_price
                                    exit_time = entry_opt.iloc[j]['timestamp']
                                    exit_reason = 'TP_HIT'
                                    break
                            
                            pnl = exit_price - entry_price
                            pnl_pct = (pnl / entry_price) * 100
                            
                            trades.append({
                                'trade_id': trade_id,
                                'underlying': symbol,
                                'signal_time': row['timestamp'],
                                'underlying_price': row['close'],
                                'option_symbol': option_symbol,
                                'entry_time': entry_time,
                                'entry_price': entry_price,
                                'sl_price': sl_price,
                                'tp_price': tp_price,
                                'exit_time': exit_time,
                                'exit_price': exit_price,
                                'exit_reason': exit_reason,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct
                            })
                            
                            trade_id += 1
        
        return pd.DataFrame(trades)
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        # Market conditions
        df_nifty, df_bn = self.analyze_market_conditions()
        
        # PCR sentiment
        self.analyze_pcr_sentiment()
        
        # Simulated trades
        df_trades = self.simulate_option_trades()
        
        if df_trades.empty:
            print("\n⚠️  No trades executed (strategy conditions not met)")
            print("\nPossible reasons:")
            print("  - Market in consolidation (no breakouts)")
            print("  - Volume conditions not satisfied")
            print("  - Missing option candle data for resolved strikes")
            return
        
        # Performance metrics
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        
        total_trades = len(df_trades)
        wins = len(df_trades[df_trades['pnl'] > 0])
        losses = len(df_trades[df_trades['pnl'] <= 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = df_trades['pnl'].sum()
        avg_pnl = df_trades['pnl'].mean()
        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if wins > 0 else 0
        avg_loss = df_trades[df_trades['pnl'] <= 0]['pnl'].mean() if losses > 0 else 0
        
        print(f"\n📊 Overall Performance")
        print(f"  Total Trades:     {total_trades}")
        print(f"  Wins:             {wins}")
        print(f"  Losses:           {losses}")
        print(f"  Win Rate:         {win_rate:.1f}%")
        print(f"  Total P&L:        ₹{total_pnl:.2f}")
        print(f"  Avg P&L:          ₹{avg_pnl:.2f}")
        print(f"  Avg Win:          ₹{avg_win:.2f}")
        print(f"  Avg Loss:         ₹{avg_loss:.2f}")
        print(f"  Profit Factor:    {abs(avg_win/avg_loss):.2f}x" if avg_loss != 0 else "  Profit Factor:    N/A")
        
        # Exit analysis
        print(f"\n🚪 Exit Reasons")
        for reason, count in df_trades['exit_reason'].value_counts().items():
            pct = (count / total_trades) * 100
            print(f"  {reason:12s}: {count} ({pct:.1f}%)")
        
        # By underlying
        print(f"\n📈 By Underlying")
        for symbol in ['NIFTY', 'BANKNIFTY']:
            sym_trades = df_trades[df_trades['underlying'] == symbol]
            if len(sym_trades) > 0:
                sym_pnl = sym_trades['pnl'].sum()
                sym_wins = len(sym_trades[sym_trades['pnl'] > 0])
                sym_wr = (sym_wins / len(sym_trades) * 100)
                print(f"  {symbol:10s}: {len(sym_trades)} trades | ₹{sym_pnl:+.2f} | WR: {sym_wr:.1f}%")
        
        # Trade details
        print(f"\n" + "=" * 80)
        print("TOP 5 BEST TRADES")
        print("=" * 80)
        top5 = df_trades.nlargest(5, 'pnl')[['trade_id', 'option_symbol', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']]
        print(top5.to_string(index=False))
        
        print(f"\n" + "=" * 80)
        print("TOP 5 WORST TRADES")
        print("=" * 80)
        worst5 = df_trades.nsmallest(5, 'pnl')[['trade_id', 'option_symbol', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']]
        print(worst5.to_string(index=False))
        
        # Save to CSV  
        csv_path = 'd:/SOS/Scalping-Orchestration-System-SOS-/sos-engine/backtest_jan12_detailed.csv'
        df_trades.to_csv(csv_path, index=False)
        print(f"\n✅ Detailed report saved: {csv_path}")
        
        # Recommendations
        print(f"\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        
        if win_rate < 50:
            print("  ⚠️  Win rate below 50%:")
            print("     - Consider tightening entry filters (e.g., require confirmed EMA crossover)")
            print("     - Add momentum confirmation (RSI > 50 or MACD positive)")
        
        if avg_loss < avg_win * -0.5:
            print("  ⚠️  Average loss too large relative to wins:")
            print("     - Consider tigherSL (e.g., 1.0x instead of 1.5x)")
            print("     - Use trailing SL after 50% TP achieved")
        
        tp_rate = len(df_trades[df_trades['exit_reason'] == 'TP_HIT']) / total_trades * 100 if total_trades > 0 else 0
        if tp_rate < 30:
            print("  ⚠️  Low TP hit rate:")
            print("     - Consider reducing TP multiplier (2.0x instead of 2.5x)")
            print("     - Partial profit booking at 1.5x risk")
        
        print(f"\n{'=' * 80}")

if __name__ == "__main__":
    analyzer = BacktestAnalyzer()
    analyzer.generate_report()
