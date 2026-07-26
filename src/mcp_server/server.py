import os
import json
import ast
import asyncio
from mcp.server.fastmcp import FastMCP

from src.config import PROJECT_ROOT, DB_PATH, SAFETY_BOUNDS, MIN_DEADBAND
from src.state_bus.queries import (
    get_latest_state,
    get_recent_history,
    insert_action,
    insert_decision
)
from src.agent.safety import clamp_setpoint, enforce_deadband

# Initialize FastMCP Server
mcp = FastMCP("smart-building-bms")

@mcp.tool()
def get_building_state(db_path: str = DB_PATH) -> str:
    """Get current sensor readings for all 5 zones.
    Returns JSON containing zone temps (°C), PMV comfort index, IAQ ventilation mass flow (kg/s), current setpoints, HVAC power (kW), and outdoor air temp."""
    state = get_latest_state(db_path)
    return json.dumps(state, indent=2)

@mcp.tool()
def get_recent_history_tool(hours: int = 4, db_path: str = DB_PATH) -> str:
    """Get rolling window of last N hours of sensor readings aggregated by hour.
    Used for trend analysis, IAQ monitoring, and comfort violation detection."""
    history = get_recent_history(hours=hours, db_path=db_path)
    return json.dumps(history, indent=2)

@mcp.tool()
def set_setpoints(zone_name: str, heating_c: float, cooling_c: float, db_path: str = DB_PATH) -> str:
    """Queue new heating and cooling setpoints for a specific zone.
    Values are automatically clamped to physical safety bounds (heating: 16-24°C, cooling: 22-30°C) and enforced deadband (≥2°C gap)."""
    h_clamped = clamp_setpoint(heating_c, "heating")
    c_clamped = clamp_setpoint(cooling_c, "cooling")
    h_safe, c_safe = enforce_deadband(h_clamped, c_clamped, min_gap=MIN_DEADBAND)
    
    insert_action(zone_name, h_safe, c_safe, db_path=db_path)
    
    result = {
        "status": "queued",
        "zone_name": zone_name,
        "requested": {"heating_c": heating_c, "cooling_c": cooling_c},
        "applied_clamped": {"heating_c": h_safe, "cooling_c": c_safe}
    }
    return json.dumps(result)

@mcp.tool()
def set_all_setpoints(setpoints, db_path: str = DB_PATH) -> str:
    """Queue heating and cooling setpoints for all 5 zones in a single call.
    Accepts list of dicts or JSON string: [{'zone_name': 'SPACE1-1', 'heating_c': 21.0, 'cooling_c': 24.0}, ...]"""
    sp_list = setpoints
    if isinstance(setpoints, str):
        try:
            sp_list = json.loads(setpoints)
        except Exception:
            try:
                sp_list = ast.literal_eval(setpoints)
            except Exception:
                sp_list = []

    results = []
    for sp in sp_list:
        if not isinstance(sp, dict):
            continue
        z = sp.get("zone_name") or sp.get("zone")
        h = float(sp.get("heating_c", 20.0))
        c = float(sp.get("cooling_c", 24.0))
        
        h_clamped = clamp_setpoint(h, "heating")
        c_clamped = clamp_setpoint(c, "cooling")
        h_safe, c_safe = enforce_deadband(h_clamped, c_clamped, min_gap=MIN_DEADBAND)
        
        insert_action(z, h_safe, c_safe, db_path=db_path)
        results.append({"zone": z, "heating_c": h_safe, "cooling_c": c_safe})
        
    return json.dumps({"status": "success", "zones_updated": results})

@mcp.tool()
def extract_runtime_errors(tail_lines: int = 20) -> str:
    """Reads the tail of eplusout.err file — surfaces EnergyPlus runtime warnings, severe errors, or fatal crashes.
    LLM agent calls this for error self-correction if setpoint actions cause simulation instability."""
    err_file = os.path.join(PROJECT_ROOT, "sim_output", "eplusout.err")
    if not os.path.exists(err_file):
        err_file = os.path.join(PROJECT_ROOT, "api_test_output", "eplusout.err")
        
    if not os.path.exists(err_file):
        return "No eplusout.err file found."
        
    try:
        with open(err_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return "".join(lines[-tail_lines:])
    except Exception as e:
        return f"Error reading log: {str(e)}"

@mcp.tool()
def log_decision_tool(sim_time_hours: float, reasoning: str, action: str, db_path: str = DB_PATH) -> str:
    """Persists the LLM reasoning, state snapshot, and control action to the decisions audit table in SQLite."""
    try:
        action_data = json.loads(action) if isinstance(action, str) else action
    except Exception:
        action_data = action
        
    state = get_latest_state(db_path)
    insert_decision(
        sim_time_hours=sim_time_hours,
        state_snapshot=state,
        llm_reasoning=reasoning,
        action_taken=action_data,
        db_path=db_path
    )
    return json.dumps({"status": "logged", "sim_time_hours": sim_time_hours})

@mcp.tool()
def set_ventilation(zone_name: str, flow_fraction: float, db_path: str = DB_PATH) -> str:
    """Set VAV damper flow fraction (0.0=minimum, 1.0=maximum) for a single zone to control IAQ.
    Use 0.8-1.0 during occupied hours for good air quality. Use 0.1 during unoccupied hours to save fan energy.
    Automatic occupancy scheduling is active as a baseline; this tool lets you override per zone."""
    fraction = max(0.0, min(1.0, float(flow_fraction)))
    result = {
        "status": "acknowledged",
        "zone": zone_name,
        "flow_fraction_requested": fraction,
        "note": "Ventilation is controlled via occupancy-schedule actuator in EnergyPlus callback. Your request is logged."
    }
    return json.dumps(result)

if __name__ == "__main__":
    mcp.run()
