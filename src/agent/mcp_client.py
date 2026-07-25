import sys
import os
import json
import ast
import asyncio
import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.config import PROJECT_ROOT, OLLAMA_MODEL, DB_PATH
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
            
            hour_of_day = int(sim_time_hours) % 24
            tou_price = get_tou_price(hour_of_day)
            carbon_intensity = get_carbon_intensity(hour_of_day)
            
            system_prompt = f"""You are an autonomous HVAC Building Management System optimization agent controlling a 5-zone commercial building.
ZONES: SPACE1-1, SPACE2-1, SPACE3-1, SPACE4-1, SPACE5-1

CURRENT CONDITIONS:
- Simulation Time: Hour {sim_time_hours:.1f} (Hour of day: {hour_of_day:02d}:00)
- Time-of-Use Electricity Rate: ${tou_price:.2f} / kWh
- Grid Carbon Intensity: {carbon_intensity} gCO2/kWh

GOALS & PRIORITY:
1. SAFETY: Keep zone temperatures between 15°C and 32°C at all times.
2. COMFORT & IAQ: Maintain PMV between -0.5 and +0.5 during occupied hours. Keep mechanical ventilation airflow > 0.05 kg/s.
3. COST ($) & ENERGY: Minimize HVAC electricity cost, especially during Peak TOU hours ($0.15/kWh from 12:00 to 18:00).
4. CARBON: Reduce HVAC demand during high-carbon grid hours.

CONSTRAINTS:
- Heating setpoint range: 16.0°C to 24.0°C
- Cooling setpoint range: 22.0°C to 30.0°C
- Cooling setpoint must be ≥ Heating setpoint + 2.0°C (deadband).

INSTRUCTIONS:
You MUST call the available tools:
1. Call `get_building_state` to view current zone temperatures, PMV, IAQ flow, and HVAC power.
2. Call `set_all_setpoints` to update zone setpoints for all 5 zones.
3. If errors or warnings are flagged, call `extract_runtime_errors`.
4. Call `log_decision_tool` to log your decision reasoning.
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Simulation hour {sim_time_hours:.1f}. Check building state, optimize setpoints for all 5 zones, and log your decision."}
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

            msg = response.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            # Fallback if model didn't directly emit tool_calls: execute set_all_setpoints directly
            if not tool_calls:
                content = msg.get("content", "")
                print(f"LLM Response text: {content[:150]}...")
                
                default_setpoints = [
                    {"zone_name": z, "heating_c": 21.0, "cooling_c": 24.0} for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
                ]
                await session.call_tool("set_all_setpoints", {"setpoints": default_setpoints, "db_path": db_path})
                await session.call_tool("log_decision_tool", {"sim_time_hours": sim_time_hours, "reasoning": content or "Structured optimization decision", "action": json.dumps(default_setpoints), "db_path": db_path})
                return {"status": "completed", "tool_calls_executed": 0}

            # Step 2: Dispatch executed tool calls to MCP server
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
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
        for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]:
            insert_action(z, 21.0, 24.0, db_path=db_path)
        insert_decision(sim_time_hours, {}, f"Fallback triggered due to error: {e}", [{"zone": z, "heating_c": 21.0, "cooling_c": 24.0} for z in ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]], db_path=db_path)
        return {"status": "fallback", "error": str(e)}

if __name__ == "__main__":
    from src.state_bus.db import init_db
    init_db()
    print("Testing isolated MCP Client to Ollama tool-calling bridge...")
    res = execute_agent_turn_sync(12.0)
    print(f"Result: {res}")
