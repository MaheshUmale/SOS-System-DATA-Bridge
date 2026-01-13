import json
import os

class StrategyBuilder:
    def __init__(self, pattern_id):
        self.data = {
            "pattern_id": pattern_id,
            "regime_config": {},
            "phases": [],
            "execution": {}
        }

    def set_regime(self, regime_name, allow_entry=True, quantity_mod=1.0, tp_mult=1.0, buffer_atr=0.5):
        """Set configuration for a specific market regime (e.g., BULLISH, SIDEWAYS)"""
        self.data["regime_config"][regime_name] = {
            "allow_entry": allow_entry,
            "quantity_mod": quantity_mod,
            "tp_mult": tp_mult,
            "buffer_atr": buffer_atr
        }
        return self

    def add_phase(self, phase_id, conditions, capture=None, timeout=None):
        """Add a phase to the pattern state machine"""
        if isinstance(conditions, str):
            conditions = [conditions]
            
        phase = {
            "id": phase_id,
            "conditions": conditions
        }
        if capture:
            phase["capture"] = capture
        if timeout:
            phase["timeout"] = timeout
            
        self.data["phases"].append(phase)
        return self

    def set_execution(self, side, entry, sl, tp, option_selection="ATM_CALL"):
        """Define the trade execution logic"""
        self.data["execution"] = {
            "side": side.upper(),
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "option_selection": option_selection
        }
        return self

    def build_json(self):
        """Return the strategy as a formatted JSON string"""
        return json.dumps(self.data, indent=4)

    def save(self, directory="strategies"):
        """Save the strategy to a .json file in the specified directory"""
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        filename = f"{self.data['pattern_id']}.json"
        path = os.path.join(directory, filename)
        
        with open(path, "w") as f:
            f.write(self.build_json())
        
        print(f"✅ Strategy saved to: {path}")

# Example Usage
if __name__ == "__main__":
    # 1. Define a Momentum Long Strategy
    factory = StrategyBuilder("DEMO_MOMENTUM_LONG")
    
    # Configure Regimes
    factory.set_regime("BULLISH", quantity_mod=1.2)
    factory.set_regime("SIDEWAYS", allow_entry=True)
    factory.set_regime("BEARISH", allow_entry=False)
    
    # Define Phases
    factory.add_phase(
        phase_id="SETUP",
        conditions=[
            "vars.screener.rvol > 1.5",
            "volume > moving_avg(history, 20, 'volume')"
        ],
        capture={
            "swing_high": "highest(history, 10, 'high')"
        }
    )
    
    factory.add_phase(
        phase_id="TRIGGER",
        conditions="close > vars.swing_high",
        timeout=10
    )
    
    # Define Execution
    factory.set_execution(
        side="LONG",
        entry="close + 0.5",
        sl="candle.getLow() - candle.getATR()",
        tp="entry + (risk * 2.0)",
        option_selection="OTM_CALL_1"
    )
    
    # Save it
    factory.save()
