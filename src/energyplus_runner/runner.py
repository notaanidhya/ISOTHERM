import sys
import os
EP_PATH = r"C:\EnergyPlusV26-1-0"
if EP_PATH not in sys.path:
    sys.path.insert(0, EP_PATH)
from pyenergyplus.api import EnergyPlusAPI
from src.config import PREPARED_IDF_PATH, WEATHER_PATH, DB_PATH, PROJECT_ROOT
from src.energyplus_runner.callbacks import create_synchronous_callback
from src.state_bus.db import init_db

def run_synchronous_simulation(idf_path=PREPARED_IDF_PATH, epw_path=WEATHER_PATH, output_dir=None, db_path=DB_PATH):
    """Launches EnergyPlus with synchronous callback blocking every 60 sim minutes for LLM agent optimization."""
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "sim_output")
        
    os.makedirs(output_dir, exist_ok=True)
    init_db(db_path=db_path, reset=True)

    api = EnergyPlusAPI()
    state = api.state_manager.new_state()

    callback = create_synchronous_callback(api, db_path=db_path)
    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, callback)

    os.makedirs(output_dir, exist_ok=True)
    cmd_args = [
        "-w", epw_path,
        "-d", output_dir,
        "-r", idf_path
    ]

    print("=========================================================")
    print("🚀 LAUNCHING SYNCHRONOUS CLOSED-LOOP BMS SIMULATION")
    print(f"IDF: {idf_path}")
    print(f"EPW: {epw_path}")
    print(f"DB:  {db_path}")
    print("=========================================================")

    try:
        exit_code = api.runtime.run_energyplus(state, cmd_args)
        print(f"EnergyPlus simulation completed with exit code: {exit_code}")
    except OSError as os_err:
        print(f"EnergyPlus simulation exit caught (WinError expected): {os_err}")
    except Exception as e:
        print(f"Simulation execution error: {e}")
    finally:
        api.state_manager.delete_state(state)
        print("Simulation state cleanup complete.")

if __name__ == "__main__":
    run_synchronous_simulation()
