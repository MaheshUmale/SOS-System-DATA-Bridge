# SOS Unified Database Schema (`sos_unified.db`)

This document provides a detailed overview of the schema for the `sos_unified.db` SQLite database. This database serves as the single source of truth for all market data used in the Scalping Orchestration System (SOS).

## 1. `instrument_master`

This table stores the master list of all financial instruments, mapping human-readable symbols to the instrument keys used by various APIs.

| Column           | Type    | Description                                                 | Primary Key |
| ---------------- | ------- | ----------------------------------------------------------- | ----------- |
| `trading_symbol` | `TEXT`  | The common trading symbol (e.g., "RELIANCE", "NIFTY").      | Yes         |
| `instrument_key` | `TEXT`  | The unique instrument key from the data provider (e.g., Upstox). | No          |
| `segment`        | `TEXT`  | The market segment (e.g., "NSE_EQ", "NSE_INDEX").         | No          |
| `name`           | `TEXT`  | The full name of the instrument (e.g., "Nifty 50").         | No          |

---

## 2. `candles`

This table stores historical and live candle data for all instruments at various time intervals.

| Column    | Type      | Description                                                 | Primary Key |
| --------- | --------- | ----------------------------------------------------------- | ----------- |
| `symbol`    | `TEXT`    | The trading symbol of the instrument.                       | Yes         |
| `timestamp` | `INTEGER` | The Unix timestamp (in milliseconds) for the candle's open time. | Yes         |
| `interval`  | `TEXT`    | The candle's time interval (e.g., "1m", "5m", "1d").        | Yes         |
| `open`      | `REAL`    | The opening price of the candle.                            | No          |
| `high`      | `REAL`    | The highest price of the candle.                            | No          |
| `low`       | `REAL`    | The lowest price of the candle.                             | No          |
| `close`     | `REAL`    | The closing price of the candle.                            | No          |
| `volume`    | `INTEGER` | The trading volume during the candle's period.              | No          |
| `source`    | `TEXT`    | The source of the data (e.g., "upstox_live", "tv_screener"). | No          |

---

## 3. `option_aggregates`

This table stores high-level, aggregated option chain data for a given instrument at a specific point in time.

| Column          | Type      | Description                                                 | Primary Key |
| --------------- | --------- | ----------------------------------------------------------- | ----------- |
| `symbol`          | `TEXT`    | The underlying symbol for the option chain (e.g., "NIFTY"). | Yes         |
| `timestamp`       | `INTEGER` | The Unix timestamp (in seconds) of the snapshot.            | Yes         |
| `expiry`          | `TEXT`    | The expiry date of the option series (YYYY-MM-DD).          | No          |
| `total_call_oi` | `INTEGER` | The total open interest for all call options.               | No          |
| `total_put_oi`  | `INTEGER` | The total open interest for all put options.                | No          |
| `pcr`             | `REAL`    | The Put-Call Ratio (total_put_oi / total_call_oi).          | No          |

---

## 4. `option_chain_details`

This table stores detailed, strike-by-strike open interest data for a given option chain.

| Column       | Type      | Description                                                 | Primary Key |
| ------------ | --------- | ----------------------------------------------------------- | ----------- |
| `symbol`       | `TEXT`    | The underlying symbol for the option chain.                 | Yes         |
| `timestamp`    | `INTEGER` | The Unix timestamp (in seconds) of the snapshot.            | Yes         |
| `strike`       | `REAL`    | The strike price of the option.                             | Yes         |
| `call_oi`      | `INTEGER` | The open interest for the call option at this strike.       | No          |
| `put_oi`       | `INTEGER` | The open interest for the put option at this strike.        | No          |
| `call_oi_chg`  | `INTEGER` | The change in open interest for the call option.            | No          |
| `put_oi_chg`   | `INTEGER` | The change in open interest for the put option.             | No          |

---

## 5. `sentiment_updates`

This table stores the market sentiment data that is calculated and broadcast by the data bridge.

| Column     | Type      | Description                                                 | Primary Key |
| ---------- | --------- | ----------------------------------------------------------- | ----------- |
| `timestamp`  | `INTEGER` | The Unix timestamp (in milliseconds) of the sentiment snapshot. | Yes         |
| `regime`     | `TEXT`    | The calculated market regime (e.g., "BULLISH", "BEARISH").    | No          |
| `pcr`        | `REAL`    | The Put-Call Ratio of the primary index.                    | No          |
| `advances`   | `INTEGER` | The number of advancing stocks in the market.               | No          |
| `declines`   | `INTEGER` | The number of declining stocks in the market.               | No          |
