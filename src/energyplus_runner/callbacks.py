import sys
from src.config import ZONES, DB_PATH, OCCUPIED_HOURS, UNOCCUPIED_COOLING_CEILING, UNOCCUPIED_HEATING_FLOOR
from src.energyplus_runner.sensors import SensorRegistry
from src.energyplus_runner.actuators import ActuatorRegistry
from src.state_bus.queries import insert_state_log, get_pending_actions, mark_action_applied
from src.agent.mcp_client import execute_agent_turn_sync

def _apply_occupancy_clamps(htg: float, clg: float, is_unoccupied: bool) -> tuple:
    """Hard-enforce night setback ceiling/floor — overrides LLM if needed."""
    if is_unoccupied:
        clg = min(clg, UNOCCUPIED_COOLING_CEILING)
        htg = max(htg, UNOCCUPIED_HEATING_FLOOR)
    return htg, clg

def create_synchronous_callback(api, db_path=DB_PATH):
    sensors = SensorRegistry()
    actuators = ActuatorRegistry()

    last_agent_hour = -1.0
    current_setpoints = {z: {"heating_c": 21.0, "cooling_c": 24.0} for z in ZONES}

    def callback(state):
        nonlocal last_agent_hour, current_setpoints

        if not api.exchange.api_data_fully_ready(state):
            return

        if api.exchange.warmup_flag(state):
            return

        if not sensors.initialized:
            sensors.init_handles(state, api)
            actuators.init_handles(state, api)

        # 1. Compute current simulation time in total elapsed hours
        day_of_year = api.exchange.day_of_year(state)
        current_hour_of_day = api.exchange.current_time(state)
        sim_time_hours = (day_of_year - 1) * 24.0 + current_hour_of_day

        # Occupancy flag used by hard clamp below
        hour_of_day = int(sim_time_hours) % 24
        is_unoccupied = not (OCCUPIED_HOURS[0] <= hour_of_day < OCCUPIED_HOURS[1])

        # Automatic transition: when entering occupied hours (08:00), ensure setpoints aren't left in night setback
        if not is_unoccupied:
            for z in ZONES:
                if current_setpoints[z]["heating_c"] < 19.0:
                    h_safe, c_safe = actuators.set_zone_setpoint(state, api, z, 20.5, 24.5)
                    current_setpoints[z] = {"heating_c": h_safe, "cooling_c": c_safe}

        # 2. Apply any pending actions from action_queue (with occupancy clamps)
        pending = get_pending_actions(db_path=db_path)
        for act in pending:
            z = act["zone_name"]
            htg, clg = _apply_occupancy_clamps(
                act["heating_setpoint_c"], act["cooling_setpoint_c"], is_unoccupied
            )
            h_safe, c_safe = actuators.set_zone_setpoint(state, api, z, htg, clg)
            current_setpoints[z] = {"heating_c": h_safe, "cooling_c": c_safe}
            mark_action_applied(act["id"], db_path=db_path)

        # Phase 02 — Apply automatic occupancy-based ventilation every timestep
        # (LLM can override per-zone via set_ventilation MCP tool if wired)
        actuators.apply_occupancy_ventilation(state, api, hour_of_day)

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
                hvac_elec_kw=env.get("elec_kw", 0.0),
                outdoor_temp=env["outdoor_temp_c"],
                solar=0.0,
                hvac_gas_kw=env.get("gas_kw", 0.0),
                db_path=db_path
            )

        # 5. Synchronous LLM Control Trigger (Every 3 simulated hours / 180 min)
        AGENT_INTERVAL_HOURS = 3.0
        if last_agent_hour < 0 or (sim_time_hours - last_agent_hour >= AGENT_INTERVAL_HOURS):
            print(f"\n[Sync Control Loop] Hour {sim_time_hours:.1f} | {'UNOCCUPIED' if is_unoccupied else 'OCCUPIED'} -> Invoking LLM Agent Turn...")

            # BLOCKING SYNCHRONOUS CALL to LLM MCP Client
            res = execute_agent_turn_sync(sim_time_hours=sim_time_hours, db_path=db_path)
            print(f"[Sync Control Loop] LLM Agent turn finished: {res.get('status')} (tools: {res.get('tool_calls_executed', 0)})")

            # Immediately apply post-agent setpoints (with occupancy clamps)
            post_pending = get_pending_actions(db_path=db_path)
            for act in post_pending:
                z = act["zone_name"]
                htg, clg = _apply_occupancy_clamps(
                    act["heating_setpoint_c"], act["cooling_setpoint_c"], is_unoccupied
                )
                h_safe, c_safe = actuators.set_zone_setpoint(state, api, z, htg, clg)
                current_setpoints[z] = {"heating_c": h_safe, "cooling_c": c_safe}
                mark_action_applied(act["id"], db_path=db_path)

            last_agent_hour = sim_time_hours

    return callback
