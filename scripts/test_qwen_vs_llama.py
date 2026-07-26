import time
import json
import ollama
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Define the exact tool schemas sent to Ollama
OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_building_state",
            "description": "Get current sensor readings for all 5 zones.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_all_setpoints",
            "description": "Queue heating and cooling setpoints for all 5 zones in a single call.",
            "parameters": {
                "type": "object",
                "properties": {
                    "setpoints": {
                        "type": "array",
                        "description": "List of dicts: [{'zone_name': 'SPACE1-1', 'heating_c': 20.5, 'cooling_c': 25.0}, ...]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "zone_name": {"type": "string"},
                                "heating_c": {"type": "number"},
                                "cooling_c": {"type": "number"}
                            },
                            "required": ["zone_name", "heating_c", "cooling_c"]
                        }
                    }
                },
                "required": ["setpoints"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_decision_tool",
            "description": "Persists the LLM reasoning and action to the decisions audit table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sim_time_hours": {"type": "number"},
                    "reasoning": {"type": "string"},
                    "action": {"type": "string"}
                },
                "required": ["sim_time_hours", "reasoning", "action"]
            }
        }
    }
]

# 5 representative test turns
TEST_TURNS = [
    {
        "name": "Turn 1: Winter Occupied Off-Peak (08:00)",
        "hour": 8.0,
        "season": "Winter (Jan 15)",
        "tou": "Off-Peak",
        "mode": "Occupied",
        "price": 0.05,
        "target_htg": 20.5,
        "target_clg": 25.0,
        "row_label": "OCCUPIED | Off-Peak (Winter)"
    },
    {
        "name": "Turn 2: Winter Occupied Peak (14:00)",
        "hour": 14.0,
        "season": "Winter (Jan 15)",
        "tou": "Peak",
        "mode": "Occupied",
        "price": 0.15,
        "target_htg": 19.0,
        "target_clg": 25.0,
        "row_label": "OCCUPIED | Peak (Winter)"
    },
    {
        "name": "Turn 3: Winter Unoccupied Off-Peak (22:00)",
        "hour": 22.0,
        "season": "Winter (Jan 15)",
        "tou": "Off-Peak",
        "mode": "Unoccupied",
        "price": 0.05,
        "target_htg": 16.0,
        "target_clg": 27.0,
        "row_label": "UNOCCUPIED | Any TOU"
    },
    {
        "name": "Turn 4: Summer Occupied Mid-Peak (10:00)",
        "hour": 10.0,
        "season": "Summer (Jul 1)",
        "tou": "Mid-Peak",
        "mode": "Occupied",
        "price": 0.08,
        "target_htg": 16.0,
        "target_clg": 24.5,
        "row_label": "OCCUPIED | Mid-Peak (Summer)"
    },
    {
        "name": "Turn 5: Summer Occupied Peak (16:00)",
        "hour": 16.0,
        "season": "Summer (Jul 1)",
        "tou": "Peak",
        "mode": "Occupied",
        "price": 0.15,
        "target_htg": 16.0,
        "target_clg": 26.0,
        "row_label": "OCCUPIED | Peak (Summer)"
    }
]

def build_system_prompt(turn):
    return f"""You are an autonomous HVAC Building Management System agent controlling a 5-zone commercial office.
ZONES: SPACE1-1, SPACE2-1, SPACE3-1, SPACE4-1, SPACE5-1

CURRENT CONTEXT:
- Simulation Hour : {turn['hour']:.1f}
- Season          : {turn['season']}
- TOU Tier        : {turn['tou']}
- Electricity Price: ${turn['price']:.2f}/kWh
- Occupancy Mode  : {turn['mode']}

CANONICAL DECISION TABLE (SINGLE SOURCE OF TRUTH):
1. UNOCCUPIED | Any TOU -> Heating 16.0°C, Cooling 27.0°C
2. WINTER OCCUPIED | Off-Peak -> Heating 20.5°C, Cooling 25.0°C
3. WINTER OCCUPIED | Mid-Peak -> Heating 20.5°C, Cooling 25.0°C
4. WINTER OCCUPIED | Peak -> Heating 19.0°C, Cooling 25.0°C (Load shed heating)
5. SUMMER OCCUPIED | Off-Peak -> Heating 16.0°C, Cooling 23.5°C
6. SUMMER OCCUPIED | Mid-Peak -> Heating 16.0°C, Cooling 24.5°C
7. SUMMER OCCUPIED | Peak -> Heating 16.0°C, Cooling 26.0°C (Load shed cooling)

CURRENT RECOMMENDED DECISION TABLE ROW FOR THIS TURN:
  {turn['row_label']} -> Heating {turn['target_htg']}°C, Cooling {turn['target_clg']}°C

TOOL CALL SEQUENCE (CRITICAL RULES):
1. set_all_setpoints — MUST ONLY take 'setpoints' parameter (list of [{{'zone_name': '...', 'heating_c': X, 'cooling_c': Y}}]). NEVER pass 'reasoning' or 'action' strings to set_all_setpoints!
2. log_decision_tool — MANDATORY every turn. MUST ONLY take 'reasoning' and 'action' parameters.

CRITICAL INSTRUCTION: Always make formal structured tool calls using your tool API. NEVER output raw markdown JSON strings or text descriptions as a fallback.
"""

def evaluate_model(model_name):
    print(f"\n=======================================================")
    print(f"  EVALUATING MODEL: {model_name}")
    print(f"=======================================================")
    
    total_latency = 0.0
    valid_tool_calls_count = 0
    correct_row_count = 0
    malformed_calls_count = 0
    
    for i, turn in enumerate(TEST_TURNS, 1):
        print(f"\n[Turn {i}/5] {turn['name']}...")
        sys_prompt = build_system_prompt(turn)
        user_prompt = f"Hour {turn['hour']} | {turn['mode']} | {turn['tou']} | {turn['season']}. Apply the correct decision table row for all 5 zones and log your reasoning."
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        t0 = time.time()
        try:
            res = ollama.chat(model=model_name, messages=messages, tools=OLLAMA_TOOLS)
            dt = time.time() - t0
            total_latency += dt
        except Exception as e:
            dt = time.time() - t0
            total_latency += dt
            print(f"  [ERROR] API call failed: {e}")
            malformed_calls_count += 1
            continue
            
        msg = res.get("message", {})
        tool_calls = msg.get("tool_calls", [])
        
        if not tool_calls:
            print(f"  [FAIL] No tool calls emitted! Latency: {dt:.2f}s")
            print(f"         Content: {msg.get('content', '')[:100]}...")
            malformed_calls_count += 1
            continue
            
        print(f"  [OK] Emitted {len(tool_calls)} tool calls in {dt:.2f}s")
        
        # Analyze tool calls
        setpoints_called = False
        log_called = False
        row_accurate = False
        turn_malformed = False
        
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    turn_malformed = True
            
            if name == "set_all_setpoints":
                setpoints_called = True
                sp_list = args.get("setpoints", [])
                if not isinstance(sp_list, list) or len(sp_list) == 0:
                    turn_malformed = True
                else:
                    # Check accuracy against target row
                    match_count = 0
                    for sp in sp_list:
                        if isinstance(sp, dict):
                            h = float(sp.get("heating_c", 0))
                            c = float(sp.get("cooling_c", 0))
                            if abs(h - turn['target_htg']) <= 0.1 and abs(c - turn['target_clg']) <= 0.1:
                                match_count += 1
                    if match_count == 5:
                        row_accurate = True
                    else:
                        print(f"       -> Setpoints mismatch: got {sp_list[:2]}... expected H:{turn['target_htg']}, C:{turn['target_clg']}")
                        
            elif name == "log_decision_tool":
                log_called = True
                if not args.get("reasoning") or not args.get("action"):
                    turn_malformed = True
            elif name != "get_building_state":
                turn_malformed = True
                
        if turn_malformed:
            print(f"  [FAIL] Malformed tool call arguments detected.")
            malformed_calls_count += 1
        elif setpoints_called and log_called:
            valid_tool_calls_count += 1
            if row_accurate:
                correct_row_count += 1
                print(f"  [PERFECT] Both tools called correctly with exact target row setpoints!")
            else:
                print(f"  [PARTIAL] Tools called validly, but table row setpoints were not 100% accurate.")
        else:
            print(f"  [FAIL] Missing required tool call (set_all_setpoints={setpoints_called}, log={log_called}).")
            malformed_calls_count += 1
            
    avg_latency = total_latency / len(TEST_TURNS)
    print(f"\n-------------------------------------------------------")
    print(f"  RESULTS FOR {model_name}:")
    print(f"  - Total Latency         : {total_latency:.2f}s (Avg: {avg_latency:.2f}s/turn)")
    print(f"  - Valid Tool Call Rate  : {valid_tool_calls_count}/5 ({valid_tool_calls_count/5*100:.0f}%)")
    print(f"  - Correct Row Selection : {correct_row_count}/5 ({correct_row_count/5*100:.0f}%)")
    print(f"  - Zero Malformed Calls  : {malformed_calls_count == 0} ({malformed_calls_count} malformed)")
    print(f"-------------------------------------------------------\n")
    return {
        "model": model_name,
        "total_latency": total_latency,
        "avg_latency": avg_latency,
        "valid_rate": valid_tool_calls_count,
        "correct_row": correct_row_count,
        "zero_malformed": (malformed_calls_count == 0)
    }

if __name__ == "__main__":
    print("Starting Isolated 5-Turn MCP Benchmark: Qwen 2.5 7B vs Llama 3.1...")
    qwen_res = evaluate_model("qwen2.5:7b-instruct")
    llama_res = evaluate_model("llama3.1:latest")
    
    print("\n=======================================================")
    print("  FINAL COMPARATIVE SCORECARD")
    print("=======================================================")
    print(f"Metric                  | Qwen 2.5 (7B)        | Llama 3.1 (8B)")
    print(f"------------------------+----------------------+----------------------")
    print(f"Avg Latency / Turn      | {qwen_res['avg_latency']:6.2f}s              | {llama_res['avg_latency']:6.2f}s")
    print(f"Valid Tool Calls (out of 5) | {qwen_res['valid_rate']}/5                  | {llama_res['valid_rate']}/5")
    print(f"Correct Row Accuracy    | {qwen_res['correct_row']}/5                  | {llama_res['correct_row']}/5")
    print(f"Zero Malformed Calls?   | {str(qwen_res['zero_malformed']):<20} | {str(llama_res['zero_malformed']):<20}")
    print("=======================================================\n")
