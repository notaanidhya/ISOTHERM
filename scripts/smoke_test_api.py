import sys
import os

EP_PATH = r"C:\EnergyPlusV26-1-0"
if EP_PATH not in sys.path:
    sys.path.insert(0, EP_PATH)

from pyenergyplus.api import EnergyPlusAPI

def main():
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()

    call_count = 0
    space1_temp_handle = -1
    outdoor_temp_handle = -1
    clg_actuator_handle = -1
    htg_actuator_handle = -1

    def callback_function(state_arg):
        nonlocal call_count, space1_temp_handle, outdoor_temp_handle, clg_actuator_handle, htg_actuator_handle
        
        if not api.exchange.api_data_fully_ready(state_arg):
            return

        if space1_temp_handle == -1:
            # Query exact variables verified from IDF Output:Variable list
            space1_temp_handle = api.exchange.get_variable_handle(
                state_arg, "Zone Air Temperature", "SPACE1-1"
            )
            outdoor_temp_handle = api.exchange.get_variable_handle(
                state_arg, "Site Outdoor Air Drybulb Temperature", "Environment"
            )
            # Query actuator handles for schedule overrides
            clg_actuator_handle = api.exchange.get_actuator_handle(
                state_arg, "Schedule:Compact", "Schedule Value", "Clg-SetP-Sch"
            )
            htg_actuator_handle = api.exchange.get_actuator_handle(
                state_arg, "Schedule:Compact", "Schedule Value", "Htg-SetP-Sch"
            )

            print("=== EnergyPlus API Handles Initialized ===")
            print(f"  SPACE1-1 Temp Handle: {space1_temp_handle}")
            print(f"  Outdoor Temp Handle: {outdoor_temp_handle}")
            print(f"  Cooling Setpoint Actuator Handle: {clg_actuator_handle}")
            print(f"  Heating Setpoint Actuator Handle: {htg_actuator_handle}")

        call_count += 1

        # Test setpoint actuator override at timestep 50
        if call_count == 50 and clg_actuator_handle != -1:
            print(">>> OVERRIDING COOLING SETPOINT TO 26.0°C via Actuator <<<")
            api.exchange.set_actuator_value(state_arg, clg_actuator_handle, 26.0)

        if space1_temp_handle != -1 and outdoor_temp_handle != -1:
            space1_temp = api.exchange.get_variable_value(state_arg, space1_temp_handle)
            outdoor_temp = api.exchange.get_variable_value(state_arg, outdoor_handle if 'outdoor_handle' in locals() else outdoor_temp_handle)
            if call_count <= 5 or call_count % 25 == 0:
                print(f"[Callback #{call_count}] SPACE1-1 Temp: {space1_temp:.2f}°C | Outdoor: {outdoor_temp:.2f}°C")

        if call_count >= 100:
            print(f"\n✅ PHASE 0 DE-RISKING SUCCESS: 100 callbacks completed successfully!")
            api.runtime.stop_simulation(state_arg)

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, callback_function)

    model_path = os.path.abspath(os.path.join("building_model", "5ZoneAirCooled.idf"))
    weather_path = os.path.abspath(os.path.join("building_model", "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"))
    output_dir = os.path.abspath("api_test_output")

    cmd_args = [
        "-w", weather_path,
        "-d", output_dir,
        "-r", model_path
    ]

    exit_code = api.runtime.run_energyplus(state, cmd_args)
    print(f"EnergyPlus simulation finished with exit code: {exit_code}")
    api.state_manager.delete_state(state)

if __name__ == "__main__":
    main()
