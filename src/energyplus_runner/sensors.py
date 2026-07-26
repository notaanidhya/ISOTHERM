import sys
from src.config import ZONES

class SensorRegistry:
    def __init__(self):
        self.temp_handles = {}
        self.pmv_handles = {}
        self.iaq_handles = {}
        self.outdoor_temp_handle = -1
        self.hvac_power_handle = -1
        self.is_meter_handle = False
        self.gas_power_handle = -1    # Phase 02: NaturalGas:Facility for heating savings
        
        # Cumulative meter state tracking (EnergyPlus get_meter_value returns cumulative Joules)
        self.prev_elec_joules = None
        self.prev_gas_joules  = None
        self.initialized = False

    def init_handles(self, state, api):
        """Initializes API variable handles for all 5 zones and outdoor environment."""
        for z in ZONES:
            # 1. Zone Air Temperature
            h_temp = api.exchange.get_variable_handle(state, "Zone Air Temperature", z)
            self.temp_handles[z] = h_temp
            
            # 2. Zone Fanger PMV (Try multiple key variations: People name vs Zone name)
            h_pmv = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", f"{z} PEOPLE 1")
            if h_pmv == -1:
                h_pmv = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", f"{z} PEOPLE")
            if h_pmv == -1:
                h_pmv = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", z)
            self.pmv_handles[z] = h_pmv
            
            # 3. Zone Mechanical Ventilation Mass Flow Rate (IAQ proxy)
            h_iaq = api.exchange.get_variable_handle(state, "Zone Mechanical Ventilation Mass Flow Rate", z)
            if h_iaq == -1:
                h_iaq = api.exchange.get_variable_handle(state, "Zone Mechanical Ventilation Standard Density Volume Flow Rate", z)
            self.iaq_handles[z] = h_iaq

        # Outdoor Drybulb Temp
        self.outdoor_temp_handle = api.exchange.get_variable_handle(
            state, "Site Outdoor Air Drybulb Temperature", "Environment"
        )
        
        # HVAC Power Handle (Variable preferred over meter for instantaneous demand rate in W)
        self.hvac_power_handle = api.exchange.get_variable_handle(state, "Facility Total HVAC Electricity Demand Rate", "Whole Building")
        if self.hvac_power_handle == -1:
            self.hvac_power_handle = api.exchange.get_variable_handle(state, "Facility Total HVAC Electricity Demand Rate", "Environment")
        if self.hvac_power_handle == -1:
            self.hvac_power_handle = api.exchange.get_variable_handle(state, "Facility Total Electricity Demand Rate", "Whole Building")
        if self.hvac_power_handle == -1:
            self.hvac_power_handle = api.exchange.get_meter_handle(state, "Electricity:HVAC")
            self.is_meter_handle = True
        else:
            self.is_meter_handle = False

        # NaturalGas:Facility meter — captures boiler/heating coil energy savings from setback
        self.gas_power_handle = api.exchange.get_meter_handle(state, "NaturalGas:Facility")
        if self.gas_power_handle == -1:
            self.gas_power_handle = api.exchange.get_meter_handle(state, "Heating:NaturalGas")

        self.initialized = True
        meter_name = "N/A"
        if self.is_meter_handle and self.hvac_power_handle != -1:
            try:
                meter_name = api.exchange.get_meter_name(state, self.hvac_power_handle)
            except Exception:
                meter_name = "Electricity:HVAC"
        print(f"[Sensors] Handles initialized for 5 zones. Outdoor: {self.outdoor_temp_handle}, HVAC elec handle: {self.hvac_power_handle} (is_meter={self.is_meter_handle}, meter='{meter_name}'), Gas handle: {self.gas_power_handle}, PMV handles: {self.pmv_handles}")

    def read_zone_sensors(self, state, api, zone_name: str) -> dict:
        """Reads temperature, PMV, and IAQ flow rate for a given zone."""
        temp = None
        pmv = None
        iaq = None

        h_t = self.temp_handles.get(zone_name, -1)
        if h_t != -1:
            temp = api.exchange.get_variable_value(state, h_t)

        h_p = self.pmv_handles.get(zone_name, -1)
        if h_p != -1:
            pmv = api.exchange.get_variable_value(state, h_p)

        h_i = self.iaq_handles.get(zone_name, -1)
        if h_i != -1:
            iaq = api.exchange.get_variable_value(state, h_i)

        return {
            "temp_c": temp,
            "pmv": pmv,
            "iaq_vent_flow": iaq
        }

    def read_environment_sensors(self, state, api) -> dict:
        """Reads outdoor temperature, electric HVAC demand, and natural gas heating demand.
        hvac_power_kw = electricity + gas combined (total HVAC energy rate for current timestep),
        enabling meaningful comparison of heating energy savings from night setback.
        Calculates delta Joules for cumulative meter readings to prevent cumulative odometer inflation."""
        outdoor_temp = None
        elec_kw = 0.0
        gas_kw  = 0.0

        if self.outdoor_temp_handle != -1:
            outdoor_temp = api.exchange.get_variable_value(state, self.outdoor_temp_handle)

        if self.hvac_power_handle != -1:
            if self.is_meter_handle:
                curr_elec = api.exchange.get_meter_value(state, self.hvac_power_handle)
                # get_meter_value returns Joules consumed during this 15-minute zone timestep
                elec_kw = curr_elec / 900.0 / 1000.0
            else:
                watts = api.exchange.get_variable_value(state, self.hvac_power_handle)
                elec_kw = watts / 1000.0 if watts and watts > 0 else 0.0

        if self.gas_power_handle != -1:
            curr_gas = api.exchange.get_meter_value(state, self.gas_power_handle)
            # get_meter_value returns Joules consumed during this 15-minute zone timestep
            gas_kw = curr_gas / 900.0 / 1000.0

        total_kw = elec_kw + gas_kw

        return {
            "outdoor_temp_c": outdoor_temp,
            "hvac_power_kw": total_kw,   # combined timestep average kW rate
            "elec_kw": elec_kw,
            "gas_kw": gas_kw,
        }
