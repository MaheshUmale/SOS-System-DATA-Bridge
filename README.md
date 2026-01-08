# SOS-System-DATA-Bridge
python data bridge for Scalping-Orchestration-System-SOS-


Extend the existing logic to enhance:

This expanded TRD provides an exhaustive technical breakdown of the Scalping Orchestration System (SOS). It incorporates your specific requirements for TradingView Screener integration, Trendlyne SmartOptions backfill, and direct NSE Data processing.

1. System Architecture: The "Screener-Triggered" Model
Instead of brute-force fetching data for 5000+ stocks, we use a Funnel Architecture.

Level 1 (The Funnel): Python Bridge runs a continuous TradingView-Screener query.

Level 2 (The Trigger): When a stock hits specific "In-Play" criteria (e.g., RVOL > 2.0 and ADX > 25), it is promoted to the Active Watchlist.

Level 3 (The Deep Dive): For Active Watchlist symbols, the Bridge immediately initiates high-speed fetches from Upstox (Candles) and SmartOptions (OI Context).

Level 4 (The Execution): Normalized data is pushed to the Java LMAX Disruptor for sub-millisecond signal processing.

2. Backend Data Bridge: Detailed Component Breakdown
A. TradingView-Screener Logic (screener_manager.py)
Using the tradingview-screener library, we define "Global Filters" to identify stocks in play.

Fields Used: relative_volume_10d_calc (RVOL), change_from_open, ADX, ATR, and MACD.macd|5 (5-min MACD).

Logic: * Query runs every 10–30 seconds.

Example Filter: (Query().where(col('relative_volume_10d_calc') > 2, col('change') > 1).get_scanner_data()).

Result: A list of symbols that are "active." This list is passed to the DataOrchestrator.

B. Trendlyne SmartOptions Integration (smart_options_client.py)
This service handles the historical context for Options.

Feature: Backfill historical OI, Max Pain, and Put-Call Ratio (PCR) from Trendlyne's SmartOptions endpoint.

Usage: When the Java Engine restarts, it calls this service to fetch the "Morning State" (9:15 AM to current time) of the Option Chain to reconstruct "OI Walls."

C. Direct NSE & Upstox Ingestion (live_feed_manager.py)
Index Data (NSE): Direct JSON fetch for NIFTY/BANKNIFTY PCR and Market Breadth (Adv/Dec).

Stock Data (Upstox): WebSocket-based candle snapshots for "Active Watchlist" stocks only.
