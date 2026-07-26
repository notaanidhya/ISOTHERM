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

def get_target_setpoints(is_summer: bool, is_occupied: bool, is_precon: bool, tou_tier_name: str) -> tuple[float, float, str, str]:
    """
    CANONICAL SINGLE SOURCE OF TRUTH for all HVAC setpoint decisions.
    Returns: (heating_sp_c, cooling_sp_c, table_row_label, description)
    """
    if is_precon:
        if is_summer:
            return (16.0, 24.5, "PRE-CON | Any TOU", "precool without reheat")
        else:
            return (20.5, 25.0, "PRE-CON | Any TOU", "morning warmup")
            
    if not is_occupied:
        return (16.0, 27.0, "UNOCCUPIED | Any TOU", "night setback")
        
    if is_summer:
        # SUMMER (Cooling Dominant) — keep heating floor low (16.0°C) to eliminate VAV reheat waste!
        if tou_tier_name == "Peak":
            return (16.0, 26.0, "OCCUPIED | Peak", "load shed cooling, PMV ±0.8 OK")
        elif tou_tier_name == "Off-Peak":
            return (16.0, 23.5, "OCCUPIED | Off-Peak", "precool buffer")
        else:
            return (16.0, 24.5, "OCCUPIED | Mid-Peak", "balanced cooling")
    else:
        # WINTER (Heating Dominant)
        if tou_tier_name == "Peak":
            return (19.0, 25.5, "OCCUPIED | Peak", "load shed heating, PMV ±0.8 OK")
        elif tou_tier_name == "Off-Peak":
            return (21.5, 24.0, "OCCUPIED | Off-Peak", "comfort buffer")
        else:
            return (20.5, 25.0, "OCCUPIED | Mid-Peak", "balanced heating")

def render_decision_table_markdown() -> str:
    """Dynamically renders the DECISION TABLE for the LLM system prompt from get_target_setpoints."""
    lines = ["DECISION TABLE — apply the matching row:"]
    lines.append(" WINTER (Heating Dominant — Day < 152 or Day > 243):")
    for precon, occ, tier in [(False, False, "Any"), (True, False, "Any"), (False, True, "Off-Peak"), (False, True, "Mid-Peak"), (False, True, "Peak")]:
        h, c, row_lbl, desc = get_target_setpoints(False, occ, precon, tier)
        lines.append(f"  {row_lbl:<20} → Heating {h:.1f}°C, Cooling {c:.1f}°C   ({desc})")
    lines.append(" SUMMER (Cooling Dominant — Day 152 to 243):")
    for precon, occ, tier in [(False, False, "Any"), (True, False, "Any"), (False, True, "Off-Peak"), (False, True, "Mid-Peak"), (False, True, "Peak")]:
        h, c, row_lbl, desc = get_target_setpoints(True, occ, precon, tier)
        lines.append(f"  {row_lbl:<20} → Heating {h:.1f}°C, Cooling {c:.1f}°C   ({desc})")
    return "\n".join(lines)

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
                tou_tier_name = "Peak"
                tou_tier     = "PEAK HIGH-COST ($0.15/kWh)"
                tou_strategy = "CRITICAL LOAD SHEDDING: Minimize HVAC power while keeping PMV within ±0.8 (see Decision Table)."
            elif tou_price <= 0.05:
                tou_tier_name = "Off-Peak"
                tou_tier     = "OFF-PEAK CHEAP ($0.05/kWh)"
                tou_strategy = "PRE-CONDITIONING BUFFER: Build thermal mass while power is cheap without causing VAV reheat (see Decision Table)."
            else:
                tou_tier_name = "Mid-Peak"
                tou_tier     = "MID-PEAK STANDARD ($0.10/kWh)"
                tou_strategy = "BALANCED COMFORT: Standard operation without reheat waste (see Decision Table)."

            # ── Occupancy mode ────────────────────────────────────────────────
            if is_precon:
                occupancy_mode     = "PRE-CONDITIONING (07:00 — occupants arrive in 1 hour)"
                occupancy_strategy = "Bring zones toward comfort targets without causing reheat waste (see Decision Table)."
            elif is_occupied:
                occupancy_mode     = "OCCUPIED (08:00–18:00)"
                occupancy_strategy = "Building has occupants. Target comfortable temperatures according to season and TOU tier (see Decision Table)."
            else:
                occupancy_mode     = "UNOCCUPIED (18:00–08:00)"
                occupancy_strategy = "Building is EMPTY. Zero comfort obligation. Apply night setback (see Decision Table) to minimize indoor-outdoor delta-T."

            # ── Canonical setpoint lookup for current turn (SINGLE SOURCE OF TRUTH) ──
            curr_htg, curr_clg, curr_row_lbl, curr_desc = get_target_setpoints(is_summer, is_occupied, is_precon, tou_tier_name)

            # ── Phase 3A: Pre-fetch trend history and inject into prompt ──────
            # Fetch last 3 hours of sensor history directly — more reliable than
            # asking the LLM to call get_recent_history_tool every turn.
            trend_context = "No recent trend data available."
            try:
                history_result = await session.call_tool(
                    "get_recent_history_tool",
                    {"hours": 3, "db_path": db_path}
                )
                raw = ""
                if hasattr(history_result, "content") and history_result.content:
                    for item in history_result.content:
                        if getattr(item, "type", "") == "text" and hasattr(item, "text"):
                            raw = item.text
                            break
                        elif hasattr(item, "text"):
                            raw = item.text
                            break
                if not raw:
                    raw = str(history_result)
                    if "text=" in raw:
                        start = raw.find("text='") + 6
                        end   = raw.rfind("'")
                        raw   = raw[start:end] if start > 6 else raw
                history_data = json.loads(raw)
                if history_data and isinstance(history_data, list):
                    # Summarise: last known avg temp and PMV per zone
                    zone_summary = {}
                    for row in history_data:
                        z = row.get("zone_name", "?")
                        if z not in zone_summary:
                            zone_summary[z] = row
                    lines = []
                    for z, r in zone_summary.items():
                        avg_t   = r.get("avg_temp",    "?")
                        avg_pmv = r.get("avg_pmv",     "?")
                        avg_kw  = r.get("avg_hvac_kw", "?")
                        avg_out = r.get("avg_outdoor",  "?")
                        lines.append(f"  {z}: avg_temp={avg_t:.1f}°C  avg_pmv={avg_pmv:.3f}  avg_hvac_kw={avg_kw:.3f}  outdoor={avg_out:.1f}°C")
                    trend_context = "RECENT TREND (last 3 h per zone):\n" + "\n".join(lines)
            except Exception as hist_ex:
                print(f"[History] Pre-fetch failed: {hist_ex}")

            system_prompt = f"""You are an autonomous HVAC Building Management System agent controlling a 5-zone commercial office.
ZONES: SPACE1-1, SPACE2-1, SPACE3-1, SPACE4-1, SPACE5-1

CURRENT CONTEXT:
- Simulation Hour : {sim_time_hours:.1f}  (Clock: {hour_of_day:02d}:00)
- Season          : {season}
- TOU Tier        : {tou_tier}
- Electricity Price: ${tou_price:.2f}/kWh
- Carbon Intensity : {carbon_intensity} gCO2/kWh
- Occupancy Mode  : {occupancy_mode}

{trend_context}

OCCUPANCY STRATEGY (HIGHEST PRIORITY AFTER SAFETY):
{occupancy_strategy}

TOU ENERGY STRATEGY:
{tou_strategy}

{render_decision_table_markdown()}

CURRENT RECOMMENDED DECISION TABLE ROW FOR THIS TURN:
  {curr_row_lbl} → Heating {curr_htg:.1f}°C, Cooling {curr_clg:.1f}°C ({curr_desc})

HARD CONSTRAINTS:
- Zone temperatures must stay between 16°C and 30°C at all times.
- Cooling setpoint ≥ Heating setpoint + 2.0°C (deadband — mandatory).
- Heating range: 16.0–24.0°C  |  Cooling range: 22.0–30.0°C

TOOL CALL SEQUENCE (CRITICAL RULES):
1. get_building_state      — read current temps, PMV, IAQ flow (zone_iaq_vent_flow), HVAC power.
2. set_all_setpoints       — MUST ONLY take 'setpoints' parameter (list of [{{'zone_name': '...', 'heating_c': X, 'cooling_c': Y}}]). NEVER pass 'reasoning' or 'action' strings to set_all_setpoints!
3. log_decision_tool       — MANDATORY every turn. MUST ONLY take 'reasoning' and 'action' parameters. NEVER pass setpoint lists to log_decision_tool!

CRITICAL INSTRUCTION: Always make formal structured tool calls using your tool API. NEVER output raw markdown JSON strings like "```json ... ```" or text descriptions as a fallback.

IAQ VENTILATION (automatic, but you can monitor):
- Ventilation is automatically set to 80% during occupied hours and 10% during unoccupied hours.
- If zone_iaq_vent_flow reads < 0.005 kg/s during occupied hours, flag it in your log_decision_tool reasoning.
- You may call set_ventilation(zone_name, flow_fraction) to override a specific zone if IAQ is critical.
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

            # Fallback — model didn't emit tool_calls; apply canonical table defaults
            if not tool_calls:
                content = msg.get("content", "")
                print(f"LLM Response text (no tool calls): {content[:150]}...")

                fb_htg, fb_clg, fb_lbl, fb_desc = get_target_setpoints(is_summer, is_occupied, is_precon, tou_tier_name)
                default_setpoints = [
                    {"zone_name": z, "heating_c": fb_htg, "cooling_c": fb_clg}
                    for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
                ]
                await session.call_tool("set_all_setpoints", {"setpoints": default_setpoints, "db_path": db_path})
                await session.call_tool("log_decision_tool", {
                    "sim_time_hours": sim_time_hours,
                    "reasoning": content or f"Fallback ({fb_lbl}): {fb_desc}",
                    "action": json.dumps(default_setpoints),
                    "db_path": db_path
                })
                return {"status": "completed_fallback", "tool_calls_executed": 0}

            # ── Phase 3B & 3C: Dispatch tool calls with failure tracking ──────
            # Track which critical tools ran and whether they succeeded
            tools_executed   = []
            setpoints_ok     = False   # did set_all_setpoints succeed?
            log_tool_called  = False   # did LLM call log_decision_tool?
            applied_action   = None    # last setpoint payload for audit log

            for tool_call in tool_calls:
                func      = tool_call.get("function", {})
                tool_name = func.get("name")
                tool_args = func.get("arguments", {}) or {}
                tool_args["db_path"] = db_path

                print(f"Executing MCP Tool: {tool_name} with args: {tool_args}")
                try:
                    tool_result = await session.call_tool(tool_name, tool_args)
                    print(f"Tool {tool_name} result: {str(tool_result)[:100]}...")
                    tools_executed.append(tool_name)

                    if tool_name == "set_all_setpoints":
                        setpoints_ok   = True
                        applied_action = tool_args.get("setpoints", None)
                    if tool_name == "log_decision_tool":
                        log_tool_called = True

                except Exception as ex:
                    # Phase 3B: log failure clearly — don't let a failed set_all_setpoints
                    # get reported as success in the audit trail
                    print(f"[ERROR] Tool {tool_name} FAILED: {ex}")
                    if tool_name == "set_all_setpoints":
                        setpoints_ok = False  # explicitly mark as failed

            # Phase 3C: Guarantee the audit trail has an entry every turn
            # If the LLM skipped log_decision_tool, inject a structured fallback entry
            if not log_tool_called:
                status_note = (
                    f"[AUTO-LOG] LLM did not call log_decision_tool this turn. "
                    f"setpoints_ok={setpoints_ok}. "
                    f"Tools called by LLM: {[tc.get('function',{}).get('name') for tc in tool_calls]}. "
                    f"Occupancy: {occupancy_mode}, TOU: {tou_tier}, Season: {season}."
                )
                # Include failure flag in action if setpoints failed
                action_payload = applied_action if setpoints_ok else f"SET_FAILED — {applied_action}"
                try:
                    await session.call_tool("log_decision_tool", {
                        "sim_time_hours": sim_time_hours,
                        "reasoning": status_note,
                        "action": json.dumps(action_payload) if action_payload else json.dumps({"status": "no_setpoints_applied"}),
                        "db_path": db_path
                    })
                    print(f"[Phase3C] Auto-injected log_decision_tool entry for hour {sim_time_hours:.1f}")
                except Exception as log_ex:
                    print(f"[Phase3C] Auto-log also failed: {log_ex}")

            return {
                "status": "completed",
                "tool_calls_executed": len(tool_calls),
                "setpoints_ok": setpoints_ok,
                "log_called": log_tool_called or True,  # True because we guarantee it above
                "tools_run": tools_executed
            }

def execute_agent_turn_sync(sim_time_hours: float, model: str = OLLAMA_MODEL, db_path: str = DB_PATH) -> dict:
    """Synchronous wrapper callable from inside EnergyPlus blocking callback thread."""
    try:
        return asyncio.run(run_mcp_agent_turn_async(sim_time_hours, model, db_path))
    except Exception as e:
        print(f"Error in execute_agent_turn_sync: {e}")
        # Canonical table error fallback
        hour_of_day   = int(sim_time_hours) % 24
        day_of_year   = int(sim_time_hours / 24) % 365
        is_summer     = 152 <= day_of_year <= 243
        is_occupied   = OCCUPIED_HOURS[0] <= hour_of_day < OCCUPIED_HOURS[1]
        is_precon     = (hour_of_day == OCCUPIED_HOURS[0] - 1)
        tou_price     = get_tou_price(hour_of_day)
        tou_tier_name = "Peak" if tou_price >= 0.15 else ("Off-Peak" if tou_price <= 0.05 else "Mid-Peak")
        
        fb_htg, fb_clg, fb_lbl, fb_desc = get_target_setpoints(is_summer, is_occupied, is_precon, tou_tier_name)
        for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]:
            insert_action(z, fb_htg, fb_clg, db_path=db_path)
        insert_decision(
            sim_time_hours, {},
            f"Error fallback ({fb_lbl} -> {fb_desc}): {e}",
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
