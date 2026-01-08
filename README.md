# SOS-System-DATA-Bridge
python data bridge for Scalping-Orchestration-System-SOS-


Extend the existing logic to enhance:


This expanded TRD provides an exhaustive technical breakdown of the **Scalping Orchestration System (SOS)**. It incorporates your specific requirements for **TradingView Screener integration**, **Trendlyne SmartOptions backfill**, and direct **NSE Data** processing.

---

# **1. System Architecture: The "Screener-Triggered" Model**

Instead of brute-force fetching data for 5000+ stocks, we use a **Funnel Architecture**.

1. **Level 1 (The Funnel):** Python Bridge runs a continuous `TradingView-Screener` query.
2. **Level 2 (The Trigger):** When a stock hits specific "In-Play" criteria (e.g., `RVOL > 2.0` and `ADX > 25`), it is promoted to the **Active Watchlist**.
3. **Level 3 (The Deep Dive):** For Active Watchlist symbols, the Bridge immediately initiates high-speed fetches from **Upstox** (Candles) and **SmartOptions** (OI Context).
4. **Level 4 (The Execution):** Normalized data is pushed to the **Java LMAX Disruptor** for sub-millisecond signal processing.

---

# **2. Backend Data Bridge: Detailed Component Breakdown**

### **A. TradingView-Screener Logic (`screener_manager.py`)**

Using the `tradingview-screener` library, we define "Global Filters" to identify stocks in play.

* **Fields Used:** `relative_volume_10d_calc` (RVOL), `change_from_open`, `ADX`, `ATR`, and `MACD.macd|5` (5-min MACD).
* **Logic:** * Query runs every 10–30 seconds.
* Example Filter: `(Query().where(col('relative_volume_10d_calc') > 2, col('change') > 1).get_scanner_data())`.
* **Result:** A list of symbols that are "active." This list is passed to the `DataOrchestrator`.



### **B. Trendlyne SmartOptions Integration (`smart_options_client.py`)**

This service handles the historical context for Options.

* **Feature:** Backfill historical OI, Max Pain, and Put-Call Ratio (PCR) from Trendlyne's SmartOptions endpoint.
* **Usage:** When the Java Engine restarts, it calls this service to fetch the "Morning State" (9:15 AM to current time) of the Option Chain to reconstruct "OI Walls."

### **C. Direct NSE & Upstox Ingestion (`live_feed_manager.py`)**

* **Index Data (NSE):** Direct JSON fetch for NIFTY/BANKNIFTY PCR and Market Breadth (Adv/Dec).
* **Stock Data (Upstox):** WebSocket-based candle snapshots for "Active Watchlist" stocks only.

---

# **3. Interface Contracts (The "Source-Agnostic" Schema)**

The Java Engine must not care where data comes from. The Bridge normalizes everything into these JSON contracts.

### **Contract 1: `SCREENER_ALERT` (New)**

Broadcasted when a stock enters/leaves the "In-Play" list.

```json
{
  "type": "SCREENER_ALERT",
  "symbol": "RELIANCE",
  "action": "ADD",
  "metrics": { "rvol": 2.4, "momentum_score": 88, "timeframe": "5m" }
}

```

### **Contract 2: `OPTION_CHAIN_BACKFILL` (Trendlyne Data)**

Used for engine recovery.

```json
{
  "type": "BACKFILL_DATA",
  "symbol": "NIFTY",
  "history": [
    { "ts": 1704711600, "strike": 21500, "ce_oi": 150000, "pe_oi": 45000, "max_pain": 21450 },
    { "ts": 1704711660, "strike": 21500, "ce_oi": 152000, "pe_oi": 46000, "max_pain": 21450 }
  ]
}

```

---

# **4. Persistence & Database Schema (SQLite)**

We use a **Split-Database Strategy** to prevent the "Heavy File" problem.

1. **`sos_master_data.db`**: Stores static data (Symbol tokens, instrument keys).
2. **`sos_timeseries_2026_01.db`**: Monthly partitioned files for price and OI data.

### **Table Detail: `market_depth_history**`

| Column | Type | Detail |
| --- | --- | --- |
| `timestamp` | INTEGER | Epoch (PK) |
| `symbol` | TEXT | E.g., "NIFTY_BANK" (PK) |
| `rvol` | REAL | From TV Screener |
| `pcr` | REAL | From NSE/Trendlyne |
| `adv_dec_ratio` | REAL | From Direct NSE Feed |

---

# **5. Java Engine: LMAX Disruptor Flow**

The Java Engine processes the normalized feed through three specialized handlers.

1. **Context Handler:** Updates the `GlobalMarketMood` (The 7 States) using the `pcr` and `adv_dec_ratio` from the contract.
2. **Pattern Matcher:** * If `SCREENER_ALERT` adds "RELIANCE", the engine instantiates a new `PatternStateMachine` for it.
* If `MARKET_UPDATE` comes in, it evaluates the JSON-based steps (e.g., "Was there a Volume Spike > 2.0?").


3. **Order Orchestrator:**
* Vetoes the trade if `Regime == SIDEWAYS`.
* Dispatches to **Upstox API** using the `instrument_key` mapping provided in the Bridge's initial sync.



---

# **6. Technical Requirements Summary (TRD)**

| Feature | Requirement Detail |
| --- | --- |
| **Concurrency** | LMAX Disruptor Ring Buffer (Size: 1024 events) |
| **Data Integrity** | Cross-verify Upstox prices against TV-Screener `close` values. |
| **Latency Target** | Bridge-to-Execution < 25ms. |
| **Storage** | SQLite in **WAL Mode** with Monthly Sharding. |
| **Recovery** | Mandatory `BACKFILL_DATA` fetch from Trendlyne on startup. |

This refined model ensures that the **Python Bridge** does all the "heavy lifting" (Screening, Sentiment, Historical Buffering), allowing the **Java Engine** to remain a lean, ultra-fast execution machine.

 
