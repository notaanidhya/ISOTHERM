import sys
import os
import json
import ast
import asyncio
import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.config import PROJECT_ROOT, OLLAMA_MODEL, DB_PATH, OCCUPIED_HOURS
from src.utils.carbon import get_tou_price, get_carbon_intensity
from src.state_bus.queries import get_latest_state, insert_action, insert_decision
from src.agent.safety import clamp_setpoint, enforce_deadband

def convert_mcp_tool_to_ollama(mcp_tool) -> dict:
    """Translates an MCP Tool schema to Ollama / OpenAI function tool format."""
    schema = mcp_tool.inputSchema or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": schema
        }
    }

async def run_mcp_agent_turn_async(sim_time_hours: float, model: str = OLLAMA_MODEL, db_path: str = DB_PATH) -> dict:
    """Asynchronously connects to stdio MCP server, fetches tools, sends prompt to Ollama, and executes tool calls."""
    server_script = os.path.join(PROJECT_ROOT, "src", "mcp_server", "server.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=env,
        cwd=PROJECT_ROOT
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools from MCP server
            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools

            # Translate to Ollama function tool format
            ollama_tools = [convert_mcp_tool_to_ollama(t) for t in mcp_tools]

            # ── Time / TOU / Occupancy / Season context ─────────────────────
            hour_of_day       = int(sim_time_hours) % 24
            tou_price         = get_tou_price(hour_of_day)
            carbon_intensity  = get_carbon_intensity(hour_of_day)
            is_occupied       = OCCUPIED_HOURS[0] <= hour_of_day < OCCUPIED_HOURS[1]
            is_precon         = (hour_of_day == OCCUPIED_HOURS[0] - 1)  # 07:00 pre-conditioning window

            # Rough season from sim_time_hours (day 152–243 ≈ Jun–Aug = summer)
            day_of_year = int(sim_time_hours / 24) % 365
            is_summer   = 152 <= day_of_year <= 243
            season      = "SUMMER (cooling dominant)" if is_summer else "WINTER (heating dominant)"

            # ── TOU tier ─────────────────────────────────────────────────────
            if tou_price >= 0.15:
                tou_tier     = "PEAK HIGH-COST ($0.15/kWh)"
                tou_strategy = "CRITICAL LOAD SHEDDING: Heating ≤19°C, Cooling ≥25.5°C. Comfort may slip to PMV ±0.8."
            elif tou_price <= 0.05:
                tou_tier     = "OFF-PEAK CHEAP ($0.05/kWh)"
                tou_strategy = "PRE-CONDITIONING BUFFER: Build thermal mass while power is cheap. Heating 21.5–22.5°C, Cooling 23–24°C."
            else:
                tou_tier     = "MID-PEAK STANDARD ($0.10/kWh)"
                tou_strategy = "BALANCED: Heating 20–21°C, Cooling 24–25°C."

            # ── Occupancy mode ────────────────────────────────────────────────
            if is_precon:
                occupancy_mode     = "PRE-CONDITIONING (07:00 — occupants arrive in 1 hour)"
                occupancy_strategy = (
                    "Bring all zones to comfort setpoints NOW using off-peak or mid-peak power. "
                    "Target: zone_temp within 0.5°C of occupied targets before 08:00. "
                    "Heating: 20–21°C, Cooling: 24–25°C."
                )
            elif is_occupied:
                occupancy_mode     = "OCCUPIED (08:00–18:00)"
                occupancy_strategy = (
                    "Building has occupants. Comfort target PMV ±0.5. "
                    "Apply TOU strategy above — do not sacrifice comfort unless PEAK tier."
                )
            else:
                occupancy_mode     = "UNOCCUPIED (18:00–08:00)"
                occupancy_strategy = (
                    "Building is EMPTY. Zero comfort obligation. "
                    "Apply NIGHT SETBACK to minimise indoor–outdoor delta-T and total kWh:\n"
                    f"  {'Winter' if not is_summer else 'Summer'} → Heating: 16–17°C, Cooling: 27°C\n"
                    "This is the primary mechanism for real energy savings — lower delta-T = less heat loss. "
                    "Do NOT maintain comfortable temperatures for empty offices."
                )

            # ── Fallback setpoints respect occupancy ──────────────────────────
            if is_occupied or is_precon:
                fallback_htg, fallback_clg = 21.0, 24.0
            else:
                fallback_htg, fallback_clg = 17.0, 27.0  # setback fallback

            system_prompt = f"""You are an autonomous HVAC Building Management System agent controlling a 5-zone commercial office.
ZONES: SPACE1-1, SPACE2-1, SPACE3-1, SPACE4-1, SPACE5-1

CURRENT CONTEXT:
- Simulation Hour : {sim_time_hours:.1f}  (Clock: {hour_of_day:02d}:00)
- Season          : {season}
- TOU Tier        : {tou_tier}
- Electricity Price: ${tou_price:.2f}/kWh
- Carbon Intensity : {carbon_intensity} gCO2/kWh
- Occupancy Mode  : {occupancy_mode}

OCCUPANCY STRATEGY (HIGHEST PRIORITY AFTER SAFETY):
{occupancy_strategy}

TOU ENERGY STRATEGY:
{tou_strategy}

DECISION TABLE — apply the matching row:
 UNOCCUPIED  | Any TOU    → Heating 16-17°C,  Cooling 27°C          (night setback)
 PRE-CON     | Any TOU    → Heating 20-21°C,  Cooling 24-25°C       (ramp up early)
 OCCUPIED    | Off-Peak   → Heating 21.5-22°C, Cooling 23-24°C      (pre-condition)
 OCCUPIED    | Mid-Peak   → Heating 20-21°C,  Cooling 24-25°C       (balanced)
 OCCUPIED    | Peak       → Heating ≤19°C,    Cooling ≥25.5°C       (load shed, PMV ±0.8 OK)

HARD CONSTRAINTS:
- Zone temperatures must stay between 16°C and 30°C at all times.
- Cooling setpoint ≥ Heating setpoint + 2.0°C (deadband — mandatory).
- Heating range: 16.0–24.0°C  |  Cooling range: 22.0–30.0°C

TOOL CALL SEQUENCE (call all three, in order):
1. get_building_state      — read current temps, PMV, IAQ, HVAC power
2. set_all_setpoints       — apply the correct row from the decision table above for all 5 zones
3. log_decision_tool       — record your reasoning (cite which row you applied and why)
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Hour {sim_time_hours:.1f} | {occupancy_mode} | {tou_tier} | {season}. "
                    f"Apply the correct decision table row for all 5 zones and log your reasoning."
                )}
            ]

            # Step 1: Initial LLM call with tools
            try:
                response = ollama.chat(
                    model=model,
                    messages=messages,
                    tools=ollama_tools
                )
            except Exception as e:
                print(f"Ollama chat error: {e}")
                return {"status": "error", "error": str(e)}

            msg        = response.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            # Fallback — model didn't emit tool_calls; apply occupancy-aware defaults
            if not tool_calls:
                content = msg.get("content", "")
                print(f"LLM Response text (no tool calls): {content[:150]}...")

                default_setpoints = [
                    {"zone_name": z, "heating_c": fallback_htg, "cooling_c": fallback_clg}
                    for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
                ]
                await session.call_tool("set_all_setpoints", {"setpoints": default_setpoints, "db_path": db_path})
                await session.call_tool("log_decision_tool", {
                    "sim_time_hours": sim_time_hours,
                    "reasoning": content or f"Fallback: {occupancy_mode} defaults applied",
                    "action": json.dumps(default_setpoints),
                    "db_path": db_path
                })
                return {"status": "completed_fallback", "tool_calls_executed": 0}

            # Step 2: Dispatch tool calls to MCP server
            for tool_call in tool_calls:
                func      = tool_call.get("function", {})
                tool_name = func.get("name")
                tool_args = func.get("arguments", {}) or {}
                tool_args["db_path"] = db_path

                print(f"Executing MCP Tool: {tool_name} with args: {tool_args}")
                try:
                    tool_result = await session.call_tool(tool_name, tool_args)
                    print(f"Tool {tool_name} result: {str(tool_result)[:100]}...")
                except Exception as ex:
                    print(f"Error executing tool {tool_name}: {ex}")

            return {"status": "completed", "tool_calls_executed": len(tool_calls)}

def execute_agent_turn_sync(sim_time_hours: float, model: str = OLLAMA_MODEL, db_path: str = DB_PATH) -> dict:
    """Synchronous wrapper callable from inside EnergyPlus blocking callback thread."""
    try:
        return asyncio.run(run_mcp_agent_turn_async(sim_time_hours, model, db_path))
    except Exception as e:
        print(f"Error in execute_agent_turn_sync: {e}")
        # Occupancy-aware error fallback
        hour_of_day   = int(sim_time_hours) % 24
        is_unoccupied = not (OCCUPIED_HOURS[0] <= hour_of_day < OCCUPIED_HOURS[1])
        fb_htg = 17.0 if is_unoccupied else 21.0
        fb_clg = 27.0 if is_unoccupied else 24.0
        for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]:
            insert_action(z, fb_htg, fb_clg, db_path=db_path)
        insert_decision(
            sim_time_hours, {},
            f"Error fallback ({'UNOCCUPIED setback' if is_unoccupied else 'OCCUPIED defaults'}): {e}",
            [{"zone": z, "heating_c": fb_htg, "cooling_c": fb_clg} for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]],
            db_path=db_path
        )
        return {"status": "fallback", "error": str(e)}

if __name__ == "__main__":
    from src.state_bus.db import init_db
    init_db()
    print("Testing isolated MCP Client to Ollama tool-calling bridge...")
    res = execute_agent_turn_sync(12.0)
    print(f"Result: {res}")
