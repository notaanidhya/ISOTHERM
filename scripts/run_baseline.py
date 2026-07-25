import sys
import os

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

EP_PATH = r"C:\EnergyPlusV26-1-0"
if EP_PATH not in sys.path:
    sys.path.insert(0, EP_PATH)

from pyenergyplus.api import EnergyPlusAPI
from src.config import PREPARED_IDF_PATH, WEATHER_PATH, BASELINE_DB_PATH, ZONES
from src.state_bus.db import init_db
from src.state_bus.queries import insert_state_log
from src.energyplus_runner.sensors import SensorRegistry

def run_baseline():
    """Runs baseline simulation without AI control, logging default schedule performance to baseline_state.db."""
    print("================================================================")
    print("📊 RUNNING BASELINE ENERGYPLUS SIMULATION (NO AI CONTROL)")
    print("================================================================")

    output_dir = os.path.join(PROJECT_ROOT, "baseline_output")
    os.makedirs(output_dir, exist_ok=True)
    init_db(db_path=BASELINE_DB_PATH)

    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    sensors = SensorRegistry()

    def baseline_callback(state_arg):
        if not api.exchange.api_data_fully_ready(state_arg):
            return

        if not sensors.initialized:
            sensors.init_handles(state_arg, api)

        day_of_year = api.exchange.day_of_year(state_arg)
        current_hour_of_day = api.exchange.current_time(state_arg)
        sim_time_hours = (day_of_year - 1) * 24.0 + current_hour_of_day

        env = sensors.read_environment_sensors(state_arg, api)

        for z in ZONES:
            zone_data = sensors.read_zone_sensors(state_arg, api, z)
            insert_state_log(
                sim_time_hours=sim_time_hours,
                zone_name=z,
                temp_c=zone_data["temp_c"],
                pmv=zone_data["pmv"],
                vent_flow=zone_data["iaq_vent_flow"],
                heating_sp=20.0,
                cooling_sp=24.0,
                hvac_kw=env["hvac_power_kw"],
                outdoor_temp=env["outdoor_temp_c"],
                solar=0.0,
                db_path=BASELINE_DB_PATH
            )

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, baseline_callback)

    cmd_args = [
        "-w", WEATHER_PATH,
        "-d", output_dir,
        "-r", PREPARED_IDF_PATH
    ]

    try:
        exit_code = api.runtime.run_energyplus(state, cmd_args)
        print(f"Baseline simulation completed with exit code: {exit_code}")
    except OSError as os_err:
        print(f"Baseline simulation completed (WinError caught): {os_err}")
    finally:
        api.state_manager.delete_state(state)
        print("Baseline run completed. Data logged to baseline_state.db")

if __name__ == "__main__":
    run_baseline()
