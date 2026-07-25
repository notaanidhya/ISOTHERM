import sys
import os
from eppy.modeleditor import IDF

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

EP_PATH = r"C:\EnergyPlusV26-1-0"
IDD_FILE = os.path.join(EP_PATH, "Energy+.idd")

def prepare_model():
    IDF.setiddname(IDD_FILE)
    
    idf_path = os.path.join("building_model", "5ZoneAirCooled.idf")
    idf = IDF(idf_path)
    
    zones = ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
    
    print("=== 1. Creating Constant Schedules for Fanger PMV Comfort Model ===")
    
    # 1. Air Velocity Schedule (0.1 m/s constant)
    if not idf.getobject("SCHEDULE:COMPACT", "Air-Vel-Sch"):
        vel_sch = idf.newidfobject("SCHEDULE:COMPACT")
        vel_sch.Name = "Air-Vel-Sch"
        vel_sch.Schedule_Type_Limits_Name = "Any Number"
        vel_sch.Field_1 = "Through: 12/31"
        vel_sch.Field_2 = "For: AllDays"
        vel_sch.Field_3 = "Until: 24:00"
        vel_sch.Field_4 = 0.1
        print("  + Created Air-Vel-Sch (0.1 m/s)")
        
    # 2. Clothing Schedule (1.0 clo constant)
    if not idf.getobject("SCHEDULE:COMPACT", "Clothing-Sch"):
        clo_sch = idf.newidfobject("SCHEDULE:COMPACT")
        clo_sch.Name = "Clothing-Sch"
        clo_sch.Schedule_Type_Limits_Name = "Any Number"
        clo_sch.Field_1 = "Through: 12/31"
        clo_sch.Field_2 = "For: AllDays"
        clo_sch.Field_3 = "Until: 24:00"
        clo_sch.Field_4 = 1.0
        print("  + Created Clothing-Sch (1.0 clo)")

    # 3. Work Efficiency Schedule (0.0 constant)
    if not idf.getobject("SCHEDULE:COMPACT", "Work-Eff-Sch"):
        work_sch = idf.newidfobject("SCHEDULE:COMPACT")
        work_sch.Name = "Work-Eff-Sch"
        work_sch.Schedule_Type_Limits_Name = "Any Number"
        work_sch.Field_1 = "Through: 12/31"
        work_sch.Field_2 = "For: AllDays"
        work_sch.Field_3 = "Until: 24:00"
        work_sch.Field_4 = 0.0
        print("  + Created Work-Eff-Sch (0.0)")

    print("\n=== 2. Updating PEOPLE Objects with Fanger PMV + Companion Schedules ===")
    people_list = idf.idfobjects["PEOPLE"]
    for p in people_list:
        p.Work_Efficiency_Schedule_Name = "Work-Eff-Sch"
        p.Clothing_Insulation_Calculation_Method = "ClothingInsulationSchedule"
        p.Clothing_Insulation_Schedule_Name = "Clothing-Sch"
        p.Air_Velocity_Schedule_Name = "Air-Vel-Sch"
        p.Thermal_Comfort_Model_1_Type = "Fanger"
        print(f"  + Configured {p.Name} with Fanger PMV & companion schedules")

    print("\n=== 3. Adding Required Output Variables ===")
    existing_vars = [ov.Variable_Name.lower() for ov in idf.idfobjects["OUTPUT:VARIABLE"]]
    
    if "zone thermal comfort fanger model pmv" not in existing_vars:
        ov1 = idf.newidfobject("OUTPUT:VARIABLE")
        ov1.Key_Value = "*"
        ov1.Variable_Name = "Zone Thermal Comfort Fanger Model PMV"
        ov1.Reporting_Frequency = "hourly"
        print("  + Added Output:Variable Zone Thermal Comfort Fanger Model PMV")
        
    if "zone mechanical ventilation mass flow rate" not in existing_vars:
        ov2 = idf.newidfobject("OUTPUT:VARIABLE")
        ov2.Key_Value = "*"
        ov2.Variable_Name = "Zone Mechanical Ventilation Mass Flow Rate"
        ov2.Reporting_Frequency = "hourly"
        print("  + Added Output:Variable Zone Mechanical Ventilation Mass Flow Rate")

    print("\n=== 4. Creating Per-Zone Heating & Cooling Setpoint Schedules ===")
    base_htg = idf.getobject("SCHEDULE:COMPACT", "Htg-SetP-Sch")
    base_clg = idf.getobject("SCHEDULE:COMPACT", "Clg-SetP-Sch")
    
    for z in zones:
        htg_name = f"Htg-SetP-Sch-{z}"
        clg_name = f"Clg-SetP-Sch-{z}"
        
        if not idf.getobject("SCHEDULE:COMPACT", htg_name):
            new_htg = idf.copyidfobject(base_htg)
            new_htg.Name = htg_name
            print(f"  + Created schedule {htg_name}")
            
        if not idf.getobject("SCHEDULE:COMPACT", clg_name):
            new_clg = idf.copyidfobject(base_clg)
            new_clg.Name = clg_name
            print(f"  + Created schedule {clg_name}")

    print("\n=== 5. Re-linking ThermostatSetpoint:DualSetpoint per Zone ===")
    dual_setpoints = idf.idfobjects["THERMOSTATSETPOINT:DUALSETPOINT"]
    base_dual = dual_setpoints[0]
    
    for z in zones:
        dual_name = f"{z} DualSetPoint"
        htg_sch_name = f"Htg-SetP-Sch-{z}"
        clg_sch_name = f"Clg-SetP-Sch-{z}"
        
        dual_obj = idf.getobject("THERMOSTATSETPOINT:DUALSETPOINT", dual_name)
        if not dual_obj:
            dual_obj = idf.copyidfobject(base_dual)
            dual_obj.Name = dual_name
            dual_obj.Heating_Setpoint_Temperature_Schedule_Name = htg_sch_name
            dual_obj.Cooling_Setpoint_Temperature_Schedule_Name = clg_sch_name
            print(f"  + Created ThermostatSetpoint:DualSetpoint {dual_name}")
            
        thermostat = idf.getobject("ZONECONTROL:THERMOSTAT", f"{z} Control")
        if thermostat:
            thermostat.Control_3_Object_Type = "ThermostatSetpoint:DualSetpoint"
            thermostat.Control_3_Name = dual_name
            print(f"  + Re-linked {z} Control to {dual_name}")

    print("\n=== 6. Configuring 2 Representative Seasons (Winter & Summer Weeks) ===")
    for rp in list(idf.idfobjects["RUNPERIOD"]):
        idf.removeidfobject(rp)
        
    rp_winter = idf.newidfobject("RUNPERIOD")
    rp_winter.Name = "Winter Representative Days"
    rp_winter.Begin_Month = 1
    rp_winter.Begin_Day_of_Month = 15
    rp_winter.End_Month = 1
    rp_winter.End_Day_of_Month = 16
    rp_winter.Day_of_Week_for_Start_Day = "Sunday"
    rp_winter.Use_Weather_File_Holidays_and_Special_Days = "No"
    rp_winter.Use_Weather_File_Daylight_Saving_Period = "No"
    print("  + Created RunPeriod: Winter Representative Days (Jan 15 - Jan 16)")

    rp_summer = idf.newidfobject("RUNPERIOD")
    rp_summer.Name = "Summer Representative Days"
    rp_summer.Begin_Month = 7
    rp_summer.Begin_Day_of_Month = 1
    rp_summer.End_Month = 7
    rp_summer.End_Day_of_Month = 2
    rp_summer.Day_of_Week_for_Start_Day = "Sunday"
    rp_summer.Use_Weather_File_Holidays_and_Special_Days = "No"
    rp_summer.Use_Weather_File_Daylight_Saving_Period = "No"
    print("  + Created RunPeriod: Summer Representative Days (Jul 1 - Jul 2)")

    output_path = os.path.join("building_model", "5ZoneAirCooled_Prepared.idf")
    idf.saveas(output_path)
    print(f"\nSUCCESS: Prepared building model saved to: {output_path}")

if __name__ == "__main__":
    prepare_model()
