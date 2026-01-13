import json
import os
import re

class StrategyCompiler:
    def __init__(self, src_dir="strategy_src", out_dir="strategies"):
        self.src_dir = src_dir
        self.out_dir = out_dir

    def parse_file(self, content):
        strategy = {
            "pattern_id": "",
            "regime_config": {},
            "phases": [],
            "execution": {}
        }
        
        current_section = None
        current_phase = None

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Section detection
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].upper()
                continue

            if current_section == "PATTERN":
                if ":" in line:
                    key, val = [x.strip() for x in line.split(":", 1)]
                    if key.upper() == "ID": strategy["pattern_id"] = val
                    if key.upper() == "SIDE": strategy["execution"]["side"] = val

            elif current_section == "REGIME":
                if ":" in line:
                    regime, params = [x.strip() for x in line.split(":", 1)]
                    config = {"allow_entry": True, "quantity_mod": 1.0, "tp_mult": 1.0, "buffer_atr": 0.5}
                    
                    # Parse params like "quantity=0.5, tp=1.2"
                    for part in params.split(","):
                        if "=" in part:
                            pk, pv = [x.strip() for x in part.split("=", 1)]
                            if pk == "allow": config["allow_entry"] = pv.lower() == "true"
                            if pk == "quantity": config["quantity_mod"] = float(pv)
                            if pk == "tp": config["tp_mult"] = float(pv)
                            if pk == "buffer": config["buffer_atr"] = float(pv)
                    
                    strategy["regime_config"][regime] = config

            elif current_section == "PHASES":
                if line.startswith("NAME:"):
                    if current_phase: strategy["phases"].append(current_phase)
                    current_phase = {"id": line[5:].strip(), "conditions": [], "capture": {}}
                elif line.startswith("CONDITIONS:"):
                    pass # Marker
                elif line.startswith("CAPTURE:"):
                    pass # Marker
                elif line.startswith("TIMEOUT:"):
                    if current_phase: current_phase["timeout"] = int(line[8:].strip())
                elif ":" in line and current_section == "PHASES":
                    # Check if it's a capture key=val
                    if "=" in line and current_phase:
                        ck, cv = [x.strip() for x in line.split("=", 1)]
                        current_phase["capture"][ck] = cv
                    else:
                        # Probably a lone condition or metadata
                        if current_phase: current_phase["conditions"].append(line)
                else:
                    # Multi-line condition accumulation
                    if current_phase:
                        current_phase["conditions"].append(line)

            elif current_section == "EXECUTION":
                if ":" in line:
                    key, val = [x.strip() for x in line.split(":", 1)]
                    if key.upper() == "SIDE": strategy["execution"]["side"] = val
                    if key.upper() == "ENTRY": strategy["execution"]["entry"] = val
                    if key.upper() == "SL": strategy["execution"]["sl"] = val
                    if key.upper() == "TP": strategy["execution"]["tp"] = val
                    if key.upper() == "OPTION": strategy["execution"]["option_selection"] = val

        # Add last phase
        if current_phase: strategy["phases"].append(current_phase)
        
        return strategy

    def compile_all(self):
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        count = 0
        for filename in os.listdir(self.src_dir):
            if filename.endswith(".txt"):
                with open(os.path.join(self.src_dir, filename), "r") as f:
                    content = f.read()
                    try:
                        strategy_json = self.parse_file(content)
                        out_path = os.path.join(self.out_dir, f"{strategy_json['pattern_id']}.json")
                        with open(out_path, "w") as out_f:
                            json.dump(strategy_json, out_f, indent=4)
                        print(f"✅ Compiled: {filename} -> {strategy_json['pattern_id']}.json")
                        count += 1
                    except Exception as e:
                        print(f"❌ Failed to compile {filename}: {str(e)}")
        
        print(f"\n🚀 Total strategies compiled: {count}")

if __name__ == "__main__":
    out_path = "d:/SOS/Scalping-Orchestration-System-SOS-/sos-engine/strategies"
    compiler = StrategyCompiler(out_dir=out_path)
    compiler.compile_all()
