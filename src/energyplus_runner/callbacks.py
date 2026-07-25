import sys
from src.config import ZONES, DB_PATH
from src.energyplus_runner.sensors import SensorRegistry
from src.energyplus_runner.actuators import ActuatorRegistry
from src.state_bus.queries import insert_state_log, get_pending_actions, mark_action_applied
from src.agent.mcp_client import execute_agent_turn_sync

def create_synchronous_callback(api, db_path=DB_PATH):
    sensors = SensorRegistry()
    actuators = ActuatorRegistry()
    
    last_agent_hour = -1.0
    current_setpoints = {z: {"heating_c": 21.0, "cooling_c": 24.0} for z in ZONES}

    def callback(state):
        nonlocal last_agent_hour, current_setpoints
        
        if not api.exchange.api_data_fully_ready(state):
            return

        if not sensors.initialized:
            sensors.init_handles(state, api)
            actuators.init_handles(state, api)

        # 1. Compute current simulation time in total elapsed hours
        day_of_year = api.exchange.day_of_year(state)
        current_hour_of_day = api.exchange.current_time(state)
        sim_time_hours = (day_of_year - 1) * 24.0 + current_hour_of_day

        # 2. Apply any pending actions from action_queue
        pending = get_pending_actions(db_path=db_path)
        for act in pending:
            z = act["zone_name"]
            h_safe, c_safe = actuators.set_zone_setpoint(
                state, api, z, act["heating_setpoint_c"], act["cooling_setpoint_c"]
            )
            current_setpoints[z] = {"heating_c": h_safe, "cooling_c": c_safe}
            mark_action_applied(act["id"], db_path=db_path)

        # 3. Read environment sensors
        env = sensors.read_environment_sensors(state, api)

        # 4. Read & Log zone sensors to SQLite state_log
        for z in ZONES:
            zone_data = sensors.read_zone_sensors(state, api, z)
            sp = current_setpoints[z]
            
            insert_state_log(
                sim_time_hours=sim_time_hours,
                zone_name=z,
                temp_c=zone_data["temp_c"],
                pmv=zone_data["pmv"],
                vent_flow=zone_data["iaq_vent_flow"],
                heating_sp=sp["heating_c"],
                cooling_sp=sp["cooling_c"],
                hvac_kw=env["hvac_power_kw"],
                outdoor_temp=env["outdoor_temp_c"],
                solar=0.0,
                db_path=db_path
            )

        # 5. Synchronous LLM Control Trigger (Every 60 simulated minutes)
        if last_agent_hour < 0 or (sim_time_hours - last_agent_hour >= 1.0):
            print(f"\n[Sync Control Loop] Hour {sim_time_hours:.1f} boundary reached -> Invoking LLM MCP Agent Turn...")
            
            # BLOCKING SYNCHRONOUS CALL to LLM MCP Client
            res = execute_agent_turn_sync(sim_time_hours=sim_time_hours, db_path=db_path)
            print(f"[Sync Control Loop] LLM Agent turn finished with status: {res.get('status')} (tools run: {res.get('tool_calls_executed', 0)})")
            
            # Immediately apply the setpoint actions generated during the agent turn
            post_pending = get_pending_actions(db_path=db_path)
            for act in post_pending:
                z = act["zone_name"]
                h_safe, c_safe = actuators.set_zone_setpoint(
                    state, api, z, act["heating_setpoint_c"], act["cooling_setpoint_c"]
                )
                current_setpoints[z] = {"heating_c": h_safe, "cooling_c": c_safe}
                mark_action_applied(act["id"], db_path=db_path)
                
            last_agent_hour = sim_time_hours

    return callback
