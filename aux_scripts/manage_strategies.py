from strategy_factory import StrategyBuilder
import os

def create_institutional_demand():
    sb = StrategyBuilder("INSTITUTIONAL_DEMAND_LONG")
    sb.set_regime("BULLISH", quantity_mod=1.0)
    sb.set_regime("COMPLETE_BULLISH", quantity_mod=1.5)
    sb.set_regime("COMPLETE_BEARISH", allow_entry=False)
    
    sb.add_phase(
        "DEMAND_SETUP",
        conditions=[
            "volume > (moving_avg(history, 20, 'volume') * 1.5)", # Reduced from 2.5
            "candle.getLow() == lowest(history, 50, 'low')"
        ],
        capture={
            "block_high": "candle.getHigh()",
            "block_low": "candle.getLow()"
        }
    )
    sb.add_phase(
        "RETEST_VALIDATION",
        conditions=[
            "candle.getLow() >= vars.block_low",
            "candle.getLow() <= (vars.block_low + (vars.block_high - vars.block_low) * 0.3)"
        ],
        timeout=15
    )
    sb.add_phase(
        "TRIGGER",
        conditions=[
            "candle.getClose() > vars.block_high",
            "sentiment.breadth_ratio > 1.2" # Reduced from 1.5
        ]
    )
    sb.set_execution(
        side="LONG",
        entry="vars.block_high + 0.5",
        sl="vars.block_low - 2.0",
        tp="entry + ( (entry - sl) * 3.0 )",
        option_selection="ATM_CALL"
    )
    return sb

def create_brf_reversal():
    sb = StrategyBuilder("BRF_SHORT")
    sb.set_regime("SIDEWAYS", quantity_mod=0.5, tp_mult=1.0)
    sb.set_regime("BEARISH", quantity_mod=1.0, tp_mult=2.5)
    sb.set_regime("COMPLETE_BEARISH", quantity_mod=1.2, tp_mult=3.0)
    sb.set_regime("COMPLETE_BULLISH", allow_entry=False)
    
    sb.add_phase(
        "SETUP",
        conditions=["candle.getVolume() > 10000"],
        capture={
            "mother_h": "candle.getHigh()",
            "mother_l": "candle.getLow()"
        }
    )
    sb.add_phase(
        "VALIDATION",
        conditions=["candle.getClose() < vars.mother_l"],
        timeout=5
    )
    sb.add_phase(
        "TRIGGER",
        conditions=[
            "candle.getHigh() < vars.mother_h",
            "candle.getClose() > vars.mother_l"
        ]
    )
    sb.set_execution(
        side="SHORT",
        entry="vars.mother_l - 0.1",
        sl="vars.mother_h",
        tp="entry - (risk * tp_mult)"
    )
    return sb

def create_round_level():
    sb = StrategyBuilder("ROUND_LEVEL_REJECTION_SHORT")
    sb.set_regime("SIDEWAYS", quantity_mod=0.5, buffer_atr=0.3)
    sb.set_regime("BEARISH", quantity_mod=1.0, buffer_atr=0.5)
    sb.set_regime("COMPLETE_BEARISH", quantity_mod=1.2, buffer_atr=0.7)
    sb.set_regime("COMPLETE_BULLISH", allow_entry=False)
    
    sb.add_phase(
        "PROXIMITY_SETUP",
        conditions=[
            "abs(candle.getClose() - round(candle.getClose(), -2)) < 50", # Increased from 25
            "sentiment.pcr_velocity <= 0"
        ],
        capture={
            "round_level": "round(candle.getClose(), -2)",
            "upper_bound": "vars.round_level + (candle.getATR() * regime.buffer_atr)"
        }
    )
    sb.add_phase(
        "REJECTION_VALIDATION",
        conditions=[
            "candle.getHigh() <= vars.upper_bound",
            "candle.getClose() < candle.getOpen()",
            "sentiment.ce_oi_change >= sentiment.pe_oi_change"
        ],
        timeout=5 # Increased from 3
    )
    sb.add_phase(
        "TRIGGER",
        conditions=["candle.getClose() < prev_candle.getLow()"]
    )
    sb.set_execution(
        side="SHORT",
        entry="prev_candle.getLow() - 0.5",
        sl="vars.upper_bound",
        tp="entry - ( (sl - entry) * 2.5 )",
        option_selection="ATM_PUT"
    )
    return sb

def create_screener_momentum():
    sb = StrategyBuilder("SCREENER_MOMENTUM_LONG")
    sb.set_regime("SIDEWAYS", allow_entry=True)
    sb.set_regime("BULLISH", quantity_mod=1.0)
    
    sb.add_phase(
        "SCREENER_SYNC",
        conditions=[
            "vars.screener.rvol > 1.2", # Loosened
            "vars.screener.change_from_open > 0.3" # Loosened
        ]
    )
    sb.add_phase(
        "CONSOLIDATION_VALIDATION",
        conditions=["stdev(history, 5, 'close') < (candle.getATR() * 1.0)"], # Loosened from 0.2
        capture={"range_max": "highest(history, 5, 'high')"}
    )
    sb.add_phase(
        "TRIGGER",
        conditions=[
            "candle.getClose() > vars.range_max",
            "candle.getVolume() > prev_candle.getVolume()"
        ]
    )
    sb.set_execution(
        side="LONG",
        entry="candle.getClose()",
        sl="candle.getLow()",
        tp="entry + ( (entry - sl) * 2.0 )",
        option_selection="OTM_CALL_1"
    )
    return sb

if __name__ == "__main__":
    # Target directory for strategies
    TARGET_DIR = "d:/SOS/Scalping-Orchestration-System-SOS-/sos-engine/strategies"
    
    strategies = [
        create_institutional_demand(),
        create_brf_reversal(),
        create_round_level(),
        create_screener_momentum()
    ]
    
    for s in strategies:
        s.save(TARGET_DIR)
        
    print("\n🚀 All strategies updated and synchronized!")
